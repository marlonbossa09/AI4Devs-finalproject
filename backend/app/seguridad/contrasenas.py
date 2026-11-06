"""Contraseñas con Argon2id (ADR-002, sección 3).

Los costes se leen de la configuración (mínimos de referencia de OWASP: 19 MiB, 2 iteraciones,
paralelismo 1). La cadena resultante incluye sus parámetros, de modo que se puede recalcular al
subirlos. Nunca se registra ni se devuelve una contraseña.
"""

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings


@lru_cache
def _hasher() -> PasswordHasher:
    s = get_settings()
    return PasswordHasher(
        time_cost=s.argon2_iterations,
        memory_cost=s.argon2_memory_kib,
        parallelism=s.argon2_parallelism,
    )


def calcular_hash(contrasena: str) -> str:
    return _hasher().hash(contrasena)


def verificar(hash_guardado: str, contrasena: str) -> bool:
    try:
        return _hasher().verify(hash_guardado, contrasena)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def necesita_recalculo(hash_guardado: str) -> bool:
    return _hasher().check_needs_rehash(hash_guardado)


@lru_cache
def hash_senuelo() -> str:
    """Hash de una contraseña aleatoria, para verificar contra él cuando el identificador no
    existe y así igualar el tiempo de respuesta (sin enumeración de identificadores)."""
    return calcular_hash("senuelo-sin-uso-" + "x" * 16)
