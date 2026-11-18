"""M5-T1 — núcleo determinista del informe individual (M5-01, parte previa a la IA). Servicio INTERNO: no hay ruta, no se registra en ``main.py``, no llama a ningún generador, no
envía datos fuera del proceso y no guarda nada (RN-56, RF-75).

QUÉ HACE. Dado quien consulta, una persona (por defecto, quien consulta) y un período, 1) decide si puede generar ese informe y, si no, con qué código; 2) selecciona SOLO los avances
que la política de M1 le permite leer; 3) construye una estructura MÍNIMA, de campos cerrados, con los hechos, los bloqueos y las agregaciones deterministas; 4) indica ``sin_datos``
cuando no hay ningún registro autorizado (RN-57, CA-172, CA-173, CA-202), caso en que el generador no se invoca nunca.

AUTORIZACIÓN. La de M1 a M4, sin política paralela (D-M5-09): ``consultante_de``, ``condicion_lectura`` (en la propia consulta SQL) y ``persona_es_visible`` (la regla de equipo de
``decidir_lectura`` elevada de una fecha a alguna fecha DEL PERÍODO; solo elige el código). Orden de evaluación (convenciones 3.2):

1. puede operar: ``ACCESO_DESACTIVADO`` o ``SIN_PERTENENCIA_VIGENTE`` (403, solo informan de su propia situación);
2. formato: ``desde`` no posterior a ``hasta`` (``SOLICITUD_INVALIDA``), sin consultar nada;
3. la persona: la propia, o una persona VISIBLE EN EL PERÍODO pedido (perteneció al equipo vigente de quien llama en algún día del período) a la que solo el supervisor vigente con acceso
   efectivo puede generar el informe (RN-53, CA-153). Un compañero visible que no es supervisor recibe ``OPERACION_NO_PERMITIDA`` (403, D-M5-02, CA-154); una persona inexistente o
   cuya visibilidad en el período no puede demostrarse, ``RECURSO_NO_DISPONIBLE`` (404 indistinguible, RNF-13, T-01): la respuesta no revela relaciones históricas ajenas al período;
4. solo entonces se leen datos, y solo los autorizados: la propietaria obtiene todos sus registros de ambos equipos (RF-93, CA-227); un supervisor, solo los de las fechas en que la
   persona pertenecía a su equipo (RF-96, CA-157, CA-224, CA-225, CA-226), nunca los de otro equipo ni los posteriores a un traslado.

QUÉ NO ENTRA (RA-08, RA-11, RN-60, RN-101, ADR-003 sección 7): actividades marcadas por error; planificaciones (conservadas o no: esta consulta solo lee avances); el resumen libre de la
bitácora; el título y el origen de una actividad iniciada en otro equipo (se presenta como «Actividad en continuidad», sin más); correos, identificadores de acceso, contraseñas,
sesiones, nombres de equipos y la auditoría. Una actividad que se ve neutral no lleva motivos de bloqueo de otro equipo porque esos avances no están autorizados y no se seleccionan.

TEXTO NO CONFIABLE (RN-31, RNF-12). ``descripcion`` y ``motivo_bloqueo`` de cada hecho y el ``texto`` de una actividad de forma completa (su título) son TEXTO LIBRE de las
personas: se conserva tal cual y se trata siempre como dato, nunca como instrucción; este módulo no lo interpreta ni lo ejecuta. ``CAMPOS_DE_TEXTO_LIBRE`` los lista para que la
integración posterior (M5-T3) los entregue delimitados y no concatenados a las instrucciones.

SEUDONIMIZACIÓN POSTERIOR (M5-T3; ADR-003 sección 6). Esta estructura es la del informe en el servidor y SÍ lleva el nombre de la persona (``persona``) y el identificador de cada actividad,
porque el contrato público los devuelve. Antes de cualquier envío a un generador, M5-T3 debe: 1) sustituir ``persona`` por un alias («Persona 1») con una tabla que viva solo en memoria;
2) sustituir ``actividades[].id`` por la referencia opaca ``ref``; 3) enviar solo los campos de ``CAMPOS_PARA_EL_GENERADOR``, construidos con una función de lista cerrada y no
serializando esta estructura; 4) no enviar el nombre de la persona, ``persona.id`` ni ninguno de los identificadores. Cada ``Hecho`` ya lleva una referencia opaca (``h1``, ``h2``…), no el
identificador de la base de datos.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido.visibilidad import Consultante, condicion_lectura, persona_es_visible
from app.errores import AppError
from app.modulos.informes import agregaciones as calculo, repositorio
from app.modulos.informes.agregaciones import Agregaciones
# La estructura y el armado de hechos son comunes al consolidado (M5-T2): se reexportan para que este módulo siga siendo el punto de entrada del informe individual.
from app.modulos.informes.estructura import (  # noqa: F401
    BLOQUEADA, CAMPOS_DE_TEXTO_LIBRE, CAMPOS_PARA_EL_GENERADOR, COMPLETA, NEUTRAL, REFERENCIA_NEUTRAL, ActividadDelInforme, Bloqueo, Hecho, Numerador, Persona,
    construir_bloque, detalle_de_reintento, estados_al_corte, exigir_periodo_valido, exigir_que_puede_operar,
)

TIPO_INDIVIDUAL = "individual"


@dataclass(frozen=True)
class InformeBase:
    """Lo que el servidor sabe del informe ANTES de redactarlo. ``sin_datos`` verdadero: no hay hechos, ni bloqueos, ni actividades y ``agregaciones`` es ``None`` (el informe solo
    indica que no hay datos disponibles). No incluye la fecha de generación ni la declaración de base del informe (RF-48, RF-87): son de la respuesta (M5-T4)."""

    tipo: str
    desde: date
    hasta: date
    persona: Persona
    sin_datos: bool
    actividades: tuple[ActividadDelInforme, ...]
    hechos: tuple[Hecho, ...]
    bloqueos: tuple[Bloqueo, ...]
    agregaciones: Agregaciones | None


def _exigir_permiso_sobre(db: Session, consultante: Consultante, persona: UUID, desde: date, hasta: date) -> None:
    if persona == consultante.persona_id:
        return                                                      # la propietaria (RN-53, CA-152)
    if not persona_es_visible(db, consultante, persona, desde, hasta):
        raise AppError("RECURSO_NO_DISPONIBLE")                     # inexistente, o sin visibilidad demostrable EN EL PERÍODO: indistinguibles (T-01, RNF-13)
    if not consultante.es_supervisor_vigente:
        raise AppError("OPERACION_NO_PERMITIDA")                    # visible, pero no es suya ni supervisa (D-M5-02, CA-154)


def autorizar_informe_individual(db: Session, consultante: Consultante, persona_id: UUID | None, desde: date, hasta: date) -> UUID:
    """Pasos 1 a 3 del orden de evaluación, SIN leer ningún dato de registros: puede operar, formato y permiso sobre la persona. Devuelve la persona del informe (``persona_id`` ``None`` es quien consulta).
    El servicio de M5-T4 aplica entre esto y la lectura los límites que no dependen de los datos (rango), para que un límite no revele nada que la autorización oculte."""
    exigir_que_puede_operar(consultante)
    exigir_periodo_valido(desde, hasta)
    objetivo = consultante.persona_id if persona_id is None else persona_id
    _exigir_permiso_sobre(db, consultante, objetivo, desde, hasta)
    return objetivo


def preparar_informe_individual(db: Session, consultante: Consultante, persona_id: UUID | None, desde: date, hasta: date, max_hechos: int | None = None) -> InformeBase:
    """Ver el docstring del módulo. ``persona_id`` ``None`` significa quien consulta. Solo lectura: no modifica ni guarda nada. ``max_hechos`` (M5-T4): si los avances autorizados superan ese máximo, ``INFORME_EXCEDE_LIMITES``."""
    return construir_informe_individual(db, consultante, autorizar_informe_individual(db, consultante, persona_id, desde, hasta), desde, hasta, max_hechos)


def construir_informe_individual(db: Session, consultante: Consultante, objetivo: UUID, desde: date, hasta: date, max_hechos: int | None = None) -> InformeBase:
    """Lee y arma el informe de una persona YA AUTORIZADA con ``autorizar_informe_individual``. No autoriza por sí misma: no se debe llamar sin haberla autorizado."""
    nombre = repositorio.nombre_de_la_persona(db, objetivo)
    filas = repositorio.avances_autorizados_del_periodo(db, consultante, objetivo, desde, hasta, None if max_hechos is None else max_hechos + 1)
    if max_hechos is not None and len(filas) > max_hechos:
        raise AppError("INFORME_EXCEDE_LIMITES", [{"campo": "hechos", "motivo": "hechos_exceden_el_maximo", "maximo_hechos": max_hechos}, detalle_de_reintento(False)])
    persona = Persona(objetivo, nombre)
    if not filas:
        return InformeBase(TIPO_INDIVIDUAL, desde, hasta, persona, True, (), (), (), None)

    actividades, hechos, bloqueos = construir_bloque(filas, Numerador())
    # Estado al corte (el corte es ``hasta``) de las actividades CON AVANCES AUTORIZADOS del período: el del último avance hasta el corte, solo si está autorizado (RA-07, RN-88).
    por_id = estados_al_corte(db, list(actividades), hasta, condicion_lectura(consultante, "a.propietaria_id", "bx.fecha_laboral", prefijo="ec"))
    estado_al_corte = {a.ref: por_id.get(id_) for id_, a in actividades.items()}
    return InformeBase(TIPO_INDIVIDUAL, desde, hasta, persona, False, tuple(actividades.values()), tuple(hechos), bloqueos,
                       calculo.calcular(tuple(hechos), tuple(actividades.values()), estado_al_corte))
