"""Parámetros de listado de M4: ``limite``, cursor opaco y rango de fechas (convenciones 6.1 y 9; D-M4-08, D-M4-03, D-M4-04).

Utilidad NUEVA y reutilizable por las consultas de M4 (histórico y vista de supervisión). M2 y M3 tienen sus propias funciones privadas de
paginación y no se refactorizan (D-M4-08): aquí no se importa nada de ellos.

- **Parámetros** (``leer_parametros``): solo los admitidos por el contrato; uno desconocido o repetido es ``SOLICITUD_INVALIDA``. No hay búsqueda por texto
  ni otros filtros (CA-136).
- **``limite``** con su valor por defecto y su máximo configurables; uno inválido o superior al máximo se rechaza con el máximo en ``detalles``.
- **Cursor opaco** (``emitir_cursor`` y ``leer_cursor``): la posición del último elemento entregado, es decir, las claves de su orden. Es solo una POSICIÓN: la
  autorización se aplica siempre al seleccionar, así que un cursor fabricado no puede entregar nada que la consulta no entregaría. Uno inválido (no es base64
  de JSON, no tiene las claves esperadas o alguna no se convierte) se rechaza igual que un ``limite`` inválido.
- **Rango de fechas laborales** (``rango_de_fechas``): ``desde`` y ``hasta`` obligatorios, ``desde`` ≤ ``hasta``, ``hasta`` puede ser futuro (D-M4-04) y la amplitud
  (``hasta - desde + 1`` días, extremos incluidos) no supera ``QUERY_MAX_RANGE_DAYS`` (por defecto 92).
"""

import base64
import binascii
import json
import re
from collections.abc import Callable, Iterable
from datetime import date

from app.compartido.fechas import parsear_fecha_laboral
from app.config import get_settings
from app.errores import AppError


def _invalida(campo: str, motivo: str, **extra: object) -> AppError:
    return AppError("SOLICITUD_INVALIDA", [{"campo": campo, "motivo": motivo, **extra}])


def leer_parametros(consulta: Iterable[tuple[str, str]], permitidos: frozenset[str]) -> dict[str, str]:
    """Los parámetros de consulta como diccionario, rechazando los no admitidos y los repetidos. Es lo primero que se valida (convenciones 3.2)."""
    vistos: dict[str, str] = {}
    for nombre, valor in consulta:
        if nombre not in permitidos:
            raise _invalida(nombre, "parametro_no_soportado")
        if nombre in vistos:
            raise _invalida(nombre, "parametro_repetido")
        vistos[nombre] = valor
    return vistos


def limite_de(valor: str | None) -> int:
    """``limite`` con su valor por defecto y su máximo configurables (convenciones 6.1)."""
    ajustes = get_settings()
    if valor is None:
        return ajustes.pagination_default_limit
    if not re.fullmatch(r"[0-9]{1,9}", valor) or not 1 <= int(valor) <= ajustes.pagination_max_limit:
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "limite", "maximo": ajustes.pagination_max_limit}])
    return int(valor)


def emitir_cursor(*claves: str) -> str:
    """Cursor opaco con las claves (texto) de la posición del último elemento entregado."""
    return base64.urlsafe_b64encode(json.dumps(list(claves), separators=(",", ":")).encode("utf-8")).decode("ascii").rstrip("=")


def leer_cursor(valor: str | None, *convertidores: Callable[[str], object]) -> tuple | None:
    """Las claves del cursor convertidas, o ``None`` si no hay cursor. Un cursor que no es exactamente una lista de ``len(convertidores)`` textos
    convertibles se rechaza (``SOLICITUD_INVALIDA``, campo ``continuar_desde``)."""
    if valor is None:
        return None
    try:
        contenido = json.loads(base64.urlsafe_b64decode(valor.encode("ascii") + b"=" * (-len(valor) % 4)))
        if not isinstance(contenido, list) or len(contenido) != len(convertidores) or not all(isinstance(c, str) for c in contenido):
            raise ValueError("forma del cursor")
        return tuple(convertir(clave) for convertir, clave in zip(convertidores, contenido))
    except (ValueError, TypeError, binascii.Error, UnicodeError):
        raise _invalida("continuar_desde", "cursor_invalido") from None


def rango_de_fechas(parametros: dict[str, str]) -> tuple[date, date]:
    """``(desde, hasta)`` validados (D-08, D-M4-03, D-M4-04): obligatorios, ``desde`` ≤ ``hasta`` y amplitud máxima configurable. ``hasta`` puede ser futuro."""
    for nombre in ("desde", "hasta"):
        if not parametros.get(nombre):
            raise _invalida(nombre, "obligatorio")
    desde = parsear_fecha_laboral(parametros["desde"], "desde")
    hasta = parsear_fecha_laboral(parametros["hasta"], "hasta")
    if desde > hasta:
        raise _invalida("desde", "posterior_a_hasta")
    maximo = get_settings().query_max_range_days
    if (hasta - desde).days + 1 > maximo:
        raise _invalida("hasta", "rango_excede_el_maximo", maximo_dias=maximo)
    return desde, hasta
