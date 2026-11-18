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

TIPO_INDIVIDUAL = "individual"
# Texto fijo de la referencia neutral (RN-101). Una sola decisión de producto: una prueba comprueba que coincide con la de M4.
REFERENCIA_NEUTRAL = "Actividad en continuidad"
COMPLETA, NEUTRAL = "completa", "neutral"
BLOQUEADA = "Bloqueada"

CAMPOS_DE_TEXTO_LIBRE = {"Hecho": ("descripcion", "motivo_bloqueo"), "ActividadDelInforme": ("texto (solo si forma es completa: es el título)",)}
CAMPOS_PARA_EL_GENERADOR = {
    "informe": ("tipo", "periodo", "persona (como alias)", "hechos", "bloqueos", "agregaciones"),
    "hecho": ("ref", "fecha_laboral", "actividad_ref", "estado", "descripcion", "motivo_bloqueo"),
    "actividad": ("ref", "forma", "texto", "planificada"),
}


@dataclass(frozen=True)
class Persona:
    id: UUID
    nombre: str


@dataclass(frozen=True)
class ActividadDelInforme:
    """Una actividad referenciada por algún hecho. ``texto`` es su título si el consultante está autorizado sobre su jornada de origen (``completa``) o la referencia neutral (``neutral``).
    ``planificada`` es el origen de la actividad (``True`` planificada, ``False`` no planificada) solo si ese origen está autorizado; si no, ``None``: el origen de una actividad iniciada
    en otro equipo no se revela (RN-101). ``id`` es para la respuesta pública y NO debe salir hacia un generador."""

    ref: str
    id: UUID
    forma: str
    texto: str
    planificada: bool | None


@dataclass(frozen=True)
class Hecho:
    """Un avance autorizado del período. ``estado`` es el estado histórico de ese avance. ``motivo_bloqueo`` solo si el estado es Bloqueada."""

    ref: str
    fecha_laboral: date
    actividad_ref: str
    estado: str
    descripcion: str
    motivo_bloqueo: str | None


@dataclass(frozen=True)
class Bloqueo:
    """Un avance en estado Bloqueada con su motivo (RF-74, RN-55, CA-165). Una entrada por avance bloqueado: si una actividad se bloquea en dos jornadas, aparecen dos."""

    hecho_ref: str
    actividad_ref: str
    fecha_laboral: date
    motivo: str


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


def _exigir_que_puede_operar(consultante: Consultante) -> None:
    if not consultante.acceso_activo:
        raise AppError("ACCESO_DESACTIVADO")
    if consultante.pertenencia is None:
        raise AppError("SIN_PERTENENCIA_VIGENTE")


def _exigir_permiso_sobre(db: Session, consultante: Consultante, persona: UUID, desde: date, hasta: date) -> None:
    if persona == consultante.persona_id:
        return                                                      # la propietaria (RN-53, CA-152)
    if not persona_es_visible(db, consultante, persona, desde, hasta):
        raise AppError("RECURSO_NO_DISPONIBLE")                     # inexistente, o sin visibilidad demostrable EN EL PERÍODO: indistinguibles (T-01, RNF-13)
    if not consultante.es_supervisor_vigente:
        raise AppError("OPERACION_NO_PERMITIDA")                    # visible, pero no es suya ni supervisa (D-M5-02, CA-154)


def preparar_informe_individual(db: Session, consultante: Consultante, persona_id: UUID | None, desde: date, hasta: date) -> InformeBase:
    """Ver el docstring del módulo. ``persona_id`` ``None`` significa quien consulta. Solo lectura: no modifica ni guarda nada."""
    _exigir_que_puede_operar(consultante)
    if desde > hasta:
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "desde", "motivo": "posterior_a_hasta"}])
    objetivo = consultante.persona_id if persona_id is None else persona_id
    _exigir_permiso_sobre(db, consultante, objetivo, desde, hasta)

    nombre = repositorio.nombre_de_la_persona(db, objetivo)
    filas = repositorio.avances_autorizados_del_periodo(db, consultante, objetivo, desde, hasta)
    persona = Persona(objetivo, nombre)
    if not filas:
        return InformeBase(TIPO_INDIVIDUAL, desde, hasta, persona, True, (), (), (), None)

    actividades: dict[UUID, ActividadDelInforme] = {}
    hechos: list[Hecho] = []
    for n, f in enumerate(filas, start=1):
        if f.actividad_id not in actividades:
            neutral = not f.origen_autorizado
            actividades[f.actividad_id] = ActividadDelInforme(
                ref=f"a{len(actividades) + 1}", id=f.actividad_id, forma=NEUTRAL if neutral else COMPLETA,
                texto=REFERENCIA_NEUTRAL if neutral else f.titulo, planificada=None if neutral else f.origen == "planificada")
        hechos.append(Hecho(f"h{n}", f.fecha_laboral, actividades[f.actividad_id].ref, f.estado, f.descripcion, f.motivo_bloqueo))
    bloqueos = tuple(Bloqueo(h.ref, h.actividad_ref, h.fecha_laboral, h.motivo_bloqueo) for h in hechos if h.estado == BLOQUEADA)
    # Estado al corte (el corte es ``hasta``) de las actividades CON AVANCES AUTORIZADOS del período: el del último avance hasta el corte, solo si está autorizado (RA-07, RN-88).
    ultimos = repositorio.ultimo_avance_hasta_el_corte(db, list(actividades), hasta, condicion_lectura(consultante, "a.propietaria_id", "bx.fecha_laboral", prefijo="ec"))
    estado_por_actividad = {u.actividad_id: (u.estado if u.autorizado else None) for u in ultimos}
    estado_al_corte = {a.ref: estado_por_actividad.get(id_) for id_, a in actividades.items()}
    return InformeBase(TIPO_INDIVIDUAL, desde, hasta, persona, False, tuple(actividades.values()), tuple(hechos), bloqueos,
                       calculo.calcular(tuple(hechos), tuple(actividades.values()), estado_al_corte))
