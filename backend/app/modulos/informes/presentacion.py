"""M5-T4 — presentación PÚBLICA de un informe: proyecciones CERRADAS del resultado interno (``servicio.ResultadoDeInforme``) a la respuesta JSON de M5-01 y M5-02. Es lo único que sale al cliente.

Estructura (borradores de contrato M5-01 y M5-02 0.2; decisiones P-3, P-5, P-11 y P-12 del 2026-11-18). Todo campo se construye a mano, uno por uno; ninguna estructura interna se serializa tal cual, así que un campo
nuevo en un modelo interno NO llega al cliente por descuido:

- ``tipo``, ``periodo`` (``desde``, ``hasta``), ``generado_en`` (momento real en UTC), ``base`` (la declaración de RF-87), ``sin_datos``.
- ``agregaciones``: las seis métricas deterministas, copiadas de ``Agregaciones`` sin recalcular ni duplicar; ``null`` si ``sin_datos``.
- ``actividades``: proyección autorizada y cerrada. ``ref`` es una referencia OPACA y LOCAL al informe (``a1``, ``a2``…), nunca el identificador de la base de datos. Forma ``completa``: ``titulo`` y ``origen`` (``planificada``
  o ``no_planificada``). Forma ``neutral``: solo ``referencia_neutral`` («Actividad en continuidad»); el origen protegido NO se muestra y el título original no sale de la base (RN-101).
- ``hechos``: los avances autorizados, cada uno con la ``actividad_ref`` de su actividad, ``fecha_laboral``, ``estado`` (el estado HISTÓRICO de ese avance), ``descripcion`` y, solo si el estado es Bloqueada, ``motivo_bloqueo``.
  Sin referencia propia del hecho: las referencias de respaldo de la narrativa son internas (PP-11 sin aprobar).
- ``bloqueos`` (P-3): agrupados por actividad: ``actividad_ref`` y ``ocurrencias`` (``fecha_laboral`` y ``motivo`` de cada avance Bloqueada autorizado). Es un registro HISTÓRICO: no dice que la actividad esté bloqueada ahora.
- ``narrativa`` (P-11): lista de secciones, cada una solo con ``texto`` (sin identificadores ni referencias); ``null`` si ``sin_datos``. En el consolidado, dentro de cada persona.

Individual: además ``persona`` (``id`` y ``nombre``; P-13, confirmada). Solo en respuestas autorizadas; el nombre y el identificador de la persona NO van al generador (que recibe un alias). Consolidado: ``personas`` (cada una con ``persona``, ``agregaciones``, ``actividades``, ``hechos``, ``bloqueos`` y ``narrativa``; NO hay colecciones
de actividades, hechos ni bloqueos al nivel del informe) y ``agregaciones_del_equipo``, la sección de equipo DETERMINISTA y sin narrativa.

Los campos ausentes se OMITEN (no se envían como nulos) cuando el dato no se puede mostrar: ``titulo``, ``origen`` y ``motivo_bloqueo``. No hay ningún campo de ranking, puntuación, porcentaje ni valoración. El orden de las personas es el
alfabético del núcleo (C-3).

``base`` (P-6, CONFIRMADA el 2026-11-18): RF-87 obliga a que todo informe deje claro en qué se basa, pero NO fija la redacción literal. ``DECLARACION_DE_BASE`` es la declaración FIJA DE PRODUCTO aprobada por la persona
responsable (redacción de producto, no una cita de RF-87). Se usa en los dos tipos de informe, también con ``sin_datos``.
"""

from dataclasses import asdict
from datetime import datetime, timezone

from app.modulos.informes.agregaciones import Agregaciones
from app.modulos.informes.consolidado import ConsolidadoBase
from app.modulos.informes.estructura import COMPLETA, ActividadDelInforme, Bloqueo, Hecho
from app.modulos.informes.individual import InformeBase
from app.modulos.informes.narrativa import NarrativaDePersona

# P-6 (confirmada): declaración fija de producto, aprobada el 2026-11-18. Cumple RF-87 («deja claro que se basa únicamente en los registros disponibles y autorizados del período y que no representa información que nunca
# fue registrada») con una redacción de producto; NO es una cita literal de RF-87.
DECLARACION_DE_BASE = "Este informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada."


