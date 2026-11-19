"""Gestión de su equipo por el supervisor (decisión de la persona responsable, 2026-11-19): crear colaboradores en su propio equipo, emitir su código de primer acceso y finalizar su pertenencia.

NO es una política nueva: reutiliza los casos de uso de provisión de M1 (``app.provision``), que ya contienen las reglas (sin altas históricas, un supervisor por equipo, sin solapes, código de un solo uso con
HMAC, auditoría sin secretos). Lo que cambia es QUIÉN los invoca y por qué canal: una persona supervisora autenticada por la API, con su sesión, CSRF y origen, en lugar de una persona operadora por la CLI.

Límites deliberados:
- Solo un supervisor con acceso efectivo, y solo sobre SU equipo (no hay parámetro de equipo): lo ajeno o inexistente responde ``RECURSO_NO_DISPONIBLE``.
- Solo crea y administra COLABORADORES. No crea equipos ni supervisores (no hay rol de administración) ni se finaliza a sí mismo.
- Las escrituras de personas usan la conexión del ROL DE PROVISIÓN (privilegios mínimos, ``PROVISION_DATABASE_URL``), no el de la aplicación: la API sigue sin poder escribir ``persona``, ``identidad`` ni ``pertenencia``
  por su cuenta; solo estos tres casos de uso, con sus reglas, lo hacen. La auditoría queda con la referencia ``operador:supervisor:<persona>|invocacion:<uuid>``.
- El código de primer acceso se devuelve UNA sola vez y no se registra ni se almacena en claro (solo su HMAC); el medio por el que el supervisor lo entrega a la persona sigue siendo una decisión abierta (PA-12).
"""

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador
from app.config import get_settings
from app.db import get_provision_engine
from app.errores import AppError
from app.provision import emision, programacion, servicio
from app.provision.errores import ErrorDeProvision
from app.provision.operadores import Operador as OperadorDeProvision

_A_CATALOGO = {"ACCESO_DESACTIVADO_ADMINISTRATIVAMENTE", "IDENTIFICADOR_DUPLICADO", "PERTENENCIA_INVALIDA", "FECHA_EFECTIVA_INVALIDA", "CAMPO_OBLIGATORIO",
               "TEXTO_DEMASIADO_LARGO", "RECURSO_NO_DISPONIBLE", "SOLICITUD_INVALIDA"}


def _equipo_del_supervisor(db: Session, op: Operador) -> uuid.UUID:
    """El equipo que supervisa HOY. Quien no es supervisor con acceso efectivo recibe 403; lo demás sale de su pertenencia, nunca de la petición."""
    if op.contexto.rol_vigente != "supervisor":
        raise AppError("OPERACION_NO_PERMITIDA")
    hoy = op.contexto.fecha_actual
    equipo = db.execute(
        text("select equipo_id from pertenencia where persona_id = :p and rol = 'supervisor' and desde <= :h and (hasta_exclusivo is null or hasta_exclusivo > :h)"),
        {"p": op.persona_id, "h": hoy}).scalar_one_or_none()
    if equipo is None:
        raise AppError("OPERACION_NO_PERMITIDA")
    return equipo


def _colaborador_del_equipo(db: Session, equipo_id: uuid.UUID, persona_id: uuid.UUID, hoy: date) -> None:
    """La persona es colaboradora VIGENTE de ese equipo; si no, el mismo 404 que un identificador inexistente."""
    existe = db.execute(
        text("select 1 from pertenencia where persona_id = :p and equipo_id = :e and rol = 'colaborador' and desde <= :h and (hasta_exclusivo is null or hasta_exclusivo > :h)"),
        {"p": persona_id, "e": equipo_id, "h": hoy}).first()
    if existe is None:
        raise AppError("RECURSO_NO_DISPONIBLE")


def _operador(op: Operador) -> OperadorDeProvision:
    return OperadorDeProvision(id=op.persona_id, identificador=f"supervisor:{op.persona_id}")


def _como_error_de_api(error: ErrorDeProvision) -> AppError:
    if error.codigo in _A_CATALOGO:
        return AppError(error.codigo, error.detalles)
    return AppError("ERROR_INTERNO")                           # p. ej. el secreto de códigos sin configurar: no se detalla


def _conexion_de_escritura():
    """Transacción del rol de provisión; comprueba que es ese rol y no otro (como la CLI)."""
    try:
        engine = get_provision_engine()
    except RuntimeError:
        raise AppError("ERROR_INTERNO") from None
    return engine.begin()


def _verificar_rol(conexion) -> None:
    actual = conexion.execute(text("select current_user")).scalar_one()
    if actual != get_settings().provision_db_role:
        raise AppError("ERROR_INTERNO")


def crear_colaborador(db: Session, op: Operador, nombre: object, identificador_acceso: object) -> dict:
    equipo_id = _equipo_del_supervisor(db, op)
    try:
        with _conexion_de_escritura() as conexion:
            _verificar_rol(conexion)
            creada = servicio.crear_persona(
                conexion, _operador(op), nombre=nombre if isinstance(nombre, str) else "", identificador_acceso=identificador_acceso if isinstance(identificador_acceso, str) else "",
                equipo_id=equipo_id, rol="colaborador", desde=op.contexto.fecha_actual)
    except ErrorDeProvision as error:
        raise _como_error_de_api(error) from None
    return {"persona_id": str(creada.persona_id), "nombre": nombre.strip(), "rol": "colaborador", "desde": creada.desde.isoformat()}


def emitir_codigo_de_primer_acceso(db: Session, op: Operador, persona_id: uuid.UUID) -> dict:
    equipo_id = _equipo_del_supervisor(db, op)
    _colaborador_del_equipo(db, equipo_id, persona_id, op.contexto.fecha_actual)
    visto: dict[str, object] = {}

    def presentar(codigo: str, caduca_en: datetime) -> None:
        visto["codigo"], visto["caduca_en"] = codigo, caduca_en

    try:
        with _conexion_de_escritura() as conexion:
            _verificar_rol(conexion)
            emision.emitir_codigo(conexion, _operador(op), persona_id=persona_id, finalidad=emision.PRIMER_ACCESO, verificacion=None, presentar=presentar)
    except ErrorDeProvision as error:
        raise _como_error_de_api(error) from None
    if "codigo" not in visto:
        raise AppError("ERROR_INTERNO")
    return {"codigo": visto["codigo"], "caduca_en": visto["caduca_en"].isoformat()}


def finalizar_pertenencia(db: Session, op: Operador, persona_id: uuid.UUID) -> dict:
    equipo_id = _equipo_del_supervisor(db, op)
    if persona_id == op.persona_id:
        raise AppError("OPERACION_NO_PERMITIDA")
    _colaborador_del_equipo(db, equipo_id, persona_id, op.contexto.fecha_actual)
    efectiva = op.contexto.fecha_actual + timedelta(days=1)       # CA-258: la finalización surte efecto en una fecha futura; hasta entonces sigue siendo integrante
    try:
        with _conexion_de_escritura() as conexion:
            _verificar_rol(conexion)
            programacion.finalizar_pertenencia(conexion, _operador(op), finalizaciones=[programacion.FinalizacionSolicitada(persona_id, efectiva)])
    except ErrorDeProvision as error:
        raise _como_error_de_api(error) from None
    return {"persona_id": str(persona_id), "fecha_efectiva": efectiva.isoformat()}
