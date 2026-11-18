"""M5-T3 — validación DETERMINISTA de la salida de un generador contra la entrada que recibió (ADR-003, secciones 8 y 9; RF-32, RN-31, RN-58).

LO QUE COMPRUEBA (todo mecánico, sin IA):

Estructura (fallo = ``RESPUESTA_MALFORMADA``): la salida es un objeto con EXACTAMENTE ``version``, ``secciones`` y ``uso``; ``version`` es la del contrato; ``secciones`` es una lista no vacía de objetos con
EXACTAMENTE ``texto`` (cadena no vacía) y ``refs`` (lista no vacía de cadenas); ``uso`` tiene EXACTAMENTE ``tokens_entrada`` y ``tokens_salida`` (enteros no negativos). Cualquier campo desconocido o ausente, o de
otro tipo, se rechaza: el esquema es cerrado. No se fija ninguna longitud máxima porque no está definida contractualmente (D-M5-06 abierta).

Contenido (fallo = ``RECHAZADA_POR_VALIDACION``, con todos los motivos que apliquen):
- ``referencia_inexistente``: una ``ref`` que no es de un hecho de la entrada.
- ``contenido_no_admitido``: enlaces, marcado (HTML o Markdown de enlace e imagen, bloques de código), correos o identificadores con forma de UUID: el texto es texto plano (ADR-003, sección 8).
- ``porcentaje``: cualquier «%» (los informes no llevan porcentajes: RN-57).
- ``alias_no_autorizado``: un alias de persona distinto del recibido.
- ``fecha_no_autorizada``: una fecha ISO que no es la de ningún hecho ni el límite del período.
- ``cifra_no_autorizada``: un número que no es ninguna métrica calculada, ni el número de hechos, ni un número que aparezca en los propios registros de la entrada (por ejemplo, el de un título citado).
- ``cifra_contradictoria``: un número seguido de «avances» o de «jornadas» que no coincide con la métrica correspondiente.

LO QUE NO GARANTIZA (riesgo residual, documentado en ``docs/api/m5-integracion-ia.md``): que el texto no contenga valoraciones subjetivas, tono evaluativo ni juicios sobre personas (RF-47); que cada frase sea
fiel a los registros que cita (solo se comprueba que las referencias existan, no que digan lo que el texto afirma); que no aparezcan nombres propios o hechos plausibles pero inventados escritos en letra; ni que
el texto libre citado no contenga datos sensibles. Eso se verifica con una evaluación por muestras (D-M5-05), no con este validador. Una cifra escrita con letras («tres avances») no se detecta.

El validador NO modifica nada: devuelve una salida nueva o lanza ``ErrorDeGeneracion`` con motivos de un vocabulario fijo, sin copiar ningún fragmento del texto.
"""

import re

from app.modulos.informes.generacion import (
    Clase, EntradaDeGeneracion, ErrorDeGeneracion, SalidaDeGeneracion, SeccionDeNarrativa, UsoDeTokens, VERSION_DEL_CONTRATO,
)

_ALIAS = re.compile(r"\bPersona\s+(\d+)\b")
_FECHA_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_NUMERO = re.compile(r"(?<!\w)\d+(?!\w)")
_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ENLACE_O_MARCADO = re.compile(r"https?://|www\.|javascript:|[<>]|\]\(|!\[|`", re.IGNORECASE)
_AVANCES = re.compile(r"(?<!\w)(\d+)\s+avances?\b", re.IGNORECASE)
_JORNADAS = re.compile(r"(?<!\w)(\d+)\s+jornadas?\b", re.IGNORECASE)


def _malformada(motivo: str) -> ErrorDeGeneracion:
    return ErrorDeGeneracion(Clase.RESPUESTA_MALFORMADA, (motivo,))


def _es_entero(valor: object) -> bool:
    return type(valor) is int and valor >= 0                       # ``True`` no es un entero válido


