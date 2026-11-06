"""Normalización del identificador de acceso (ADR-002, sección 4).

El identificador no es un dato de contacto. Se normaliza (Unicode NFKC, sin espacios en los
extremos y en minúsculas) para que 'Ana' y 'ana' sean el mismo identificador.
"""

import unicodedata


def normalizar_identificador(valor: str) -> str:
    return unicodedata.normalize("NFKC", valor).strip().lower()
