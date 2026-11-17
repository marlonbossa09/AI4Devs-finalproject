"""Purga de los eventos técnicos de autenticación (M1-T7, A11; retención técnica inicial de 30 días, decisión del 2026-11-17).

Es una orden de la CLI de provisión (``purgar-eventos-autenticacion``) y NO depende de ningún planificador: nada la ejecuta sola.
Hasta que el despliegue (DT-07) decida cómo programarla, quien administra el servidor debe lanzarla periódicamente.

Garantías:
- Borra solo eventos anteriores a la retención configurada, que nunca puede ser menor de 30 días (validación de la configuración).
- La base de datos lo comprueba además por su cuenta: un disparador impide borrar un evento de menos de 30 días a cualquier rol,
  aunque este código o el reloj inyectado fallen.
- El rol de provisión solo puede leer ``id`` y ``ocurrido_en`` de los eventos y borrar: no ve ni los HMAC ni el detalle.
- No toca la auditoría funcional, los contadores ni las sesiones.
- Devuelve cuántos eventos purgó y hasta qué fecha, sin contenido de ninguno.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Connection, text

from app.config import get_settings
from app.provision.operadores import Operador
from app.provision.servicio import Reloj, ahora_utc


@dataclass(frozen=True)
class EventosPurgados:
    invocacion: uuid.UUID
    purgados: int
    anteriores_a: datetime
    retencion_dias: int


def purgar_eventos_de_autenticacion(conexion: Connection, operador: Operador, *, invocacion: uuid.UUID, reloj: Reloj = ahora_utc) -> EventosPurgados:
    dias = get_settings().auth_event_retention_days
    limite = reloj() - timedelta(days=dias)
    purgados = conexion.execute(text("delete from evento_autenticacion where ocurrido_en < :l"), {"l": limite}).rowcount
    return EventosPurgados(invocacion, purgados, limite, dias)
