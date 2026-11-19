"""Adaptador de generación con OpenRouter (decisión de la persona responsable en la sesión del 2026-11-19: usar OpenRouter con un modelo gratuito para ver una narrativa real en el entorno de DESARROLLO).

Implementa la interfaz ``GeneradorDeTexto`` sin cambiar el contrato interno ni los públicos: recibe la ``EntradaDeGeneracion`` de campos cerrados y devuelve la salida BRUTA, que el dominio vuelve a validar SIEMPRE con
``validacion.validar_salida`` (este adaptador no valida el contenido ni confía en el modelo). Reutiliza las instrucciones fijas, el esquema y el formato de datos del adaptador local para que ambos pidan exactamente lo mismo.

SEGURIDAD Y PRIVACIDAD (a diferencia de Ollama, aquí los datos SALEN de la máquina).
- Solo desarrollo y pruebas (``config``): se rechaza en cualquier otro entorno. Solo datos FICTICIOS: los datos laborales reales con un modelo de lenguaje siguen NO autorizados (D-M5-08). Un modelo gratuito de un tercero
  puede registrar o reutilizar lo que recibe; por eso lo que sale es lo mínimo del contrato interno: alias en lugar del nombre, sin identificadores de la base de datos y sin datos de acceso.
- Destino FIJO: ``https://openrouter.ai``, por TLS con verificación de certificado, ruta fija y sin redirecciones ni proxies del entorno. La URL no es configurable.
- La clave se lee de ``INFORME_OPENROUTER_API_KEY`` (secreto del entorno, nunca versionado). Solo viaja en la cabecera ``Authorization``; no se registra, no se incluye en mensajes de error ni se devuelve al cliente.
- Los textos laborales NUNCA van en las instrucciones del sistema (constante fija); viajan como un único objeto JSON delimitado, con ``<`` y ``>`` escapados.
- Ni el prompt ni la respuesta ni los textos laborales se registran. Los fallos se declaran con mensajes FIJOS: el cuerpo de error del servicio no se propaga.
- Sin alternativa silenciosa: si OpenRouter falla, es un fallo; nunca se usa otro proveedor ni el simulado.

FALLOS. Sin conexión, 429 o error del servicio: ``GeneradorNoDisponible`` (transitorio). Plazo agotado: ``TiempoAgotado``. Clave rechazada (401/403) o modelo inexistente (404): ``GeneradorNoConfigurado`` (no es transitorio).
Cuerpo ilegible o sin contenido: se devuelve ``None`` y el validador lo rechaza como respuesta malformada.

LÍMITES (riesgo, no garantía): un modelo gratuito puede incumplir con frecuencia las reglas del validador (cifras, referencias, fechas), cambiar de modelo o desaparecer, y la calidad en español no está garantizada.
"""

import http.client
import json
import re
import ssl
from collections.abc import Callable

from app.modulos.informes.generacion import (
    EntradaDeGeneracion, GeneradorNoConfigurado, GeneradorNoDisponible, TiempoAgotado, VERSION_DEL_CONTRATO,
)
from app.modulos.informes.generador_ollama import INSTRUCCIONES_DEL_SISTEMA, esquema_de_salida, mensaje_de_datos

ANFITRION = "openrouter.ai"
RUTA_CHAT = "/api/v1/chat/completions"
MAX_RESPUESTA_BYTES = 1_000_000
MAX_TOKENS_DE_SALIDA = 4096                   # tope técnico de desarrollo (los modelos con razonamiento gastan parte en pensar): NO confirma el parámetro abierto de D-M5-06

Transporte = Callable[[str, str, bytes, dict, float], tuple[int, bytes]]


def _transporte_https(anfitrion: str, ruta: str, cuerpo: bytes, cabeceras: dict, plazo: float) -> tuple[int, bytes]:
    """Transporte por defecto: ``http.client`` por TLS verificado. Sin redirecciones, sin proxies del entorno y con la respuesta acotada."""
    conexion = http.client.HTTPSConnection(anfitrion, 443, timeout=plazo, context=ssl.create_default_context())
    try:
        conexion.request("POST", ruta, body=cuerpo, headers=cabeceras)
        respuesta = conexion.getresponse()
        return respuesta.status, respuesta.read(MAX_RESPUESTA_BYTES + 1)
    finally:
        conexion.close()


_VALLA = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


