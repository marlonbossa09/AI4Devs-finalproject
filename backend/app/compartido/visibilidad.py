"""Política de visibilidad histórica (BE-02, RA-01 a RA-12, DM-04). Base de M4 y del acceso del supervisor a M3-07.

QUÉ ES. Decide, para quien consulta, si puede LEER un registro, cómo se presenta una actividad y si ejerce supervisión.
Es de solo lectura y no escribe nada.

QUÉ NO ES.
- No es una respuesta HTTP. Devuelve una ``Decision`` interna con su motivo. Convertirla en 404 ``RECURSO_NO_DISPONIBLE`` (T-01),
  en 403 u otra cosa es de cada operación, según las convenciones y el contrato; los motivos internos distintos pueden
  (y hoy deben) ser indistinguibles hacia fuera.
- No es una operación: la usa el módulo de M4 (``app.modulos.consulta``) para las lecturas ajenas (desde M4-T1). M2 y M3 no
  la usan: toda operación suya sobre un registro ajeno sigue respondiendo 404 (convenciones 3.1) hasta M4-T6.
- No decide la presentación de M4 (referencia mínima, estado al corte: RA-06, RA-07), solo la visibilidad de base.

REGLAS (todas del modelo de datos, sección 12, y del alcance, RN-36):
- El equipo de un registro es el de la pertenencia de su propietaria que cubre su fecha laboral (RA-01, DM-04). El
  cambio de equipo posterior no lo altera (RN-82). La fecha laboral que determina el equipo de cada tipo de registro es
  (sección 12.2): bitácora, su fecha; avance y planificación, la de su bitácora; actividad, la de su bitácora de origen;
  entrada de auditoría, ``fecha_laboral_registro``.
- La propietaria consulta todo lo suyo, sin filtro por equipo (RA-03), incluida la planificación conservada (RA-11).
- Un integrante ACTIVO del equipo (pertenencia vigente hoy) lee, solo lectura, los registros cuyo equipo de esa fecha es
  el suyo, aunque se haya incorporado después (RN-36). No lee los de otro equipo ni los de períodos en que la propietaria
  pertenecía a otro (RN-36, CA-16, CA-17).
- Un registro cuya fecha no está cubierta por ninguna pertenencia de su propietaria (planificación conservada) no
  pertenece a ningún equipo: solo la propietaria lo consulta (RA-11).
- Una entrada de auditoría la ven la propietaria del registro y el supervisor autorizado del equipo de su fecha laboral;
  los compañeros no (RA-10). Las entradas de provisión no tienen visibilidad definida (RA-10, PA-06, PA-12; D-11) y no se
  muestran a nadie.
- La supervisión deriva solo de un intervalo de supervisor VIGENTE de una persona con acceso efectivo; nunca se transfiere
  (RA-12). Un supervisor con el acceso desactivado no ejerce supervisión.
- Con el acceso desactivado (IR-37) o sin pertenencia vigente (IR-38) no se consulta nada, ni siquiera lo propio.
- Nada cruza organizaciones: el equipo pertenece a una organización y la comparación es por equipo (y se comprueba la
  organización de forma explícita).

El predicado de autorización se aplica al SELECCIONAR los datos, no al presentarlos (convenciones 3.3): para listados y
vistas se ofrecen ``condicion_lectura`` y ``condicion_lectura_auditoria``, que componen la MISMA regla en SQL a partir de
la misma definición del intervalo (``pertenencias.cubre``). Las pruebas comprueban que ambas formas coinciden.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido import pertenencias
from app.compartido.pertenencias import Pertenencia, pertenencia_en_fecha

SUPERVISOR = "supervisor"


class Motivo(StrEnum):
    """Por qué se decidió. Es información INTERNA: no debe distinguirse hacia fuera (T-01)."""

    # visibles
    PROPIETARIA = "propietaria"
    EQUIPO_HISTORICO = "equipo_historico"
    SUPERVISION_DEL_EQUIPO_HISTORICO = "supervision_del_equipo_historico"
    # no visibles
    ACCESO_DESACTIVADO = "acceso_desactivado"
    SIN_PERTENENCIA_VIGENTE = "sin_pertenencia_vigente"
    SIN_EQUIPO_EN_LA_FECHA = "sin_equipo_en_la_fecha"
    OTRA_ORGANIZACION = "otra_organizacion"
    OTRO_EQUIPO = "otro_equipo"
    NO_ES_SUPERVISION = "no_es_supervision"
    PROVISION_SIN_VISIBILIDAD_DEFINIDA = "provision_sin_visibilidad_definida"


@dataclass(frozen=True)
class Decision:
    visible: bool
    motivo: Motivo

    def __bool__(self) -> bool:  # ``if decision:`` equivale a ``if decision.visible:``
        return self.visible


class Forma(StrEnum):
    """Cómo se presentaría una actividad a quien consulta, SI su operación decide que aparece (RA-04, RA-08)."""

    COMPLETA = "completa"  # título y marca de error con su motivo
    NEUTRAL = "neutral"  # «Actividad en continuidad», con identificador opaco, sin título ni marca
    OCULTA = "oculta"  # no aparece ni siquiera como referencia mínima


@dataclass(frozen=True)
class Registro:
    """Lo único que la política necesita de un registro: su propietaria y la fecha laboral que determina su equipo."""

    propietaria_id: UUID
    fecha_laboral: date | None


@dataclass(frozen=True)
class EntradaDeAuditoria:
    propietaria_registro_id: UUID
    fecha_laboral_registro: date | None
    tipo_autor: str  # 'persona' o 'provision'


@dataclass(frozen=True)
class Consultante:
    """Quien consulta, con su situación vigente en ``hoy`` (la fecha actual la fija quien llama: es inyectable)."""

    persona_id: UUID
    acceso_activo: bool
    hoy: date
    pertenencia: Pertenencia | None

    @property
    def puede_operar(self) -> bool:
        """IR-37 e IR-38."""
        return self.acceso_activo and self.pertenencia is not None

    @property
    def es_supervisor_vigente(self) -> bool:
        return self.puede_operar and self.pertenencia.rol == SUPERVISOR

    def supervisa(self, equipo_id: UUID) -> bool:
        """RA-12: supervisor vigente de ese equipo, con acceso efectivo."""
        return self.es_supervisor_vigente and self.pertenencia.equipo_id == equipo_id


def consultante_de(db: Session, persona_id: UUID, *, hoy: date, ahora: datetime | None = None) -> Consultante:
    """Carga la situación vigente de quien consulta. ``ahora`` (UTC) decide si el acceso ya está desactivado."""
    ahora = ahora or datetime.now(timezone.utc)
    fila = db.execute(
        text("select (acceso_desactivado_en is not null and acceso_desactivado_en <= :ahora) as desactivado "
             "from persona where id = :persona"),
        {"persona": persona_id, "ahora": ahora},
    ).one_or_none()
    activo = fila is not None and not fila.desactivado  # una persona inexistente no puede consultar
    return Consultante(persona_id, activo, hoy, pertenencia_en_fecha(db, persona_id, hoy))


def _rechazo_previo(consultante: Consultante) -> Decision | None:
    """Paso 2 del orden de evaluación (convenciones 3.2): puede operar."""
    if not consultante.acceso_activo:
        return Decision(False, Motivo.ACCESO_DESACTIVADO)
    if consultante.pertenencia is None:
        return Decision(False, Motivo.SIN_PERTENENCIA_VIGENTE)
    return None


def _decidir_por_equipo(db: Session, consultante: Consultante, propietaria_id: UUID, fecha: date | None) -> Decision | None:
    """Parte común: devuelve la decisión si el equipo del registro descarta al consultante, o ``None`` si coincide."""
    if propietaria_id == consultante.persona_id:
        return Decision(True, Motivo.PROPIETARIA)
    del_registro = None if fecha is None else pertenencia_en_fecha(db, propietaria_id, fecha)
    if del_registro is None:
        return Decision(False, Motivo.SIN_EQUIPO_EN_LA_FECHA)  # RA-11: planificación conservada, o fecha sin cubrir
    if del_registro.organizacion_id != consultante.pertenencia.organizacion_id:
        return Decision(False, Motivo.OTRA_ORGANIZACION)
    if del_registro.equipo_id != consultante.pertenencia.equipo_id:
        return Decision(False, Motivo.OTRO_EQUIPO)
    return None


def decidir_lectura(db: Session, consultante: Consultante, registro: Registro) -> Decision:
    """¿Puede ``consultante`` LEER el registro? (RA-01, RA-03, RA-11, RN-36). Solo lectura: nunca concede escribir."""
    previo = _rechazo_previo(consultante)
    if previo is not None:
        return previo
    resuelta = _decidir_por_equipo(db, consultante, registro.propietaria_id, registro.fecha_laboral)
    return resuelta if resuelta is not None else Decision(True, Motivo.EQUIPO_HISTORICO)


def decidir_lectura_de_auditoria(db: Session, consultante: Consultante, entrada: EntradaDeAuditoria) -> Decision:
    """¿Puede ``consultante`` ver una entrada de auditoría? (RA-10): la propietaria del registro y el supervisor autorizado
    del equipo de su fecha laboral. Las entradas de provisión no se muestran a nadie."""
    previo = _rechazo_previo(consultante)
    if previo is not None:
        return previo
    if entrada.tipo_autor != "persona":
        return Decision(False, Motivo.PROVISION_SIN_VISIBILIDAD_DEFINIDA)
    resuelta = _decidir_por_equipo(db, consultante, entrada.propietaria_registro_id, entrada.fecha_laboral_registro)
    if resuelta is not None:
        return resuelta
    if consultante.es_supervisor_vigente:
        return Decision(True, Motivo.SUPERVISION_DEL_EQUIPO_HISTORICO)
    return Decision(False, Motivo.NO_ES_SUPERVISION)


def forma_de_actividad(db: Session, consultante: Consultante, origen: Registro, *, marcada_por_error: bool) -> Forma:
    """Cómo se presenta una actividad (RA-04, RA-08), según la autorización sobre su JORNADA DE ORIGEN. No decide si la
    actividad aparece: eso lo decide la proyección de M4 (RA-06, RA-07). Quien no puede operar no ve nada."""
    decision = decidir_lectura(db, consultante, origen)
    if decision.visible:
        return Forma.COMPLETA
    if decision.motivo in (Motivo.ACCESO_DESACTIVADO, Motivo.SIN_PERTENENCIA_VIGENTE):
        return Forma.OCULTA
    return Forma.OCULTA if marcada_por_error else Forma.NEUTRAL


def puede_ver_estado_actual(db: Session, consultante: Consultante, propietaria_id: UUID) -> bool:
    """¿Se informa a ``consultante`` del ESTADO ACTUAL de las actividades de ``propietaria_id``? (RN-48, RN-85, RF-95).

    Solo si la propietaria es la propia consultante o PERTENECE HOY a su equipo. Quien consulta lo que una persona hizo en un
    equipo al que ya no pertenece no ve el estado actual de su trabajo (la persona trasladada: CA-221). Es independiente de
    la lectura del registro: se puede leer un registro y no su estado actual."""
    if not consultante.puede_operar:
        return False
    if propietaria_id == consultante.persona_id:
        return True
    actual = pertenencia_en_fecha(db, propietaria_id, consultante.hoy)
    return actual is not None and actual.equipo_id == consultante.pertenencia.equipo_id


def pertenece_al_equipo_en(db: Session, consultante: Consultante, persona_id: UUID, fecha: date) -> bool:
    """¿El equipo de ``persona_id`` en la fecha laboral es el de quien consulta? (RA-01, DM-04). A diferencia de ``decidir_lectura`` NO concede nada por ser la propia
    consultante: es la regla de las vistas DE EQUIPO (supervisión, M4-03), donde lo propio de un período en que la supervisora estaba en otro equipo no es del equipo."""
    if not consultante.puede_operar:
        return False
    pertenencia = pertenencia_en_fecha(db, persona_id, fecha)
    return pertenencia is not None and pertenencia.equipo_id == consultante.pertenencia.equipo_id


# ----------------------------------------------------------------------------------------------------------------------
# La misma regla, como predicado SQL para seleccionar solo lo autorizado (convenciones 3.3)
# ----------------------------------------------------------------------------------------------------------------------

_PREFIJO = re.compile(r"^[a-z][a-z0-9_]{0,15}$")


def condicion_lectura(consultante: Consultante, propietaria: str, fecha: str, *, prefijo: str = "vis") -> tuple[str, dict]:
    """Condición SQL equivalente a ``decidir_lectura`` para un registro cuya propietaria está en la columna
    ``propietaria`` y cuya fecha laboral está en la columna ``fecha``. Devuelve el texto y sus parámetros.

    ``propietaria`` y ``fecha`` son columnas o alias escritos por el código (se validan; nunca texto de una petición).
    ``prefijo`` evita colisiones de parámetros si se compone más de una condición en la misma consulta."""
    if not _PREFIJO.match(prefijo):
        raise ValueError(f"Prefijo no admitido: {prefijo!r}")
    propietaria = pertenencias.identificador_sql(propietaria)
    fecha = pertenencias.identificador_sql(fecha)
    if not consultante.puede_operar:
        return "false", {}
    alias = f"{prefijo}_pv"
    sql = (f"({propietaria} = :{prefijo}_persona or exists (select 1 from pertenencia {alias} "
           f"where {alias}.persona_id = {propietaria} and {pertenencias.cubre(alias, fecha)} "
           f"and {alias}.equipo_id = :{prefijo}_equipo))")
    return sql, {f"{prefijo}_persona": consultante.persona_id, f"{prefijo}_equipo": consultante.pertenencia.equipo_id}


def pertenencia_del_equipo(consultante: Consultante, alias: str, fecha: str, *, prefijo: str = "eq") -> tuple[str, dict]:
    """Condición SQL sobre un intervalo de ``pertenencia`` ya presente en la consulta (``alias``): es del equipo de quien consulta y cubre ``fecha`` (una columna o ``:nombre``).
    Es la ÚNICA expresión de «pertenece al equipo del consultante en la fecha»: ``condicion_equipo`` la usa dentro de un ``exists`` y las vistas de equipo (M4-03) la usan para
    partir de los integrantes del equipo en lugar de recorrer toda la organización. Devuelve el texto y sus parámetros (``false`` si quien consulta no puede operar)."""
    if not _PREFIJO.match(prefijo):
        raise ValueError(f"Prefijo no admitido: {prefijo!r}")
    alias = pertenencias.identificador_sql(alias)
    fecha = fecha if fecha.startswith(":") else pertenencias.identificador_sql(fecha)
    if not consultante.puede_operar:
        return "false", {}
    return f"{alias}.equipo_id = :{prefijo}_equipo and {pertenencias.cubre(alias, fecha)}", {f"{prefijo}_equipo": consultante.pertenencia.equipo_id}


def condicion_equipo(consultante: Consultante, propietaria: str, fecha: str, *, prefijo: str = "eq") -> tuple[str, dict]:
    """Condición SQL equivalente a ``pertenece_al_equipo_en``: existe una pertenencia de la propietaria (columna ``propietaria``) que cubre la fecha (columna ``fecha``) y es
    del equipo de quien consulta. Sin la rama «es la propia consultante» de ``condicion_lectura``. Es una expresión booleana (``exists (...)``) que sirve en un ``WHERE`` y en
    una lista de selección. Devuelve el texto y sus parámetros."""
    propietaria = pertenencias.identificador_sql(propietaria)
    alias = f"{prefijo}_pv"
    condicion, parametros = pertenencia_del_equipo(consultante, alias, fecha, prefijo=prefijo)
    if condicion == "false":
        return "false", {}
    return f"exists (select 1 from pertenencia {alias} where {alias}.persona_id = {propietaria} and {condicion})", parametros


def condicion_lectura_auditoria(consultante: Consultante, propietaria: str, fecha: str, tipo_autor: str,
                                *, prefijo: str = "aud") -> tuple[str, dict]:
    """Condición SQL equivalente a ``decidir_lectura_de_auditoria``: solo entradas de personas; la propietaria, o el
    supervisor vigente del equipo de la fecha laboral del registro."""
    if not _PREFIJO.match(prefijo):
        raise ValueError(f"Prefijo no admitido: {prefijo!r}")
    propietaria = pertenencias.identificador_sql(propietaria)
    fecha = pertenencias.identificador_sql(fecha)
    tipo_autor = pertenencias.identificador_sql(tipo_autor)
    if not consultante.puede_operar:
        return "false", {}
    alias = f"{prefijo}_pv"
    sql = (f"({tipo_autor} = 'persona' and ({propietaria} = :{prefijo}_persona or "
           + (f"exists (select 1 from pertenencia {alias} where {alias}.persona_id = {propietaria} "
              f"and {pertenencias.cubre(alias, fecha)} and {alias}.equipo_id = :{prefijo}_equipo)"
              if consultante.es_supervisor_vigente else "false")
           + "))")
    parametros = {f"{prefijo}_persona": consultante.persona_id}
    if consultante.es_supervisor_vigente:
        parametros[f"{prefijo}_equipo"] = consultante.pertenencia.equipo_id
    return sql, parametros