def _estructura(bruta: object) -> tuple[list[tuple[str, tuple[str, ...]]], tuple[int, int]]:
    if not isinstance(bruta, dict):
        raise _malformada("no_es_un_objeto")
    esperadas = {"version", "secciones", "uso"}
    if set(bruta) - esperadas:
        raise _malformada("campo_desconocido")
    if esperadas - set(bruta):
        raise _malformada("campo_faltante")
    if bruta["version"] != VERSION_DEL_CONTRATO:
        raise _malformada("version_no_admitida")
    secciones = bruta["secciones"]
    if not isinstance(secciones, list) or not secciones:
        raise _malformada("secciones_invalidas")
    resultado: list[tuple[str, tuple[str, ...]]] = []
    for s in secciones:
        if not isinstance(s, dict):
            raise _malformada("seccion_no_es_un_objeto")
        if set(s) - {"texto", "refs"}:
            raise _malformada("campo_desconocido")
        if {"texto", "refs"} - set(s):
            raise _malformada("campo_faltante")
        if not isinstance(s["texto"], str) or not s["texto"].strip():
            raise _malformada("texto_invalido")
        if not isinstance(s["refs"], list) or not s["refs"] or not all(isinstance(r, str) for r in s["refs"]):
            raise _malformada("refs_invalidas")
        resultado.append((s["texto"], tuple(s["refs"])))
    uso = bruta["uso"]
    if not isinstance(uso, dict):
        raise _malformada("uso_invalido")
    if set(uso) - {"tokens_entrada", "tokens_salida"}:
        raise _malformada("campo_desconocido")
    if {"tokens_entrada", "tokens_salida"} - set(uso):
        raise _malformada("campo_faltante")
    if not _es_entero(uso["tokens_entrada"]) or not _es_entero(uso["tokens_salida"]):
        raise _malformada("uso_invalido")
    return resultado, (uso["tokens_entrada"], uso["tokens_salida"])


def _numeros_de(valor: object, acumulado: set[int]) -> None:
    if isinstance(valor, dict):
        for v in valor.values():
            _numeros_de(v, acumulado)
    elif type(valor) is int:
        acumulado.add(valor)


def _cifras_permitidas(entrada: EntradaDeGeneracion) -> set[int]:
    permitidas: set[int] = {len(entrada.hechos)}
    _numeros_de(entrada.metricas, permitidas)
    textos = [a.texto for a in entrada.actividades] + [h.descripcion for h in entrada.hechos] + [h.motivo_bloqueo or "" for h in entrada.hechos]
    for t in textos:
        permitidas.update(int(n) for n in _NUMERO.findall(t))
    return permitidas


def validar_salida(bruta: object, entrada: EntradaDeGeneracion) -> SalidaDeGeneracion:
    """Devuelve la salida validada o lanza ``ErrorDeGeneracion``. No modifica ``entrada`` (inmutable) ni ``bruta``."""
    secciones, (tokens_entrada, tokens_salida) = _estructura(bruta)

    motivos: set[str] = set()
    refs_de_la_entrada = {h.ref for h in entrada.hechos}
    fechas_permitidas = {h.fecha_laboral.isoformat() for h in entrada.hechos} | {entrada.desde.isoformat(), entrada.hasta.isoformat()}
    numero_de_alias = entrada.alias.split()[-1]
    cifras = _cifras_permitidas(entrada)
    metricas = entrada.metricas
    for texto, refs in secciones:
        if not set(refs) <= refs_de_la_entrada:
            motivos.add("referencia_inexistente")
        if _ENLACE_O_MARCADO.search(texto) or _CORREO.search(texto) or _UUID.search(texto):
            motivos.add("contenido_no_admitido")
        if "%" in texto:
            motivos.add("porcentaje")
        if any(n != numero_de_alias for n in _ALIAS.findall(texto)):
            motivos.add("alias_no_autorizado")
        if any(f not in fechas_permitidas for f in _FECHA_ISO.findall(texto)):
            motivos.add("fecha_no_autorizada")
        # las cifras se buscan sin los alias («Persona 1») ni las fechas, cuyos dígitos tienen su propia comprobación
        limpio = _FECHA_ISO.sub(" ", _ALIAS.sub(" ", _UUID.sub(" ", texto)))
        if any(int(n) not in cifras for n in _NUMERO.findall(limpio)):
            motivos.add("cifra_no_autorizada")
        if any(int(n) != metricas["avances"] for n in _AVANCES.findall(limpio)) or any(int(n) != metricas["jornadas_con_registros"] for n in _JORNADAS.findall(limpio)):
            motivos.add("cifra_contradictoria")
    if motivos:
        raise ErrorDeGeneracion(Clase.RECHAZADA_POR_VALIDACION, tuple(sorted(motivos)))
    return SalidaDeGeneracion(tuple(SeccionDeNarrativa(t, r) for t, r in secciones), UsoDeTokens(tokens_entrada, tokens_salida))
