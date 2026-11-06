"""Fechas laborales (convenciones 2): formato AAAA-MM-DD, interpretadas en la zona de la organización."""

import re
from datetime import date

from app.errores import AppError

_FORMATO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parsear_fecha_laboral(valor: object, campo: str = "fecha_laboral") -> date:
    """Valida el formato estricto AAAA-MM-DD. Un formato incorrecto es SOLICITUD_INVALIDA (400)."""
    if isinstance(valor, str) and _FORMATO.match(valor):
        try:
            return date.fromisoformat(valor)
        except ValueError:
            pass
    raise AppError("SOLICITUD_INVALIDA", [{"campo": campo, "motivo": "formato_de_fecha_invalido"}])
