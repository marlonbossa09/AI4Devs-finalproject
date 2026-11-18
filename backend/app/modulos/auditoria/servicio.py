"""M3-07: consultar la auditoría de un registro (solo lectura). La autorizan la propietaria y, desde M4-T6, el supervisor vigente del equipo del registro por su fecha laboral (RA-10, CA-111)."""

import base64
import binascii
import json
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador
from app.compartido.visibilidad import EntradaDeAuditoria, consultante_de, decidir_lectura_de_auditoria
from app.config import get_settings
from app.errores import AppError
from app.modulos.auditoria import repositorio
from app.modulos.bitacoras.esquemas import momento

# Tipos de registro cuya auditoría se consulta, tal como viajan (sin acentos). La planificación admite la consulta
# aunque hoy ninguna operación la audita: no hay edición de planificaciones (IR-16).
TIPOS_OBJETO = frozenset({"bitacora", "actividad", "avance", "planificacion"})

# Operaciones de dominio hechas por personas, las únicas que esta consulta devuelve. Las de provisión
# administrativa (alta, cambio de pertenencia, accesos...) permanecen aparte (D-11) y no son un filtro válido.
OPERACIONES = frozenset({
    "cierre", "reapertura", "correccion", "modificacion_jornada_pasada", "reactivacion", "marca_error",
    "reversion_marca",
})

# Parámetros que admite M3-07. Cualquier otro se rechaza: no hay búsquedas ni filtros que el producto no contemple
# (convenciones 2) ni un listado global.
PARAMETROS = frozenset({"tipo_objeto", "objeto_id", "operacion", "limite", "continuar_desde"})


def _invalida(campo: str, motivo: str, **extra: object) -> AppError:
    return AppError("SOLICITUD_INVALIDA", [{"campo": campo, "motivo": motivo, **extra}])


def _limite_de(valor: str | None) -> int:
    """``limite`` con su valor por defecto y su máximo configurables (convenciones 6.1)."""
    settings = get_settings()
    if valor is None:
        return settings.pagination_default_limit
    if not re.fullmatch(r"[0-9]{1,9}", valor) or not 1 <= int(valor) <= settings.pagination_max_limit:
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "limite", "maximo": settings.pagination_max_limit}])
    return int(valor)


def _cursor_de(valor: str | None) -> tuple[str, str] | None:
    """El cursor es opaco para quien consulta: (momento, id) de la última entrada entregada. Uno inválido se rechaza
    igual que un ``limite`` inválido (convenciones 6.1)."""
    if valor is None:
        return None
    try:
        contenido = json.loads(base64.urlsafe_b64decode(valor.encode("ascii") + b"=" * (-len(valor) % 4)))
        instante = datetime.fromisoformat(contenido["m"])
        identificador = UUID(contenido["i"])
        if instante.tzinfo is None:
            raise ValueError("sin zona horaria")
    except (ValueError, KeyError, TypeError, binascii.Error, UnicodeError):
        raise _invalida("continuar_desde", "cursor_invalido") from None
    return instante.isoformat(), str(identificador)


def _emitir_cursor(fila) -> str:
    contenido = json.dumps({"m": fila.momento.isoformat(), "i": str(fila.id)}, separators=(",", ":"))
    return base64.urlsafe_b64encode(contenido.encode("ascii")).decode("ascii").rstrip("=")


def _entrada_a_dict(fila) -> dict:
    """EntradaAuditoría (convenciones 7). Los momentos van en UTC, como el resto de la API."""
    return {
        "id": str(fila.id),
        "momento": momento(fila.momento),
        "tipo_autor": fila.tipo_autor,
        "autor_persona_id": str(fila.autor_persona_id) if fila.autor_persona_id else None,
        "operacion": fila.operacion,
        "tipo_objeto": fila.tipo_objeto,
        "objeto_id": str(fila.objeto_id),
        "propietaria_registro_id": str(fila.propietaria_registro_id),
        "fecha_laboral_registro": fila.fecha_laboral_registro.isoformat() if fila.fecha_laboral_registro else None,
        "motivo": fila.motivo,
        "valor_anterior": fila.valor_anterior,
        "valor_nuevo": fila.valor_nuevo,
    }


