"""SOLO PARA PRUEBAS: la aplicación PRINCIPAL de SMARTWORK (``app.main:app``, con las rutas de informes ya registradas) más UNA sustitución de prueba: si existe la variable de entorno ``PRUEBA_MODO_GENERADOR``, el generador
de informes es el simulado en ese modo (por ejemplo, una salida malformada). Sirve a ``test_informes_http_real`` para provocar, a través de un socket real, un fallo del generador que la configuración real no permite
elegir a propósito. Sin esa variable es exactamente la aplicación principal.
"""

import os

from app.main import app
from app.modulos.informes.generador_simulado import GeneradorSimulado
from app.modulos.informes.router import obtener_generador

_modo = os.environ.get("PRUEBA_MODO_GENERADOR")
if _modo:
    app.dependency_overrides[obtener_generador] = lambda: GeneradorSimulado(_modo)
