"""M5-T2 — núcleo determinista del informe consolidado (M5-02, parte previa a la IA). Servicio INTERNO: no hay ruta, no se registra en ``main.py``, no llama a ningún generador, no envía datos
fuera del proceso y no guarda nada (RN-56, RF-75). No genera narrativa: de la narrativa por persona se ocupará M5-T3 (D-M5-03, aprobada en principio).

QUÉ HACE. Dado quien consulta, el equipo (por defecto, el que supervisa) y un período: 1) decide si puede generar el consolidado y, si no, con qué código; 2) selecciona SOLO los avances que
eran DEL EQUIPO en su fecha laboral, de todas las personas a la vez, con la política de M1 aplicada en la propia consulta SQL, ANTES de agrupar o calcular nada (convenciones 3.3, RA-09);
3) arma, por persona en orden alfabético, sus actividades, hechos, bloqueos y agregaciones, y las agregaciones del equipo; 4) indica ``sin_datos`` si el equipo no tiene ningún avance autorizado.

AUTORIZACIÓN (D-M5-09: la política de M1, sin política paralela). Orden de evaluación (convenciones 3.2): 1) puede operar (``ACCESO_DESACTIVADO`` si el supervisor está desactivado,
``SIN_PERTENENCIA_VIGENTE``); 2) formato (``desde`` no posterior a ``hasta``); 3) rol: solo el supervisor vigente con acceso efectivo (RN-54, RA-12); un colaborador, también uno que
fue supervisor y ya no lo es, recibe ``OPERACION_NO_PERMITIDA`` (403, CA-169); 4) el equipo: el que supervisa; un ``equipo_id`` ajeno, o inexistente, da ``RECURSO_NO_DISPONIBLE`` (404
indistinguible, CA-170); 5) solo entonces se leen datos.

POBLACIÓN. Los avances AUTORIZADOS del período de las personas que eran del equipo en la fecha laboral de cada avance (RF-83, CA-228, CA-229): una persona trasladada aporta al consolidado
del equipo anterior solo lo anterior al traslado y al del equipo nuevo solo lo posterior; el trabajo de la propia supervisora cuenta si ella estaba en el equipo esa fecha. Solo aparecen las
personas con al menos un avance autorizado (no se listan integrantes sin registros). Una actividad iniciada en otro equipo sale en forma neutral («Actividad en continuidad», sin título,
origen ni motivos ajenos: RN-101, CA-277) y su estado al corte, si lo determina un avance de otro equipo, es ``estado_no_disponible`` (RN-88, CA-235).

DIFERENCIAS CON LA VISTA DE SUPERVISIÓN (M4-03). M4-03 es una vista de ACTIVIDADES del equipo: incluye también las planificadas sin avances y las pendientes al corte (RN-47) y las muestra con
referencia mínima, motivos de inclusión, paginación y cursor. El consolidado NO importa esa población: solo cuenta AVANCES autorizados del período (una planificación sin avances no es un
registro), no emite referencias mínimas, no pagina y no ordena actividades. Comparten la política (mismos predicados) y la regla del estado al corte; por eso, cuando sus poblaciones coinciden,
los recuentos por estado deben coincidir (prueba de coherencia).

ORDEN Y NEUTRALIDAD (RF-47). Las personas se ordenan por nombre (``clave_alfabetica``: sin distinguir mayúsculas ni acentos, con la «ñ» tras la «n») y, en empate, por identificador interno: nunca por cantidad de avances, bloqueos ni ningún otro valor. La
estructura no tiene campos de ranking, puntuación, porcentaje ni valoración. Las agregaciones del equipo son las MISMAS definiciones que las individuales (``agregaciones.py``) aplicadas al
conjunto de todos los hechos autorizados del equipo.

TEXTO NO CONFIABLE y SEUDONIMIZACIÓN POSTERIOR: valen las del informe individual (``individual.py``): los textos libres se conservan como datos; antes de cualquier envío, M5-T3 sustituye cada
persona por un alias con una tabla solo en memoria, usa las referencias opacas y construye lo enviado con una función de lista cerrada (``CAMPOS_PARA_EL_GENERADOR["consolidado"]``).
"""

from dataclasses import dataclass
from datetime import date
import unicodedata
from itertools import groupby
from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido.visibilidad import Consultante, condicion_equipo
from app.errores import AppError
from app.modulos.informes import agregaciones as calculo, repositorio
from app.modulos.informes.agregaciones import Agregaciones
from app.modulos.informes.estructura import (
    ActividadDelInforme, Bloqueo, Hecho, Numerador, Persona, construir_bloque, detalle_de_reintento, estados_al_corte, exigir_periodo_valido, exigir_que_puede_operar,
)

TIPO_CONSOLIDADO = "consolidado"


def clave_alfabetica(nombre: str) -> str:
    """Criterio de comparación del orden alfabético de los nombres (C-3, confirmada el 2026-11-18). Solo sirve para ORDENAR: el nombre que se muestra no se altera.

    - Mayúsculas y minúsculas no cuentan (``casefold``): «alba» y «Alba» comparan igual.
    - Los acentos y diéresis no cuentan: «Álvaro» va entre «alba» y «Nora», no después de «Zoe» como ocurriría comparando los códigos de los caracteres.
    - La «ñ» es una letra propia del español: va después de todas las «n» y antes de la «o» (se compara como «n» seguida de un carácter posterior a cualquier letra).
    - No se usa ninguna dependencia: solo ``unicodedata`` de la biblioteca estándar. Es una comparación por caracteres, no la ordenación de un idioma o configuración regional concretos.
    El empate (nombres que comparan igual, como «José» y «Jose») lo resuelve el identificador interno de la persona, de modo que el orden es estable y no depende del orden en que lleguen las filas."""
    plegado = unicodedata.normalize("NFC", nombre.casefold()).replace("ñ", "n{")
    return "".join(c for c in unicodedata.normalize("NFD", plegado) if not unicodedata.combining(c))


