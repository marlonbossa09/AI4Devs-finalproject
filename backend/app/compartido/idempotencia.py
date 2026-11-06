"""Clave de idempotencia (T-04, convenciones 5.3).

Para las operaciones no repetibles. Cabecera ``Idempotency-Key`` obligatoria. Por persona,
operación y clave se guarda la huella de la petición y la respuesta de los resultados con éxito.

- Misma clave y misma petición: devuelve la respuesta original sin repetir efectos ni auditoría.
- Misma clave y otra petición: ``CLAVE_IDEMPOTENCIA_REUTILIZADA``.
- Misma clave mientras la primera sigue en curso: ``OPERACION_EN_CURSO`` (bloqueo consultivo de
  transacción; se libera al confirmar o deshacer).
- Solo se guardan los éxitos: la fila se inserta en la MISMA transacción que la operación, así
  que una petición rechazada no deja clave y puede reintentarse corregida.
- Una clave caducada (ventana configurable) se trata como nueva.
La identidad, el acceso y la pertenencia se evalúan ANTES (dependencias), por lo que una persona
desactivada no recibe un resultado guardado.
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errores import AppError


@dataclass(frozen=True)
class Resultado:
    estado_http: int
    cuerpo: dict
    reproducido: bool = False


def calcular_huella(contenido: dict) -> str:
    canonico = json.dumps(contenido, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def ejecutar_con_clave(
    db: Session,
    *,
    persona_id: UUID,
    operacion: str,
    clave: str | None,
    huella: str,
    ejecutar: Callable[[], tuple[int, dict]],
) -> Resultado:
    if not clave or not clave.strip():
        raise AppError("CLAVE_IDEMPOTENCIA_OBLIGATORIA")

    bloqueada = db.execute(
        text("select pg_try_advisory_xact_lock(hashtextextended(:k, 0))"),
        {"k": f"{persona_id}|{operacion}|{clave}"},
    ).scalar_one()
    if not bloqueada:
        raise AppError("OPERACION_EN_CURSO")

    previa = db.execute(
        text("select huella, estado_http, respuesta, caduca_en <= now() as caducada from clave_idempotencia "
             "where persona_id = :p and operacion = :o and clave = :c"),
        {"p": persona_id, "o": operacion, "c": clave},
    ).one_or_none()
    if previa is not None:
        if previa.caducada:
            db.execute(
                text("delete from clave_idempotencia where persona_id = :p and operacion = :o and clave = :c"),
                {"p": persona_id, "o": operacion, "c": clave},
            )
        elif previa.huella == huella:
            return Resultado(previa.estado_http, previa.respuesta, reproducido=True)
        else:
            raise AppError("CLAVE_IDEMPOTENCIA_REUTILIZADA")

    estado_http, cuerpo = ejecutar()
    ventana = timedelta(hours=get_settings().idempotency_window_hours)
    db.execute(
        text("insert into clave_idempotencia (persona_id, operacion, clave, huella, estado_http, respuesta, caduca_en) "
             "values (:p, :o, :c, :h, :e, cast(:r as jsonb), now() + :v)"),
        {"p": persona_id, "o": operacion, "c": clave, "h": huella, "e": estado_http,
         "r": json.dumps(cuerpo), "v": ventana},
    )
    return Resultado(estado_http, cuerpo)
