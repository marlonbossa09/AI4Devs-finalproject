"""Comprobación de contraseñas comprometidas contra Pwned Passwords instalado en LOCAL (M1-T8.6; ADR-002, sección 7 y A8).

La fuente es Pwned Passwords de Have I Been Pwned, elegida por la persona responsable del producto el 2026-11-17. Sus términos de uso permiten emplearlo, y a sus
conjuntos de hashes descargables, para cualquier fin lícito, también en productos comerciales (no se exige atribución, ni se puede revender ni construir un servicio
sustancialmente similar). Todo lo que sigue ocurre en este servidor: **durante un canje no se envía nada a ningún servicio externo**. La API de Pwned Passwords solo se usa
UNA vez, al instalar o actualizar el conjunto, con la herramienta oficial; la contraseña no sale del proceso, no se guarda y no se registra.

Formato oficial (el que escribe ``haveibeenpwned-downloader`` en modo directorio, el predeterminado): un archivo ``<PREFIJO>.txt`` por cada uno de los 16^5 = 1.048.576
prefijos hexadecimales de 5 caracteres (``00000`` a ``FFFFF``, en mayúsculas), cuyas líneas son ``<SUFIJO>:<CUENTA>`` con el sufijo de 35 caracteres hexadecimales del SHA-1 y la
cuenta de veces que apareció, ordenadas por sufijo y terminadas en CRLF. Para comprobar una contraseña se calcula su SHA-1 (de su UTF-8 tal como llega, sin normalizar: es lo que
compara el inicio de sesión), se abre el archivo de SU prefijo (unos 77 KB de media) y se busca el sufijo con una cuenta mayor que cero. No se carga el conjunto en memoria. Una
entrada con cuenta 0 (relleno) no cuenta como encontrada. No hay reglas de composición ni se normaliza nada más.

**El conjunto completo ocupa unos 81 GB** (estimación medida con una muestra de rangos: ~77 KB por rango x 1.048.576 rangos, ~2.060 millones de hashes) y NO está en el repositorio. Esta
comprobación solo se activa con una instalación COMPLETA de los 1.048.576 rangos y con su procedencia (``procedencia.json`` en el mismo directorio: fuente, URL, términos, herramienta,
fecha de obtención, formato y número de rangos). Un subconjunto no se acepta: la API no arranca. Sin directorio configurado, la comprobación está INACTIVA (solo rige la longitud
mínima) y la API lo avisa al arrancar: nunca se simula una cobertura que no existe. La cobertura es la de la fecha de obtención: no incluye filtraciones posteriores hasta actualizar.

Los mensajes de error son fijos: nunca incluyen contraseñas ni su hash.
"""

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

registro = logging.getLogger("smartwork.contrasenas_comprometidas")

TOTAL_DE_RANGOS = 16 ** 5          # 1.048.576 prefijos de 5 caracteres hexadecimales: una instalación completa los tiene todos
FORMATO = "sha1-por-rangos"
NOMBRE_DE_PROCEDENCIA = "procedencia.json"
NOMBRE_DEL_INDICE = "sha1.index"   # índice (prefijo, ETag) que escribe la herramienta oficial; opcional, sirve para actualizar y como huella de la versión instalada
FUENTE = "Have I Been Pwned: Pwned Passwords (SHA-1, un archivo por rango de 5 caracteres)"
URL_DE_LA_FUENTE = "https://haveibeenpwned.com/Passwords"
URL_DE_LOS_TERMINOS = "https://haveibeenpwned.com/termsofuse"
TERMINOS = ("Términos de uso de Have I Been Pwned (última actualización indicada: 27 de octubre de 2026): Pwned Passwords y sus conjuntos de hashes descargables pueden usarse "
            "para cualquier fin lícito, incluidos los productos comerciales; no se exige atribución para Pwned Passwords; no se pueden revender ni usar para construir un servicio "
            "sustancialmente similar.")
CAMPOS_DE_PROCEDENCIA = ("fuente", "url", "terminos_url", "terminos", "herramienta", "fecha_obtencion", "formato", "rangos")
_ARCHIVO_DE_RANGO = re.compile(r"([0-9A-F]{5})\.txt")