def _momento(valor: datetime) -> str:
    """ISO 8601 en UTC (convenciones, sección 2)."""
    return valor.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _agregaciones(valor: Agregaciones | None) -> dict | None:
    return None if valor is None else asdict(valor)               # las seis métricas tal cual, sin recalcular


def _actividades(actividades: tuple[ActividadDelInforme, ...]) -> list[dict]:
    resultado = []
    for a in actividades:
        if a.forma == COMPLETA:
            resultado.append({"ref": a.ref, "forma": "completa", "titulo": a.texto, "origen": "planificada" if a.planificada else "no_planificada"})
        else:
            resultado.append({"ref": a.ref, "forma": "neutral", "referencia_neutral": a.texto})
    return resultado


def _hechos(hechos: tuple[Hecho, ...]) -> list[dict]:
    resultado = []
    for h in hechos:
        hecho = {"fecha_laboral": h.fecha_laboral.isoformat(), "actividad_ref": h.actividad_ref, "estado": h.estado, "descripcion": h.descripcion}
        if h.motivo_bloqueo is not None:
            hecho["motivo_bloqueo"] = h.motivo_bloqueo
        resultado.append(hecho)
    return resultado


def _bloqueos(bloqueos: tuple[Bloqueo, ...]) -> list[dict]:
    """P-3: agrupados por actividad, en el orden de primera aparición, con la lista de sus ocurrencias autorizadas (fecha y motivo)."""
    por_actividad: dict[str, list[dict]] = {}
    for b in bloqueos:
        por_actividad.setdefault(b.actividad_ref, []).append({"fecha_laboral": b.fecha_laboral.isoformat(), "motivo": b.motivo})
    return [{"actividad_ref": ref, "ocurrencias": ocurrencias} for ref, ocurrencias in por_actividad.items()]


def _narrativa(narrativa: NarrativaDePersona | None) -> list[dict] | None:
    return None if narrativa is None else [{"texto": s.texto} for s in narrativa.secciones]       # solo el texto: ninguna referencia interna


def _persona(persona) -> dict:
    return {"id": str(persona.id), "nombre": persona.nombre}


def _cabecera(informe, generado_en: datetime) -> dict:
    return {"tipo": informe.tipo, "periodo": {"desde": informe.desde.isoformat(), "hasta": informe.hasta.isoformat()}, "generado_en": _momento(generado_en), "base": DECLARACION_DE_BASE,
            "sin_datos": informe.sin_datos}


def a_respuesta_publica(resultado, generado_en: datetime | None = None) -> dict:
    """La respuesta pública de un informe individual o consolidado. ``generado_en`` es el momento real de la generación (se inyecta solo en las pruebas)."""
    ahora = generado_en or datetime.now(timezone.utc)
    informe = resultado.informe
    por_persona = resultado.narrativa.por_persona
    if isinstance(informe, ConsolidadoBase):
        personas = []
        for i, p in enumerate(informe.personas):
            narrativa = por_persona[i] if por_persona else None
            if narrativa is not None and narrativa.persona != p.persona:                     # la narrativa de cada persona es la de ESA persona
                raise RuntimeError("Inconsistencia interna: la narrativa no corresponde a la persona")
            personas.append({"persona": _persona(p.persona), "agregaciones": _agregaciones(p.agregaciones), "actividades": _actividades(p.actividades), "hechos": _hechos(p.hechos),
                             "bloqueos": _bloqueos(p.bloqueos), "narrativa": _narrativa(narrativa)})
        return {**_cabecera(informe, ahora), "personas": personas, "agregaciones_del_equipo": _agregaciones(informe.agregaciones_del_equipo)}
    if not isinstance(informe, InformeBase):
        raise RuntimeError("Tipo de informe desconocido")
    narrativa = por_persona[0] if por_persona else None
    return {**_cabecera(informe, ahora), "persona": _persona(informe.persona), "agregaciones": _agregaciones(informe.agregaciones), "actividades": _actividades(informe.actividades),
            "hechos": _hechos(informe.hechos), "bloqueos": _bloqueos(informe.bloqueos), "narrativa": _narrativa(narrativa)}