@dataclass(frozen=True)
class PersonaDelConsolidado:
    """Lo autorizado de UNA persona en el consolidado: su bloque de actividades, hechos, bloqueos y agregaciones (las mismas definiciones que las del informe individual)."""

    persona: Persona
    actividades: tuple[ActividadDelInforme, ...]
    hechos: tuple[Hecho, ...]
    bloqueos: tuple[Bloqueo, ...]
    agregaciones: Agregaciones


@dataclass(frozen=True)
class ConsolidadoBase:
    """Lo que el servidor sabe del consolidado ANTES de redactarlo. ``sin_datos`` verdadero: no hay personas y ``agregaciones_del_equipo`` es ``None``. No incluye el nombre ni el identificador del
    equipo (ADR-003, sección 7), ni la fecha de generación ni la declaración de base (RF-48, RF-87): son de la respuesta (M5-T4). La sección de equipo (``agregaciones_del_equipo``) es
    DETERMINISTA y no lleva narrativa (D-M5-03)."""

    tipo: str
    desde: date
    hasta: date
    sin_datos: bool
    personas: tuple[PersonaDelConsolidado, ...]
    agregaciones_del_equipo: Agregaciones | None


def autorizar_informe_consolidado(db: Session, consultante: Consultante, equipo_id: UUID | None, desde: date, hasta: date) -> None:
    """Pasos 1 a 4 del orden de evaluación (C-6), SIN leer ningún dato de registros: puede operar, formato, rol y equipo. Ver ``autorizar_informe_individual`` para su uso desde M5-T4."""
    exigir_que_puede_operar(consultante)
    exigir_periodo_valido(desde, hasta)
    if not consultante.es_supervisor_vigente:
        raise AppError("OPERACION_NO_PERMITIDA")                    # RN-54, RA-12, CA-169: es un 403 por rol sobre la función, no revela ningún registro
    if equipo_id is not None and equipo_id != consultante.pertenencia.equipo_id:
        raise AppError("RECURSO_NO_DISPONIBLE")                     # equipo ajeno o inexistente: indistinguibles (CA-170, RNF-13)


def preparar_informe_consolidado(db: Session, consultante: Consultante, equipo_id: UUID | None, desde: date, hasta: date, max_hechos: int | None = None) -> ConsolidadoBase:
    """Ver el docstring del módulo. ``equipo_id`` ``None`` significa el equipo que supervisa quien consulta. Solo lectura: no modifica ni guarda nada. ``max_hechos`` (M5-T4): máximo de avances autorizados de
    TODAS las personas juntas; si se supera, ``INFORME_EXCEDE_LIMITES`` y no se trunca nada."""
    autorizar_informe_consolidado(db, consultante, equipo_id, desde, hasta)
    return construir_informe_consolidado(db, consultante, desde, hasta, max_hechos)


def construir_informe_consolidado(db: Session, consultante: Consultante, desde: date, hasta: date, max_hechos: int | None = None) -> ConsolidadoBase:
    """Lee y arma el consolidado del equipo que supervisa quien consulta, YA AUTORIZADO con ``autorizar_informe_consolidado``. No autoriza por sí misma."""
    filas = repositorio.avances_autorizados_del_equipo(db, consultante, desde, hasta, None if max_hechos is None else max_hechos + 1)
    if max_hechos is not None and len(filas) > max_hechos:
        raise AppError("INFORME_EXCEDE_LIMITES", [{"campo": "hechos", "motivo": "hechos_exceden_el_maximo", "maximo_hechos": max_hechos}, detalle_de_reintento(False)])
    if not filas:
        return ConsolidadoBase(TIPO_CONSOLIDADO, desde, hasta, True, (), None)

    # Personas en orden alfabético de nombre (``clave_alfabetica``), con el identificador como desempate: nunca por cantidad ni por ningún valor calculado (RF-47)
    por_persona = [(Persona(pid, grupo[0].nombre), grupo) for pid, grupo in ((k, list(g)) for k, g in groupby(filas, key=lambda f: f.persona_id))]
    por_persona.sort(key=lambda par: (clave_alfabetica(par[0].nombre), par[0].id))

    numerador = Numerador()
    bloques = [(persona, *construir_bloque(grupo, numerador)) for persona, grupo in por_persona]
    # Estado al corte de las actividades con avances autorizados: el del último avance hasta el corte, solo si es DEL EQUIPO (RA-07, RN-88)
    todas = [id_ for _, actividades, _, _ in bloques for id_ in actividades]
    por_id = estados_al_corte(db, todas, hasta, condicion_equipo(consultante, "a.propietaria_id", "bx.fecha_laboral", prefijo="ec"))

    personas, todos_los_hechos, todas_las_actividades, estados = [], [], [], {}
    for persona, actividades, hechos, bloqueos in bloques:
        de_la_persona = {a.ref: por_id.get(id_) for id_, a in actividades.items()}
        personas.append(PersonaDelConsolidado(persona, tuple(actividades.values()), tuple(hechos), bloqueos,
                                              calculo.calcular(tuple(hechos), tuple(actividades.values()), de_la_persona)))
        todos_los_hechos += hechos
        todas_las_actividades += actividades.values()
        estados.update(de_la_persona)
    return ConsolidadoBase(TIPO_CONSOLIDADO, desde, hasta, False, tuple(personas),
                           calculo.calcular(tuple(todos_los_hechos), tuple(todas_las_actividades), estados))
