"""Registro de códigos de un solo uso en la base (M1-T8.1). Servicio INTERNO y reutilizable por las órdenes de emisión de T8.2.

Hace solo lo que el modelo necesita para que la emisión sea segura; NO es todavía una orden: no genera el código, no lo muestra, no audita y no
tiene CLI (eso es T8.2). El código nunca llega aquí en claro: solo su HMAC.

- Toma, en este orden, el bloqueo por persona que ya comparten el inicio de sesión y la desactivación del acceso, y el de (identidad, finalidad):
  una emisión no se cruza con una desactivación y dos emisiones de lo mismo se serializan. Sin esos bloqueos, la base lo impide igualmente: el
  índice único parcial deja como mucho un código pendiente por identidad y finalidad.
- Invalida el código pendiente anterior y registra el nuevo EN LA MISMA transacción (la llama quien la abre).
- El tiempo lo decide PostgreSQL: ``caduca_en`` se calcula con ``clock_timestamp()`` de la base y ``emitido_en`` lo fija un disparador. Python solo
  aporta una duración, nunca una fecha.
- Si la finalidad no corresponde al estado de la identidad (primer acceso con contraseña ya establecida, recuperación sin contraseña) o el acceso
  está desactivado, la base rechaza el registro (DD-05): no hay forma indirecta de dar un código a un acceso desactivado.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, text

from app.config import get_settings

FINALIDADES = ("primer_acceso", "recuperacion")


@dataclass(frozen=True)
class CodigoRegistrado:
    id: uuid.UUID
    caduca_en: datetime
    invalidados: int = 0          # códigos pendientes que este registro invalidó (0 o 1)


def invalidar_pendientes(conexion: Connection, identidad_id: uuid.UUID, finalidad: str) -> int:
    """Invalida el código pendiente (no usado ni invalidado) de esa identidad y finalidad. Devuelve cuántos invalidó (0 o 1)."""
    return conexion.execute(text(
        "update codigo_unico set invalidado_en = clock_timestamp() "
        "where identidad_id = :i and finalidad = :f and usado_en is null and invalidado_en is null"),
        {"i": identidad_id, "f": finalidad}).rowcount


def registrar_codigo(conexion: Connection, *, identidad_id: uuid.UUID, finalidad: str, hash_codigo: str, emitido_por: str,
                     validez_segundos: int | None = None) -> CodigoRegistrado:
    """Invalida el código pendiente anterior y registra el nuevo. ``emitido_por`` es la referencia NO secreta de quien emite
    (``operador:<identificador>|invocacion:<uuid>``, la misma que la auditoría de provisión)."""
    if finalidad not in FINALIDADES:
        raise ValueError("Finalidad de código desconocida")
    validez = validez_segundos if validez_segundos is not None else get_settings().code_validity_minutes * 60
    persona_id = conexion.execute(text("select persona_id from identidad where id = :i"), {"i": identidad_id}).scalar_one()
    for clave in (f"smartwork:acceso:persona:{persona_id}", f"smartwork:codigo:{identidad_id}:{finalidad}"):
        conexion.execute(text("select pg_advisory_xact_lock(hashtextextended(:c, 0))"), {"c": clave})
    invalidados = invalidar_pendientes(conexion, identidad_id, finalidad)
    fila = conexion.execute(text(
        "insert into codigo_unico (identidad_id, finalidad, hash_codigo, caduca_en, emitido_por) "
        "values (:i, :f, :h, clock_timestamp() + make_interval(secs => :v), :e) returning id, caduca_en"),
        {"i": identidad_id, "f": finalidad, "h": hash_codigo, "v": validez, "e": emitido_por}).one()
    return CodigoRegistrado(fila.id, fila.caduca_en, invalidados)


# ---------------------------------------------------------------------------------------------------------------- purga (M1-T8.6)

RETENCION_DIAS = 30   # D6: retención técnica de los códigos terminados. La base lo impone además por su cuenta (disparador de la migración 0014).


@dataclass(frozen=True)
class CodigosPurgados:
    """Resultado de la purga. Solo cifras: nunca el contenido, el hash ni la persona de ningún código."""

    invocacion: uuid.UUID
    purgados: int
    anteriores_a: datetime
    retencion_dias: int


def purgar_codigos_terminados(conexion: Connection, *, invocacion: uuid.UUID) -> CodigosPurgados:
    """Borra los códigos que terminaron (usados, invalidados o caducados) hace 30 días o más. Un código pendiente y vigente no termina nunca
    por sí solo, así que no se borra; tampoco uno que terminó hace menos de 30 días. «Terminó» es ``coalesce(usado_en, invalidado_en, caduca_en)``,
    el mismo criterio del disparador de la base. Todo el tiempo es el de PostgreSQL. Repetible: la segunda vez no encuentra nada que borrar."""
    limite = conexion.execute(text("select clock_timestamp() - make_interval(days => :d)"), {"d": RETENCION_DIAS}).scalar_one()
    purgados = conexion.execute(text("delete from codigo_unico where coalesce(usado_en, invalidado_en, caduca_en) <= :l"), {"l": limite}).rowcount
    return CodigosPurgados(invocacion, purgados, limite, RETENCION_DIAS)