class ListaNoValida(Exception):
    """La instalación o su procedencia no se pueden usar. El mensaje es fijo y nunca contiene datos del conjunto ni contraseñas."""


@dataclass(frozen=True)
class Procedencia:
    fuente: str
    url: str
    terminos_url: str
    terminos: str
    herramienta: str
    fecha_obtencion: date
    formato: str
    rangos: int
    sha256_del_indice: str | None


@dataclass(frozen=True)
class Instalacion:
    directorio: Path
    procedencia: Procedencia

    def contiene(self, contrasena: str) -> bool:
        try:
            huella = hashlib.sha1(contrasena.encode("utf-8")).hexdigest().upper()
        except UnicodeEncodeError:
            return False                      # una cadena que no es UTF-8 válido no puede estar en un conjunto de hashes de UTF-8
        try:
            datos = (self.directorio / f"{huella[:5]}.txt").read_bytes()
        except OSError:
            raise ListaNoValida("Falta o no se puede leer un rango del conjunto de contraseñas comprometidas") from None
        return _contiene_sufijo(datos, huella[5:])


def _contiene_sufijo(datos: bytes, sufijo: str) -> bool:
    """``True`` si el archivo de un rango tiene la línea ``<sufijo>:<cuenta>`` con cuenta mayor que cero. Acepta CRLF y LF."""
    clave = sufijo.encode("ascii") + b":"
    if datos.startswith(clave):
        inicio = len(clave)
    else:
        i = datos.find(b"\n" + clave)
        if i < 0:
            return False
        inicio = i + 1 + len(clave)
    fin = inicio
    while fin < len(datos) and 48 <= datos[fin] <= 57:
        fin += 1
    return fin > inicio and int(datos[inicio:fin]) > 0


