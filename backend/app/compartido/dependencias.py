"""Dependencias de FastAPI que aplican el orden de evaluación (convenciones 3.2 y ADR-002 §5).

Orden para una operación autenticada:
1. Sesión válida (existe, no revocada, no caducada, sin exceso de inactividad) -> NO_IDENTIFICADA.
2. La persona puede operar (acceso no desactivado, pertenencia vigente) -> política de acceso.
3. Si la operación modifica: token CSRF y origen.
Solo después se valida el formato, el recurso y las reglas de negocio, en cada operación.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido.politica_acceso import Contexto, contexto_de_operacion
from app.config import get_settings
from app.db import get_db
from app.errores import AppError
from app.seguridad.origen import origen_permitido
from app.seguridad.sesiones import (
    CABECERA_CSRF, NOMBRE_COOKIE, csrf_coincide, hash_secreto, token_csrf,
)


@dataclass(frozen=True)
class SesionAutenticada:
    sesion_id: UUID
    persona_id: UUID
    secreto: str


@dataclass(frozen=True)
class Operador:
    """Persona identificada que puede operar, con su sesión."""

    contexto: Contexto
    sesion_id: UUID
    secreto: str

    @property
    def persona_id(self) -> UUID:
        return self.contexto.persona_id

    @property
    def csrf_token(self) -> str:
        return token_csrf(self.secreto)


def sesion_actual(request: Request, db: Session = Depends(get_db)) -> SesionAutenticada:
    secreto = request.cookies.get(NOMBRE_COOKIE)
    if not secreto:
        raise AppError("NO_IDENTIFICADA")
    fila = db.execute(
        text("select s.id, i.persona_id, s.ultimo_uso_en, s.caduca_absoluta_en, s.revocada_en, now() as ahora "
             "from sesion s join identidad i on i.id = s.identidad_id where s.secreto_hash = :h"),
        {"h": hash_secreto(secreto)},
    ).one_or_none()
    if fila is None or fila.revocada_en is not None:
        raise AppError("NO_IDENTIFICADA")
    settings = get_settings()
    ahora: datetime = fila.ahora
    inactividad = timedelta(minutes=settings.session_idle_minutes)
    if ahora >= fila.caduca_absoluta_en or ahora - fila.ultimo_uso_en > inactividad:
        raise AppError("NO_IDENTIFICADA")
    # La actualización del último uso se limita en frecuencia para no escribir en cada petición
    if ahora - fila.ultimo_uso_en > timedelta(seconds=settings.session_touch_seconds):
        db.execute(text("update sesion set ultimo_uso_en = now() where id = :i"), {"i": fila.id})
    return SesionAutenticada(fila.id, fila.persona_id, secreto)


def operador(sesion: SesionAutenticada = Depends(sesion_actual), db: Session = Depends(get_db)) -> Operador:
    return Operador(contexto_de_operacion(db, sesion.persona_id), sesion.sesion_id, sesion.secreto)


def comprobar_csrf_y_origen(request: Request, secreto: str) -> None:
    if not origen_permitido(request):
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "Origin", "motivo": "origen_no_permitido"}])
    if not csrf_coincide(secreto, request.headers.get(CABECERA_CSRF)):
        raise AppError("SOLICITUD_INVALIDA", [{"campo": CABECERA_CSRF, "motivo": "csrf_invalido"}])


def operador_que_modifica(request: Request, op: Operador = Depends(operador)) -> Operador:
    comprobar_csrf_y_origen(request, op.secreto)
    return op
