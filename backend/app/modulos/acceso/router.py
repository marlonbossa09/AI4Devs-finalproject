"""Operaciones de sesión de M1 (HU-1.1): iniciar, cerrar y consultar la sesión."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido.dependencias import (
    Operador, SesionAutenticada, comprobar_csrf_y_origen, operador, sesion_actual,
)
from app.compartido.politica_acceso import contexto_de_operacion
from app.config import get_settings
from app.db import get_db, get_engine
from app.errores import AppError
from app.modulos.acceso.esquemas import (
    InicioSesionEntrada, PersonaSalida, SesionActualSalida, SesionSalida,
)
from app.seguridad import control_de_intentos as control
from app.seguridad.contrasenas import hash_senuelo, verificar
from app.seguridad.identificadores import normalizar_identificador
from app.seguridad.origen import direccion_del_cliente, origen_permitido
from app.seguridad.sesiones import NOMBRE_COOKIE, generar_secreto, hash_secreto, token_csrf

router = APIRouter(prefix="/sesion", tags=["M1 Acceso"])

SIN_CACHE = {"Cache-Control": "no-store"}


def _atributos_cookie() -> dict:
    # Prefijo __Host-: Secure, Path=/ y sin Domain. HttpOnly y SameSite=Strict (ADR-002).
    return {"httponly": True, "secure": True, "samesite": "strict", "path": "/"}


@router.post("", status_code=201, response_model=SesionSalida, summary="M1-01a Iniciar sesión")
def iniciar_sesion(
    cuerpo: InicioSesionEntrada, request: Request, response: Response, db: Session = Depends(get_db)
) -> SesionSalida:
    # Pública: no exige sesión ni token CSRF, pero sí se verifica el origen de la petición.
    if not origen_permitido(request):
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "Origin", "motivo": "origen_no_permitido"}])

    # M1-T7 (A9, A11): control de intentos ANTES de calcular Argon2. La reserva es atómica y se confirma en una transacción propia y
    # corta, así que sobrevive aunque la petición termine en error y no mantiene ningún bloqueo mientras se calcula el hash. Un intento
    # denegado (espera o límite de origen) responde 429 sin verificar la contraseña: ni siquiera con credenciales correctas, y sin
    # distinguir un identificador que existe de otro que no.
    normalizado = normalizar_identificador(cuerpo.identificador_acceso)
    origen = direccion_del_cliente(request)
    motor = get_engine()
    reserva = control.reservar(motor, normalizado, origen)
    if isinstance(reserva, control.Denegado):
        raise AppError.demasiadas_solicitudes(reserva.espera_segundos)
    clave_origen = control.clave_de_origen(origen)

    identidad = db.execute(
        text("select id, persona_id, hash_contrasena from identidad where identificador_acceso = :i"),
        {"i": normalizado},
    ).one_or_none()
    db.rollback()  # solo lectura: se libera la conexión antes de verificar el hash (nada abierto durante Argon2)
    # Un identificador inexistente, una contraseña incorrecta o una identidad sin primer acceso
    # completado producen el mismo error y un coste de verificación comparable.
    hash_guardado = identidad.hash_contrasena if identidad and identidad.hash_contrasena else hash_senuelo()
    correcta = verificar(hash_guardado, cuerpo.contrasena)
    if identidad is None or not identidad.hash_contrasena or not correcta:
        with motor.begin() as c:
            control.registrar_fallo(c, reserva, clave_origen=clave_origen)
        raise AppError("CREDENCIALES_INVALIDAS")

    # Credenciales correctas: si el acceso está desactivado o no hay pertenencia vigente, no se
    # crea sesión (CA-29, CA-255, CA-259). El bloqueo (hasta el fin de la transacción) serializa este inicio con la
    # desactivación del acceso (M1-08): o la desactivación ya está confirmada y se ve aquí, o termina después de que esta
    # sesión exista y la revoca. Así una carrera no deja ninguna sesión válida.
    db.execute(text("select pg_advisory_xact_lock(hashtextextended(:c, 0))"), {"c": f"smartwork:acceso:persona:{identidad.persona_id}"})
    try:
        contexto = contexto_de_operacion(db, identidad.persona_id)
    except AppError as error:
        if error.codigo in ("ACCESO_DESACTIVADO", "SIN_PERTENENCIA_VIGENTE"):
            # La petición termina en error y su transacción se deshará de todos modos: se cierra YA, para no retener su conexión ni el
            # bloqueo de la persona mientras se escribe el evento en otra transacción propia.
            db.rollback()
            with motor.begin() as c:
                if error.codigo == "ACCESO_DESACTIVADO":
                    control.registrar_evento(c, "acceso_desactivado_en_inicio", persona_id=identidad.persona_id,
                                             clave_cuenta=reserva.clave, clave_origen=clave_origen)
                else:
                    control.registrar_evento(c, "inicio_fallido", persona_id=identidad.persona_id, clave_cuenta=reserva.clave,
                                             clave_origen=clave_origen, detalle={"motivo": "sin_pertenencia_vigente"})
        raise

    # Autenticación COMPLETA (contraseña correcta, acceso habilitado y pertenencia vigente): solo ahora se reinicia el contador, en la misma
    # transacción que la sesión. Con el acceso desactivado o sin pertenencia el intento sigue contando (decisión del 2026-11-17).
    control.liberar_en(db.connection(), reserva)

    # Cada inicio genera un secreto nuevo (contra la fijación de sesión).
    secreto = generar_secreto()
    absoluta = timedelta(minutes=get_settings().session_absolute_minutes)
    sesion_id = db.execute(
        text("insert into sesion (identidad_id, secreto_hash, caduca_absoluta_en) "
             "values (:i, :h, now() + :d) returning id"),
        {"i": identidad.id, "h": hash_secreto(secreto), "d": absoluta},
    ).scalar_one()
    # Evento técnico (A11) en la misma transacción que la sesión: no hay evento de un inicio que no llegó a crear sesión.
    control.registrar_evento(db.connection(), "inicio_correcto", persona_id=identidad.persona_id, sesion_id=sesion_id,
                             clave_cuenta=reserva.clave, clave_origen=clave_origen)
    response.set_cookie(NOMBRE_COOKIE, secreto, **_atributos_cookie())
    response.headers.update(SIN_CACHE)
    return SesionSalida(
        persona=PersonaSalida(id=str(contexto.persona_id), nombre=contexto.nombre),
        rol_vigente=contexto.rol_vigente,
        csrf_token=token_csrf(secreto),
    )


@router.post("/cierre", status_code=204, summary="M1-01b Cerrar sesión")
def cerrar_sesion(
    request: Request, sesion: SesionAutenticada = Depends(sesion_actual), db: Session = Depends(get_db)
) -> Response:
    comprobar_csrf_y_origen(request, sesion.secreto)
    # La revocación ocurre en el servidor: borrar la cookie no basta.
    db.execute(text("update sesion set revocada_en = now() where id = :i"), {"i": sesion.sesion_id})
    control.registrar_evento(db.connection(), "cierre_sesion", persona_id=sesion.persona_id, sesion_id=sesion.sesion_id)
    respuesta = Response(status_code=204, headers=SIN_CACHE)
    respuesta.delete_cookie(NOMBRE_COOKIE, **_atributos_cookie())
    return respuesta


@router.get("", response_model=SesionActualSalida, summary="M1-01c Consultar mi sesión")
def consultar_sesion(response: Response, op: Operador = Depends(operador)) -> SesionActualSalida:
    response.headers.update(SIN_CACHE)
    return SesionActualSalida(
        persona=PersonaSalida(id=str(op.persona_id), nombre=op.contexto.nombre),
        rol_vigente=op.contexto.rol_vigente,
        csrf_token=op.csrf_token,
        fecha_actual=op.contexto.fecha_actual.isoformat(),
    )
