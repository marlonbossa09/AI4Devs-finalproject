"""M5-T5 — destinos LOCALES autorizados para un generador de IA que corre en la misma máquina (Ollama). La URL del proveedor viene de la configuración y NO puede convertir al backend en un proxy HTTP arbitrario hacia
otro equipo, otra red o internet: solo se admite ``http://`` hacia la propia máquina (``127.0.0.1``, ``localhost`` o ``::1``) con puerto explícito, sin credenciales en la URL, sin ruta, sin parámetros y sin fragmento.
Las rutas de la API del proveedor las fija el adaptador, no la configuración. Es puro (sin red): se puede probar sin ningún servicio.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

ANFITRIONES_LOCALES = frozenset({"127.0.0.1", "localhost", "::1"})
_CONTROL_O_ESPACIO = re.compile(r"[\s\x00-\x1f\x7f]")


@dataclass(frozen=True)
class DestinoLocal:
    anfitrion: str
    puerto: int

    @property
    def url(self) -> str:
        return f"http://[{self.anfitrion}]:{self.puerto}" if ":" in self.anfitrion else f"http://{self.anfitrion}:{self.puerto}"


def validar_destino_local(url: str) -> DestinoLocal:
    """Devuelve el destino o lanza ``ValueError`` con un mensaje FIJO (nunca el valor recibido: podría llevar credenciales)."""
    if not isinstance(url, str) or not url or _CONTROL_O_ESPACIO.search(url):
        raise ValueError("La URL del generador local no es válida")
    try:
        partes = urlsplit(url)
        puerto = partes.port
        anfitrion = partes.hostname
    except ValueError:
        raise ValueError("La URL del generador local no es válida") from None
    if partes.scheme != "http":
        raise ValueError("La URL del generador local debe usar http (solo se admite el destino local)")
    if anfitrion is None or anfitrion.lower() not in ANFITRIONES_LOCALES:
        raise ValueError("La URL del generador local solo puede apuntar a la propia máquina: 127.0.0.1, localhost o ::1")
    if partes.username is not None or partes.password is not None:
        raise ValueError("La URL del generador local no puede llevar credenciales")
    if partes.path not in ("", "/") or partes.query or partes.fragment:
        raise ValueError("La URL del generador local no puede llevar ruta, parámetros ni fragmento")
    if puerto is None or not 1 <= puerto <= 65535:
        raise ValueError("La URL del generador local debe indicar el puerto")
    return DestinoLocal(anfitrion.lower(), puerto)
