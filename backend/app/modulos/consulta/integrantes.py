"""M4-05 (M4-T7) — integrantes vigentes de mi equipo (``GET /api/v1/equipo/integrantes``), solo lectura (D-M4-02, aprobada).

Para qué: elegir a un compañero al consultar su bitácora (M4-01) o filtrar el histórico (M4-02) sin tener que conocer su identificador. Es el MÍNIMO necesario: por integrante, solo
``persona_id``, ``nombre`` y ``rol`` (``colaborador`` o ``supervisor``). Nunca un correo, un identificador de acceso, datos de autenticación ni historial de pertenencias.

Autorización: cualquier persona que pueda operar (sesión y acceso efectivo: ``operador``). Solo ve a los integrantes de SU equipo, con la misma expresión de pertenencia que usa el
resto de la política de M1 (``pertenencia_del_equipo``): una persona de otro equipo u organización no se enumera nunca y un equipo ajeno no se puede pedir (no hay parámetro de equipo).

Quién aparece: quien tiene una pertenencia que cubre HOY (también quien tiene el acceso desactivado, porque sus registros siguen siendo consultables por su equipo: CA-30, CA-256).
**Limitación aprobada:** quien ya salió del equipo NO aparece, aunque sus registros históricos sigan siendo consultables (M4-01 y M4-02 por rango); no hay directorio histórico.
Listado paginado según convenciones 6.1 (orden por nombre e identificador).
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido import paginacion
from app.compartido.dependencias import Operador
from app.compartido.visibilidad import consultante_de
from app.modulos.consulta import repositorio

PARAMETROS_DE_INTEGRANTES = frozenset({"limite", "continuar_desde"})


def consultar_integrantes(db: Session, op: Operador, consulta: list[tuple[str, str]]) -> dict:
    parametros = paginacion.leer_parametros(consulta, PARAMETROS_DE_INTEGRANTES)         # formato antes que los datos (convenciones 3.2)
    cantidad = paginacion.limite_de(parametros.get("limite"))
    cursor = paginacion.leer_cursor(parametros.get("continuar_desde"), str, UUID)

    consultante = consultante_de(db, op.persona_id, hoy=op.contexto.fecha_actual)
    filas = repositorio.integrantes_vigentes(db, consultante, op.contexto.fecha_actual, cursor, cantidad + 1)
    pagina = filas[:cantidad]
    return {
        "elementos": [{"persona_id": str(f.persona_id), "nombre": f.nombre, "rol": f.rol} for f in pagina],
        "siguiente": paginacion.emitir_cursor(pagina[-1].nombre, str(pagina[-1].persona_id)) if len(filas) > cantidad else None,
    }
