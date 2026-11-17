"""Códigos de un solo uso de primer acceso y recuperación (M1-T8.1; ADR-002, secciones 4, 6 y 8; decisiones A4 y D1 del 2026-11-17).

- **128 bits** de un generador criptográfico (``secrets``). Se escribe y se dicta con 26 caracteres del alfabeto Crockford Base32 (sin
  ``I``, ``L``, ``O`` ni ``U``), agrupados con guiones. La representación (alfabeto y agrupación) es una decisión de presentación
  ``[PROPUESTO]`` pendiente de confirmar antes de mostrarla (T8.2); no cambia la entropía ni lo que se guarda.
- **Solo se guarda un HMAC-SHA256** del código (64 hexadecimales), con un secreto propio, ``CODE_PEPPER``, INDEPENDIENTE de ``AUTH_PEPPER`` y no
  versionado. El código en claro solo existe en la terminal de quien lo emite y en el canje.
- Entrada tolerante, canónica por dentro: ``normalizar`` acepta minúsculas, guiones y espacios, y las confusiones habituales (``I``/``L`` por
  ``1`` y ``O`` por ``0``); rechaza cualquier otra cosa, otra longitud y cualquier codificación no canónica, de modo que cada código tiene una
  única forma y un único hash.
- Este módulo es puro: no toca la base de datos ni ningún reloj. Los estados (vigencia, uso único, invalidación, intentos) los garantiza
  PostgreSQL con su propio reloj (migración 0014).
"""

import hashlib
import hmac
import secrets

from app.config import get_settings

ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"          # Crockford Base32
BITS = 128
LONGITUD = 26                                          # 26 caracteres * 5 bits = 130 bits: 128 de código y 2 de relleno a cero
_DOMINIO = b"smartwork-codigo-unico-v1"
_CONFUSIONES = str.maketrans({"I": "1", "L": "1", "O": "0"})


class SecretoDeCodigosNoConfigurado(RuntimeError):
    """Falta ``CODE_PEPPER``: sin él no se puede generar ni comprobar un código y se falla cerrado."""


def _secreto() -> bytes:
    s = get_settings().code_pepper
    if s is None:
        raise SecretoDeCodigosNoConfigurado("Falta CODE_PEPPER: los códigos de un solo uso no pueden funcionar sin él")
    return s.get_secret_value().encode("utf-8")


def _codificar(octetos: bytes) -> str:
    valor = int.from_bytes(octetos, "big") << (LONGITUD * 5 - BITS)
    return "".join(ALFABETO[(valor >> (5 * (LONGITUD - 1 - i))) & 31] for i in range(LONGITUD))


def generar_octetos() -> bytes:
    """Los 128 bits aleatorios de un código nuevo."""
    return secrets.token_bytes(BITS // 8)


def generar_codigo() -> str:
    """Un código nuevo en su forma canónica (26 caracteres, sin guiones)."""
    return _codificar(generar_octetos())


def generar_codigo_y_hash() -> tuple[str, str]:
    """Un código nuevo (canónico) y su HMAC: lo único que llega a la base es el segundo."""
    octetos = generar_octetos()
    return _codificar(octetos), hash_de_octetos(octetos)


def formatear(codigo: str) -> str:
    """Forma para mostrar y dictar: grupos de cinco separados por guiones (el último, de seis)."""
    return "-".join((codigo[:5], codigo[5:10], codigo[10:15], codigo[15:20], codigo[20:]))


def normalizar(texto: str) -> bytes | None:
    """Los 16 octetos de un código escrito por una persona, o ``None`` si no es un código bien formado."""
    if not isinstance(texto, str) or len(texto) > 64:
        return None
    limpio = "".join(texto.split()).replace("-", "").upper().translate(_CONFUSIONES)
    if len(limpio) != LONGITUD or any(c not in ALFABETO for c in limpio):
        return None
    valor = 0
    for c in limpio:
        valor = (valor << 5) | ALFABETO.index(c)
    if valor & ((1 << (LONGITUD * 5 - BITS)) - 1):      # los 2 bits de relleno deben ser cero: una única forma por código
        return None
    return (valor >> (LONGITUD * 5 - BITS)).to_bytes(BITS // 8, "big")


def hash_de_octetos(octetos: bytes) -> str:
    """HMAC-SHA256 (hexadecimal) con el secreto propio de los códigos y separación de dominio."""
    return hmac.new(_secreto(), _DOMINIO + b"|" + octetos, hashlib.sha256).hexdigest()


def hash_de_codigo(texto: str) -> str | None:
    """Hash de un código escrito por una persona, o ``None`` si no está bien formado (nunca llega a compararse con la base)."""
    octetos = normalizar(texto)
    return None if octetos is None else hash_de_octetos(octetos)


def hash_senuelo() -> str:
    """Hash de un código aleatorio que no existe: sirve para igualar el trabajo cuando el identificador o el código no valen (T8.3)."""
    return hash_de_octetos(generar_octetos())


def hashes_coinciden(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("ascii"), b.encode("ascii"))


def comprobar_configuracion() -> None:
    _secreto()