def _sha256_de(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def leer_procedencia(directorio: Path) -> Procedencia:
    try:
        datos = json.loads((directorio / NOMBRE_DE_PROCEDENCIA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ListaNoValida("Falta el archivo de procedencia del conjunto de contraseñas comprometidas o no es JSON válido") from None
    if not isinstance(datos, dict) or any(campo not in datos for campo in CAMPOS_DE_PROCEDENCIA):
        raise ListaNoValida("La procedencia del conjunto de contraseñas comprometidas está incompleta")
    for campo in ("fuente", "url", "terminos_url", "terminos", "herramienta", "formato"):
        if not isinstance(datos[campo], str) or not datos[campo].strip():
            raise ListaNoValida("La procedencia del conjunto de contraseñas comprometidas está incompleta")
    if datos["formato"] != FORMATO:
        raise ListaNoValida("El formato declarado del conjunto de contraseñas comprometidas no es el admitido")
    try:
        fecha = date.fromisoformat(datos["fecha_obtencion"])
    except (TypeError, ValueError):
        raise ListaNoValida("La fecha de obtención del conjunto de contraseñas comprometidas no es AAAA-MM-DD") from None
    if not isinstance(datos["rangos"], int) or isinstance(datos["rangos"], bool):
        raise ListaNoValida("El número de rangos declarado del conjunto de contraseñas comprometidas no es válido")
    huella = datos.get("sha256_del_indice")
    if huella is not None and (not isinstance(huella, str) or not re.fullmatch(r"[0-9a-f]{64}", huella)):
        raise ListaNoValida("La huella del índice del conjunto de contraseñas comprometidas no es un SHA-256 hexadecimal en minúsculas")
    return Procedencia(datos["fuente"].strip(), datos["url"].strip(), datos["terminos_url"].strip(), datos["terminos"].strip(), datos["herramienta"].strip(), fecha,
                       datos["formato"], datos["rangos"], huella)


def rangos_instalados(directorio: Path) -> list[int]:
    """Los prefijos (como número) cuyo archivo ``<PREFIJO>.txt`` existe y es menor que el total esperado. Ignora cualquier otro archivo (procedencia, índice, temporales)."""
    presentes = bytearray(TOTAL_DE_RANGOS)
    try:
        with os.scandir(directorio) as entradas:
            for e in entradas:
                m = _ARCHIVO_DE_RANGO.fullmatch(e.name)
                if m is not None and e.is_file():
                    n = int(m.group(1), 16)
                    if n < TOTAL_DE_RANGOS:
                        presentes[n] = 1
    except OSError:
        raise ListaNoValida("No se puede leer el directorio del conjunto de contraseñas comprometidas") from None
    return [i for i in range(TOTAL_DE_RANGOS) if presentes[i]]


def cargar(directorio: str | Path) -> Instalacion:
    """Verifica la instalación: procedencia completa, los 1.048.576 rangos presentes y, si hay índice, su huella. Lanza ``ListaNoValida`` si algo no cuadra."""
    ruta = Path(directorio)
    if not ruta.is_dir():
        raise ListaNoValida("El directorio del conjunto de contraseñas comprometidas no existe")
    procedencia = leer_procedencia(ruta)
    presentes = len(rangos_instalados(ruta))
    if presentes != TOTAL_DE_RANGOS or procedencia.rangos != TOTAL_DE_RANGOS:
        raise ListaNoValida(f"La instalación del conjunto de contraseñas comprometidas está incompleta: {presentes} de {TOTAL_DE_RANGOS} rangos "
                            f"(la procedencia declara {procedencia.rangos}); se exige la instalación completa")
    indice = ruta / NOMBRE_DEL_INDICE
    if procedencia.sha256_del_indice is not None:
        if not indice.is_file() or _sha256_de(indice) != procedencia.sha256_del_indice:
            raise ListaNoValida("La huella del índice del conjunto de contraseñas comprometidas no coincide con su procedencia: se actualizó o se modificó sin regenerarla")
    return Instalacion(ruta, procedencia)


def generar_procedencia(directorio: str | Path, *, herramienta: str, fecha_obtencion: date) -> Path:
    """Escribe ``procedencia.json`` con la fuente y los términos fijos, el número REAL de rangos presentes y la huella del índice si existe. Lo usa quien instala o actualiza
    el conjunto (``python -m scripts.lista_contrasenas procedencia``); ``herramienta`` es la herramienta y la versión con que se obtuvo."""
    ruta = Path(directorio)
    indice = ruta / NOMBRE_DEL_INDICE
    datos = {"fuente": FUENTE, "url": URL_DE_LA_FUENTE, "terminos_url": URL_DE_LOS_TERMINOS, "terminos": TERMINOS, "herramienta": herramienta.strip(),
             "fecha_obtencion": fecha_obtencion.isoformat(), "formato": FORMATO, "rangos": len(rangos_instalados(ruta)),
             "sha256_del_indice": _sha256_de(indice) if indice.is_file() else None}
    destino = ruta / NOMBRE_DE_PROCEDENCIA
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino


@lru_cache(maxsize=1)
def _instalacion_configurada() -> Instalacion | None:
    directorio = get_settings().compromised_passwords_dir
    return cargar(directorio) if directorio else None


def reiniciar() -> None:
    """Olvida la instalación cargada (la siguiente comprobación la vuelve a leer de la configuración). Para pruebas y para recargar al reiniciar."""
    _instalacion_configurada.cache_clear()


def comprobar_configuracion() -> Instalacion | None:
    """Al arrancar la API: si hay un directorio configurado debe ser una instalación completa y válida (si no, la API no arranca); si no hay ninguno, la comprobación está
    inactiva y se avisa."""
    instalacion = _instalacion_configurada()
    if instalacion is None:
        registro.warning("No hay conjunto de contraseñas comprometidas (COMPROMISED_PASSWORDS_DIR): la comprobación está INACTIVA; solo rige la longitud mínima.")
    else:
        p = instalacion.procedencia
        registro.info("Pwned Passwords instalado: %d rangos SHA-1 (conjunto completo a fecha %s, %s). No incluye filtraciones posteriores a esa fecha.",
                      p.rangos, p.fecha_obtencion.isoformat(), p.herramienta)
    return instalacion


def hay_listado() -> bool:
    return _instalacion_configurada() is not None


def es_comprometida(contrasena: str) -> bool:
    """``True`` si el SHA-1 de la contraseña figura en el conjunto instalado. Sin conjunto configurado devuelve ``False`` (la comprobación está inactiva)."""
    instalacion = _instalacion_configurada()
    return instalacion is not None and instalacion.contiene(contrasena)
