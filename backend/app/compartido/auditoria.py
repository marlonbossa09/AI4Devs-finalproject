"""Servicio de auditoría (BE-10, subconjunto de la Entrega 2).

Registra UNA entrada por operación, dentro de la misma transacción que el cambio de dominio
(IR-24, IR-35): si algo falla, no queda ni el cambio ni la entrada. No hay consulta de
auditoría todavía (M3-07 queda fuera de esta entrega).
"""

import json
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def registrar_operacion_de_persona(
    db: Session,
    *,
    autor_persona_id: UUID,
    operacion: str,
    tipo_objeto: str,
    objeto_id: UUID,
    propietaria_registro_id: UUID,
    fecha_laboral_registro: date | None,
    valor_anterior: dict | None,
    valor_nuevo: dict | None,
    motivo: str | None = None,
) -> None:
    db.execute(
        text(
            "insert into auditoria (tipo_autor, autor_persona_id, operacion, tipo_objeto, objeto_id, "
            "propietaria_registro_id, fecha_laboral_registro, motivo, valor_anterior, valor_nuevo) "
            "values ('persona', :autor, :op, :tipo, :obj, :prop, :fecha, :motivo, "
            "cast(:ant as jsonb), cast(:nuevo as jsonb))"
        ),
        {
            "autor": autor_persona_id, "op": operacion, "tipo": tipo_objeto, "obj": objeto_id,
            "prop": propietaria_registro_id, "fecha": fecha_laboral_registro, "motivo": motivo,
            "ant": json.dumps(valor_anterior), "nuevo": json.dumps(valor_nuevo),
        },
    )
