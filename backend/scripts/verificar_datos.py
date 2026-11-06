"""Comprobaciones de coherencia de los datos (solo lectura).

Uso (desde backend/):  uv run python -m scripts.verificar_datos

- Líneas temporales de pertenencias (DB-01): sin huecos ni solapes dentro del período de
  actividad de cada persona. Los solapes ya los impide la base de datos; los huecos se
  detectan aquí (IR-28, contigüidad).
- ``estado_actual`` de las actividades (DB-03, DM-02): derivar desde la secuencia de avances y
  comparar con el valor almacenado.
"""

import sys

from sqlalchemy import Connection, text

from app.db import get_owner_engine

LINEAS_INCOHERENTES = text("""
    SELECT persona_id FROM (
        SELECT persona_id, hasta_exclusivo,
               lead(desde) OVER (PARTITION BY persona_id ORDER BY desde) AS siguiente_desde
        FROM pertenencia
    ) t
    WHERE siguiente_desde IS NOT NULL
      AND (hasta_exclusivo IS NULL OR hasta_exclusivo <> siguiente_desde)
""")

ESTADOS_INCOHERENTES = text("""
    SELECT a.id FROM actividad a
    WHERE a.estado_actual IS DISTINCT FROM COALESCE((
        SELECT av.estado
        FROM avance av JOIN bitacora b ON b.id = av.bitacora_id
        WHERE av.actividad_id = a.id
        ORDER BY b.fecha_laboral DESC, av.registrado_en DESC, av.id DESC
        LIMIT 1
    ), 'Pendiente')
""")


def lineas_temporales_incoherentes(conexion: Connection) -> list[object]:
    return [fila[0] for fila in conexion.execute(LINEAS_INCOHERENTES)]


def estados_actuales_incoherentes(conexion: Connection) -> list[object]:
    return [fila[0] for fila in conexion.execute(ESTADOS_INCOHERENTES)]


def main() -> int:
    with get_owner_engine().connect() as c:
        lineas = lineas_temporales_incoherentes(c)
        estados = estados_actuales_incoherentes(c)
    print(f"Personas con huecos en su línea temporal: {len(lineas)}")
    print(f"Actividades con estado_actual incoherente: {len(estados)}")
    return 0 if not lineas and not estados else 1


if __name__ == "__main__":
    sys.exit(main())
