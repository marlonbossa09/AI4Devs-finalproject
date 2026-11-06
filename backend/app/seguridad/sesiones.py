"""Secretos de sesión y token CSRF (ADR-002, secciones 5 y 12).

- El secreto de la sesión es aleatorio (256 bits) y solo viaja en la cookie ``__Host-``. En la
  base de datos solo se guarda su hash SHA-256: una fuga de la base no entrega sesiones vivas.
- El token CSRF no se almacena: se deriva con HMAC-SHA256 del secreto de la sesión. Solo quien
  conoce el secreto (la persona, mediante su cookie HttpOnly) puede obtenerlo; conocerlo no
  permite recuperar el secreto. Es un token de sincronización asociado a la sesión.
"""

import hashlib
import hmac
import secrets

NOMBRE_COOKIE = "__Host-sesion"
CABECERA_CSRF = "X-CSRF-Token"


def generar_secreto() -> str:
    return secrets.token_urlsafe(32)


def hash_secreto(secreto: str) -> str:
    return hashlib.sha256(secreto.encode("utf-8")).hexdigest()


def token_csrf(secreto: str) -> str:
    return hmac.new(secreto.encode("utf-8"), b"smartwork-csrf-v1", hashlib.sha256).hexdigest()


def csrf_coincide(secreto: str, presentado: str | None) -> bool:
    if not presentado:
        return False
    return hmac.compare_digest(token_csrf(secreto), presentado)
