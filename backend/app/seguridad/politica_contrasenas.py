"""Política de contraseñas de las personas (M1-T8.1; ADR-002, sección 7, A8; decisiones del 2026-11-17).

Confirmado: longitud mínima de 10 caracteres (parámetro ``PASSWORD_MIN_LENGTH``), SIN reglas de composición y SIN caducidad periódica.
Se cuentan caracteres Unicode tal como llegan (sin normalizar): es lo mismo que compara el inicio de sesión, que tampoco normaliza, así que una
contraseña se establece y se verifica siempre con la misma cadena. El máximo es el del inicio de sesión (``LOGIN_PASSWORD_MAX_LENGTH``).

Contraseñas comprometidas: la política recibe la comprobación como parámetro (``es_comprometida``). Las rutas de canje le pasan
``contrasenas_comprometidas.es_comprometida``, que consulta el listado LOCAL con procedencia verificada (T8.6); sin listado configurado, esa comprobación
está inactiva. Ver ``app/seguridad/contrasenas_comprometidas.py``.

Es pura: no guarda ni registra la contraseña. La usan el canje del primer acceso y el de la recuperación.
"""

from collections.abc import Callable

from app.config import get_settings

DEMASIADO_CORTA = "demasiado_corta"
DEMASIADO_LARGA = "demasiado_larga"
COMPROMETIDA = "comprometida"


class ContrasenaNoValida(ValueError):
    """La contraseña incumple la política. ``motivo`` es un código estable, nunca la contraseña."""

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(motivo)


def evaluar_contrasena(contrasena: str, *, es_comprometida: Callable[[str], bool] | None = None) -> str | None:
    """``None`` si la contraseña cumple la política; si no, el motivo (``demasiado_corta``, ``demasiado_larga`` o ``comprometida``)."""
    s = get_settings()
    if len(contrasena) < s.password_min_length:
        return DEMASIADO_CORTA
    if len(contrasena) > s.login_password_max_length:
        return DEMASIADO_LARGA
    if es_comprometida is not None and es_comprometida(contrasena):
        return COMPROMETIDA
    return None


def exigir_contrasena(contrasena: str, *, es_comprometida: Callable[[str], bool] | None = None) -> None:
    motivo = evaluar_contrasena(contrasena, es_comprometida=es_comprometida)
    if motivo is not None:
        raise ContrasenaNoValida(motivo)
