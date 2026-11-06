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
from app.db import get_db
from app.errores import AppError
from app.modulos.acceso.esquemas import (
    InicioSesionEntrada, PersonaSalida, SesionActualSalida, SesionSalida,
)
from app.seguridad.contrasenas import hash_senuelo, verificar
from app.seguridad.identificadores import normalizar_identificador
from app.seguridad.origen import origen_permitido
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

    identidad = db.execute(
        text("select id, persona_id, hash_contrasena from identidad where identificador_acceso = :i"),
        {"i": normalizar_identificador(cuerpo.identificador_acceso)},
    ).one_or_none()
    # Un identificador inexistente, una contraseña incorrecta o una identidad sin primer acceso
    # completado producen el mismo error y un coste de verificación comparable.
    hash_guardado = identidad.hash_contrasena if identidad and identidad.hash_contrasena else hash_senuelo()
    correcta = verificar(hash_guardado, cuerpo.contrasena)
    if identidad is None or not identidad.hash_contrasena or not correcta:
        raise AppError("CREDENCIALES_INVALIDAS")

    # Credenciales correctas: si el acceso está desactivado o no hay pertenencia vigente, no se
    # crea sesión (CA-29, CA-255, CA-259).
    contexto = contexto_de_operacion(db, identidad.persona_id)

    # Cada inicio genera un secreto nuevo (contra la fijación de sesión).
    secreto = generar_secreto()
    absoluta = timedelta(minutes=get_settings().session_absolute_minutes)
    db.execute(
        text("insert into sesion (identidad_id, secreto_hash, caduca_absoluta_en) "
             "values (:i, :h, now() + :d)"),
        {"i": identidad.id, "h": hash_secreto(secreto), "d": absoluta},
    )
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