class GeneradorOpenRouter:
    """Ver el docstring del módulo. ``transporte`` solo se sustituye en las pruebas."""

    def __init__(self, clave: str, modelo: str, plazo_segundos: float, transporte: Transporte | None = None) -> None:
        if not clave or not clave.strip() or not modelo or not modelo.strip() or plazo_segundos <= 0:
            raise ValueError("Configuración del generador de OpenRouter no válida")
        # ``modelo`` puede ser una lista separada por comas: OpenRouter prueba los modelos EN ESE ORDEN si el primero no está disponible o está limitado (sigue siendo UN solo proveedor).
        self._modelos = [m.strip() for m in modelo.split(",") if m.strip()]
        if not self._modelos or len(self._modelos) > 3:                                         # OpenRouter admite como máximo 3 modelos en la lista
            raise ValueError("Configuración del generador de OpenRouter no válida")
        self._clave, self._modelo, self._plazo = clave.strip(), ",".join(self._modelos), float(plazo_segundos)
        self._transporte = transporte or _transporte_https

    def __repr__(self) -> str:                                                                  # la clave nunca aparece en una representación
        return f"GeneradorOpenRouter(modelo={self._modelo!r})"

    def generar(self, entrada: EntradaDeGeneracion) -> object:
        datos = entrada.a_diccionario()
        esquema = esquema_de_salida([h["ref"] for h in datos["hechos"]])
        instrucciones = INSTRUCCIONES_DEL_SISTEMA + "\nEl esquema JSON que debes cumplir es: " + json.dumps(esquema, ensure_ascii=False, separators=(",", ":"))
        cuerpo = json.dumps({
            **({"model": self._modelos[0]} if len(self._modelos) == 1 else {"models": self._modelos}), "stream": False, "temperature": 0, "max_tokens": MAX_TOKENS_DE_SALIDA,
            "response_format": {"type": "json_object"}, "reasoning": {"effort": "low"},
            "messages": [{"role": "system", "content": instrucciones}, {"role": "user", "content": mensaje_de_datos(datos)}],
        }, ensure_ascii=False).encode("utf-8")
        cabeceras = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Bearer {self._clave}", "X-Title": "SMARTWORK"}
        try:
            estado, crudo = self._transporte(ANFITRION, RUTA_CHAT, cuerpo, cabeceras, self._plazo)
        except TimeoutError:
            raise TiempoAgotado("plazo agotado") from None
        except (OSError, http.client.HTTPException):
            raise GeneradorNoDisponible("generador remoto no disponible") from None
        if estado in (401, 403, 404):
            raise GeneradorNoConfigurado("clave o modelo no admitidos por el generador remoto")
        if estado != 200:
            raise GeneradorNoDisponible("el generador remoto respondió con un error")
        return self._interpretar(crudo)

    @staticmethod
    def _interpretar(crudo: bytes) -> object:
        if len(crudo) > MAX_RESPUESTA_BYTES:
            return None
        try:
            respuesta = json.loads(crudo)
        except ValueError:
            return None
        if not isinstance(respuesta, dict) or respuesta.get("error"):                           # OpenRouter puede devolver 200 con un cuerpo de error del proveedor
            return None
        opciones = respuesta.get("choices")
        mensaje = opciones[0].get("message") if isinstance(opciones, list) and opciones and isinstance(opciones[0], dict) else None
        contenido = mensaje.get("content") if isinstance(mensaje, dict) else None
        if not isinstance(contenido, str):
            return None
        valla = _VALLA.match(contenido)
        try:
            del_modelo = json.loads(valla.group(1) if valla else contenido)
        except ValueError:
            return contenido                                                                    # no es JSON: el validador lo rechaza como no objeto
        if not isinstance(del_modelo, dict):
            return del_modelo
        if set(del_modelo) - {"secciones"}:                                                     # al modelo solo se le pide ``secciones``: cualquier otro campo es inesperado y el validador lo rechaza
            return {**del_modelo, "campos_no_pedidos_al_modelo": True}
        uso = respuesta.get("usage") if isinstance(respuesta.get("usage"), dict) else {}
        entrada, salida = uso.get("prompt_tokens"), uso.get("completion_tokens")
        return {**del_modelo, "version": VERSION_DEL_CONTRATO,
                "uso": {"tokens_entrada": entrada if type(entrada) is int and entrada >= 0 else 0, "tokens_salida": salida if type(salida) is int and salida >= 0 else 0}}