def consultar_auditoria(db: Session, op: Operador, parametros: dict[str, list[str]]) -> dict:
    """M3-07. La auditoría de UN registro: bitácora, actividad, avance o planificación, para quien está autorizado a verla (RA-10): su propietaria y el supervisor vigente del equipo del
    registro por su fecha laboral (CA-110, CA-111). La decisión es la de la política de M1 (``decidir_lectura_de_auditoria``) y el filtro de cada entrada, su equivalente SQL.

    Orden de evaluación (convenciones 3.2): primero el FORMATO de los parámetros, sin consultar nada; después la
    visibilidad del registro; solo entonces se leen las entradas. El filtro de autorización se aplica antes de
    construir la respuesta y antes de paginar (3.3).

    - ``tipo_objeto`` y ``objeto_id`` son obligatorios: no existe consulta sin objeto ni listado global.
    - Un registro inexistente y uno que quien consulta no está autorizado a ver (un compañero que no es la propietaria ni el supervisor, o el supervisor de otro equipo, o uno
      trasladado o sin rol vigente) responden lo mismo, ``RECURSO_NO_DISPONIBLE``, sin revelar si existe (CA-112, CA-113, CA-286).
    - Solo se devuelven entradas hechas por personas; las de provisión no aparecen (CA-285, D-11).
    - Cada entrada trae lo necesario para reconstruir el cambio: autor, momento real, operación, motivo, valor
      anterior y nuevo, y la fecha laboral del registro (CA-106, CA-108, CA-109). Una operación que modifica varios
      campos es una sola entrada (CA-267). Las operaciones sin cambios no generan entradas, así que no aparecen.
    - Es solo lectura: no escribe nada ni genera entradas de auditoría."""
    for nombre in sorted(set(parametros) - PARAMETROS):
        raise _invalida(nombre, "parametro_no_soportado")
    for nombre, valores in parametros.items():
        if len(valores) != 1:
            raise _invalida(nombre, "parametro_repetido")
    unico = {nombre: valores[0] for nombre, valores in parametros.items()}

    for obligatorio in ("tipo_objeto", "objeto_id"):
        if not unico.get(obligatorio):
            raise _invalida(obligatorio, "obligatorio")
    tipo_objeto = unico["tipo_objeto"]
    if tipo_objeto not in TIPOS_OBJETO:
        raise _invalida("tipo_objeto", "tipo_no_valido")
    try:
        objeto_id = UUID(unico["objeto_id"])
    except ValueError:
        raise _invalida("objeto_id", "identificador_no_valido") from None
    operacion = unico.get("operacion")
    if operacion is not None and operacion not in OPERACIONES:
        raise _invalida("operacion", "operacion_no_valida")
    cantidad = _limite_de(unico.get("limite"))
    cursor = _cursor_de(unico.get("continuar_desde"))

    # La autorización se decide ANTES de leer ninguna entrada, con la política compartida de M1 y la fecha laboral del propio registro; las entradas se vuelven a filtrar al
    # seleccionarlas (``condicion_lectura_auditoria``), así que ni la lista, ni el orden, ni el cursor, ni ``siguiente`` dependen de lo que no se puede ver.
    registro = repositorio.propietaria_y_fecha_del_registro(db, tipo_objeto, objeto_id)
    consultante = consultante_de(db, op.persona_id, hoy=op.contexto.fecha_actual)
    if registro is None or not decidir_lectura_de_auditoria(db, consultante, EntradaDeAuditoria(registro.propietaria_id, registro.fecha_laboral, "persona")).visible:
        raise AppError("RECURSO_NO_DISPONIBLE")

    filas = repositorio.listar_entradas(db, consultante, tipo_objeto, objeto_id, operacion, cursor, cantidad + 1)
    pagina = filas[:cantidad]
    return {
        "elementos": [_entrada_a_dict(f) for f in pagina],
        "siguiente": _emitir_cursor(pagina[-1]) if len(filas) > cantidad else None,
    }
