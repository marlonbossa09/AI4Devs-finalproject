"""Casos de uso de provisión: crear un equipo (M1-02a), crear una persona con su primera pertenencia (M1-02b) y registrar
traslados y cambios de rol (M1-05).

Independientes de la CLI y de cualquier transporte. Cada función recibe una conexión ya dentro de UNA transacción (quien
llama la abre y la confirma o la deshace): una orden rechazada no deja altas parciales ni entradas de auditoría. Todas
dejan UNA entrada de auditoría de provisión con la persona operadora, sin credenciales ni códigos (IR-34, CA-251).

Reglas: IR-02/IR-28 (sin solapes, lo garantiza también la base), IR-03 y IR-32 (supervisión del equipo), IR-29/IR-30,
RN-106 (sin altas históricas: ``desde`` igual o posterior a la fecha actual de la organización, que se mide con un reloj
INYECTABLE; D7) y P6 (nombre de equipo único por organización, sin distinguir mayúsculas ni espacios exteriores; no se
quitan acentos ni espacios interiores).
"""

import json
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.provision.errores import ErrorDeProvision
from app.provision.linea_temporal import (
    IntervaloDeSupervisor, Tramo, primera_irregularidad_de_persona, primera_violacion_de_supervision, solapa_con_supervisor,
    supervision_cubre_desde,
)
from app.provision.operadores import Operador
from app.seguridad.identificadores import normalizar_identificador

ROLES = ("colaborador", "supervisor")
Reloj = Callable[[], datetime]


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _fecha_actual(zona_horaria: str, reloj: Reloj) -> date:
    return reloj().astimezone(ZoneInfo(zona_horaria)).date()


def _referencia(operador: Operador, invocacion: uuid.UUID) -> str:
    return f"operador:{operador.identificador}|invocacion:{invocacion}"


def _texto(valor: str | None, campo: str) -> str:
    """Nombre obligatorio, recortado (los espacios exteriores no cuentan), con el máximo configurable (D-03)."""
    limpio = (valor or "").strip()
    if not limpio:
        raise ErrorDeProvision("CAMPO_OBLIGATORIO", [{"campo": campo, "motivo": "vacio"}])
    if len(limpio) > get_settings().text_max_title:
        raise ErrorDeProvision("TEXTO_DEMASIADO_LARGO", [{"campo": campo, "motivo": "demasiado_largo"}])
    return limpio


def _bloquear(conexion: Connection, clave: str) -> None:
    """Serializa las órdenes que tocan lo mismo (bloqueo consultivo hasta el fin de la transacción). Las restricciones
    de la base de datos siguen siendo la garantía final."""
    conexion.execute(text("select pg_advisory_xact_lock(hashtextextended(:c, 0))"), {"c": clave})


def _auditar(conexion: Connection, operador: Operador, invocacion: uuid.UUID, *, tipo_objeto: str, objeto_id: uuid.UUID,
             propietaria: uuid.UUID | None, valor_nuevo: dict, operacion: str = "alta",
             valor_anterior: dict | None = None, motivo: str | None = None) -> None:
    conexion.execute(
        text("insert into auditoria (tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id, "
             "propietaria_registro_id, motivo, valor_anterior, valor_nuevo) "
             "values ('provision', :ref, :op, :t, :o, :p, :motivo, cast(:anterior as jsonb), cast(:nuevo as jsonb))"),
        {"ref": _referencia(operador, invocacion), "op": operacion, "t": tipo_objeto, "o": objeto_id, "p": propietaria,
         "motivo": motivo, "anterior": None if valor_anterior is None else json.dumps(valor_anterior), "nuevo": json.dumps(valor_nuevo)},
    )


def _restriccion(error: IntegrityError) -> str | None:
    return getattr(getattr(error.orig, "diag", None), "constraint_name", None)


# ---------------------------------------------------------------------------------------------------- M1-02a

@dataclass(frozen=True)
class EquipoCreado:
    equipo_id: uuid.UUID
    organizacion_id: uuid.UUID
    nombre: str


def crear_equipo(conexion: Connection, operador: Operador, *, organizacion_id: uuid.UUID, nombre: str,
                 invocacion: uuid.UUID | None = None) -> EquipoCreado:
    """M1-02a. Crea un equipo dentro de una organización existente. Nace en provisión: sin colaboradores y sin supervisor
    (CA-250). Nombre único por organización (P6)."""
    invocacion = invocacion or uuid.uuid4()
    nombre = _texto(nombre, "nombre")
    existe = conexion.execute(text("select 1 from organizacion where id = :o"), {"o": organizacion_id}).first()
    if existe is None:
        raise ErrorDeProvision("RECURSO_NO_DISPONIBLE", [{"campo": "organizacion"}])
    _bloquear(conexion, f"smartwork:equipo:organizacion:{organizacion_id}")
    repetido = conexion.execute(
        text("select 1 from equipo where organizacion_id = :o "
             "and lower(btrim(nombre, E' \t\r\n\f\v')) = lower(btrim(:n, E' \t\r\n\f\v'))"),
        {"o": organizacion_id, "n": nombre},
    ).first()
    if repetido is not None:
        raise ErrorDeProvision("NOMBRE_DE_EQUIPO_DUPLICADO")
    try:
        equipo_id = conexion.execute(
            text("insert into equipo (organizacion_id, nombre) values (:o, :n) returning id"),
            {"o": organizacion_id, "n": nombre},
        ).scalar_one()
    except IntegrityError as error:
        if _restriccion(error) == "equipo_nombre_unico_por_organizacion":
            raise ErrorDeProvision("NOMBRE_DE_EQUIPO_DUPLICADO") from error
        raise
    _auditar(conexion, operador, invocacion, tipo_objeto="equipo", objeto_id=equipo_id, propietaria=None,
             valor_nuevo={"equipo": str(equipo_id), "organizacion": str(organizacion_id), "nombre": nombre})
    return EquipoCreado(equipo_id, organizacion_id, nombre)


# ---------------------------------------------------------------------------------------------------- M1-02b

@dataclass(frozen=True)
class PersonaCreada:
    persona_id: uuid.UUID
    equipo_id: uuid.UUID
    rol: str
    desde: date
    sin_contrasena: bool = True  # no se emite ningún código: el primer acceso es M1-03a/b


def crear_persona(conexion: Connection, operador: Operador, *, nombre: str, identificador_acceso: str,
                  equipo_id: uuid.UUID, rol: str, desde: date, reloj: Reloj = ahora_utc,
                  invocacion: uuid.UUID | None = None) -> PersonaCreada:
    """M1-02b. Crea una persona, su identidad de acceso (SIN contraseña) y su primera pertenencia, en una sola operación
    atómica. No emite ningún código."""
    invocacion = invocacion or uuid.uuid4()
    nombre = _texto(nombre, "nombre")
    identificador = normalizar_identificador(identificador_acceso or "")
    if not identificador:
        raise ErrorDeProvision("CAMPO_OBLIGATORIO", [{"campo": "identificador_acceso", "motivo": "vacio"}])
    if len(identificador) > get_settings().login_identifier_max_length:
        raise ErrorDeProvision("TEXTO_DEMASIADO_LARGO", [{"campo": "identificador_acceso", "motivo": "demasiado_largo"}])
    if rol not in ROLES:
        raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"campo": "rol", "motivo": "rol_no_valido"}])

    equipo = conexion.execute(
        text("select e.id, o.zona_horaria from equipo e join organizacion o on o.id = e.organizacion_id where e.id = :e"),
        {"e": equipo_id},
    ).one_or_none()
    if equipo is None:
        raise ErrorDeProvision("RECURSO_NO_DISPONIBLE", [{"campo": "equipo"}])
    if desde < _fecha_actual(equipo.zona_horaria, reloj):  # CA-253, RN-106: no hay altas históricas
        raise ErrorDeProvision("FECHA_EFECTIVA_INVALIDA")

    _bloquear(conexion, f"smartwork:pertenencias:equipo:{equipo_id}")  # serializa las altas de un mismo equipo
    if conexion.execute(text("select 1 from identidad where identificador_acceso = :i"), {"i": identificador}).first():
        raise ErrorDeProvision("IDENTIFICADOR_DUPLICADO")

    supervisores = [IntervaloDeSupervisor(f.desde, f.hasta_exclusivo) for f in conexion.execute(
        text("select desde, hasta_exclusivo from pertenencia where equipo_id = :e and rol = 'supervisor'"), {"e": equipo_id})]
    if rol == "supervisor" and solapa_con_supervisor(supervisores, desde):
        raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"campo": "rol", "motivo": "el_equipo_ya_tiene_supervisor"}])  # CA-08
    if rol == "colaborador" and not supervision_cubre_desde(supervisores, desde):
        raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"campo": "rol", "motivo": "el_equipo_no_tiene_supervisor_desde_esa_fecha"}])  # IR-32

    try:
        persona_id = conexion.execute(text("insert into persona (nombre) values (:n) returning id"), {"n": nombre}).scalar_one()
        conexion.execute(
            text("insert into identidad (persona_id, identificador_acceso, hash_contrasena) values (:p, :i, null)"),
            {"p": persona_id, "i": identificador},
        )
        conexion.execute(
            text("insert into pertenencia (persona_id, equipo_id, rol, desde, hasta_exclusivo) values (:p, :e, :r, :d, null)"),
            {"p": persona_id, "e": equipo_id, "r": rol, "d": desde},
        )
    except IntegrityError as error:
        restriccion = _restriccion(error)
        if restriccion in ("identidad_identificador_acceso_key", "identidad_persona_id_key"):
            raise ErrorDeProvision("IDENTIFICADOR_DUPLICADO") from error
        if restriccion in ("pertenencia_un_supervisor_por_equipo_y_fecha", "pertenencia_sin_solape_por_persona"):
            raise ErrorDeProvision("PERTENENCIA_INVALIDA") from error
        raise
    # IR-34, CA-251: una entrada de provisión; sin credenciales ni identificadores de acceso.
    _auditar(conexion, operador, invocacion, tipo_objeto="persona", objeto_id=persona_id, propietaria=persona_id,
             valor_nuevo={"persona": str(persona_id), "equipo": str(equipo_id), "rol": rol, "desde": desde.isoformat()})
    return PersonaCreada(persona_id, equipo_id, rol, desde)


# ---------------------------------------------------------------------------------------------------- M1-05

@dataclass(frozen=True)
class CambioSolicitado:
    """«Desde ``fecha_efectiva`` la persona pertenece a ``equipo_id`` con el rol ``rol``»."""

    persona_id: uuid.UUID
    equipo_id: uuid.UUID
    rol: str
    fecha_efectiva: date


@dataclass(frozen=True)
class CambioAplicado:
    persona_id: uuid.UUID
    tipo: str                      # traslado, cambio_de_rol o traslado_y_cambio_de_rol
    equipo_anterior_id: uuid.UUID
    rol_anterior: str
    equipo_id: uuid.UUID
    rol: str
    fecha_efectiva: date


@dataclass(frozen=True)
class PertenenciaDelHistorial:
    id: uuid.UUID
    equipo_id: uuid.UUID
    equipo: str
    rol: str
    desde: date
    hasta_exclusivo: date | None


@dataclass(frozen=True)
class TrasladoRegistrado:
    invocacion: uuid.UUID
    cambios: tuple[CambioAplicado, ...]
    historiales: dict[uuid.UUID, tuple[PertenenciaDelHistorial, ...]]   # CA-13: el historial COMPLETO de cada persona afectada


def _bloquear_en_orden(conexion: Connection, claves: Sequence[str]) -> None:
    """Bloquea varias claves SIEMPRE en el mismo orden (ordenadas): dos órdenes que comparten recursos no se bloquean entre sí."""
    for clave in sorted(set(claves)):
        _bloquear(conexion, clave)


def _invalida(motivo: str, indice: int) -> ErrorDeProvision:
    return ErrorDeProvision("PERTENENCIA_INVALIDA", [{"campo": "cambios", "indice": indice, "motivo": motivo}])


def registrar_traslado(conexion: Connection, operador: Operador, *, cambios: Sequence[CambioSolicitado],
                       reloj: Reloj = ahora_utc, invocacion: uuid.UUID | None = None) -> TrasladoRegistrado:
    """M1-05. Registra, en UNA operación atómica, uno o varios cambios de equipo o de rol con efecto futuro (por ejemplo,
    el relevo de un supervisor: el saliente se traslada y el entrante asume la supervisión en la misma fecha).

    Reglas: cada ``fecha_efectiva`` es posterior a la fecha actual de la organización (IR-30, CA-243; el reloj es inyectable,
    D7); solo se cierra el último intervalo sin fin de la persona y se abre otro en esa fecha, sin tocar jamás un intervalo
    existente (IR-30, conservación del historial, CA-249); se valida la línea temporal RESULTANTE completa, la de cada
    persona (IR-02, IR-28: sin solapes ni huecos, un único equipo por fecha, CA-14 y CA-248) y la de cada equipo afectado
    (IR-03, IR-32: como máximo un supervisor y exactamente uno mientras haya colaboradores, CA-240 a CA-242), y el conjunto
    se aplica o se rechaza entero. Una única entrada de auditoría con los valores anterior y nuevo de TODOS los cambios (IR-35).

    Serialización: se bloquean (consultivamente, hasta el fin de la transacción) las personas y después los equipos afectados,
    siempre en el mismo orden; el bloqueo de equipo es el mismo que usa ``crear_persona``. Las restricciones de la base de datos
    y el disparador diferido de IR-32 son la garantía final."""
    invocacion = invocacion or uuid.uuid4()
    cambios = list(cambios)
    if not cambios:
        raise ErrorDeProvision("CAMPO_OBLIGATORIO", [{"campo": "cambios", "motivo": "vacio"}])
    personas = [c.persona_id for c in cambios]
    if len(set(personas)) != len(personas):
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": "cambios", "motivo": "persona_repetida"}])
    for i, c in enumerate(cambios):
        if c.rol not in ROLES:
            raise _invalida("rol_no_valido", i)

    # 1. Las personas, en orden. Con su bloqueo nadie más cambia sus pertenencias hasta el final de la transacción.
    _bloquear_en_orden(conexion, [f"smartwork:pertenencias:persona:{p}" for p in personas])
    existentes = {f.id for f in conexion.execute(text("select id from persona where id = any(cast(:ids as uuid[]))"), {"ids": personas})}
    for i, c in enumerate(cambios):
        if c.persona_id not in existentes:
            raise ErrorDeProvision("RECURSO_NO_DISPONIBLE", [{"campo": "persona", "indice": i}])
    por_persona: dict[uuid.UUID, list] = {p: [] for p in personas}
    for f in conexion.execute(
        text("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia "
             "where persona_id = any(cast(:ids as uuid[])) order by persona_id, desde"), {"ids": personas}):
        por_persona[f.persona_id].append(f)

    equipos = {c.equipo_id for c in cambios} | {por_persona[c.persona_id][-1].equipo_id for c in cambios if por_persona[c.persona_id]}
    datos_equipo = {f.id: f for f in conexion.execute(
        text("select e.id, e.nombre, e.organizacion_id, o.zona_horaria from equipo e "
             "join organizacion o on o.id = e.organizacion_id where e.id = any(cast(:ids as uuid[]))"), {"ids": list(equipos)})}
    for i, c in enumerate(cambios):
        if c.equipo_id not in datos_equipo:
            raise ErrorDeProvision("RECURSO_NO_DISPONIBLE", [{"campo": "equipo", "indice": i}])

    # 2. Reglas de cada cambio.
    ultimas: dict[uuid.UUID, object] = {}
    for i, c in enumerate(cambios):
        historial = por_persona[c.persona_id]
        if not historial:
            raise _invalida("sin_pertenencia", i)  # asignar una primera pertenencia a una persona existente no tiene contrato
        ultima = historial[-1]
        destino = datos_equipo[c.equipo_id]
        if c.fecha_efectiva <= _fecha_actual(destino.zona_horaria, reloj):  # CA-243
            raise ErrorDeProvision("FECHA_EFECTIVA_INVALIDA", [{"campo": "fecha_efectiva", "indice": i}])
        if ultima.hasta_exclusivo is not None:
            raise _invalida("pertenencia_finalizada", i)  # no hay reincorporación (PA-24)
        if datos_equipo[ultima.equipo_id].organizacion_id != destino.organizacion_id:
            raise _invalida("otra_organizacion", i)
        if c.fecha_efectiva <= ultima.desde:  # IR-30: solo se cierra el último intervalo, con un fin posterior a su inicio
            raise _invalida("fecha_no_posterior_al_inicio_de_la_ultima_pertenencia", i)
        if ultima.equipo_id == c.equipo_id and ultima.rol == c.rol:
            raise _invalida("sin_cambio", i)
        ultimas[c.persona_id] = ultima

    # 3. Los equipos afectados, también en orden, y su línea temporal completa leída DESPUÉS de bloquearlos.
    _bloquear_en_orden(conexion, [f"smartwork:pertenencias:equipo:{e}" for e in equipos])
    filas_equipo: dict[uuid.UUID, list[dict]] = {e: [] for e in equipos}
    for f in conexion.execute(
        text("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia "
             "where equipo_id = any(cast(:ids as uuid[]))"), {"ids": list(equipos)}):
        filas_equipo[f.equipo_id].append({"id": f.id, "persona": f.persona_id, "rol": f.rol, "desde": f.desde, "hasta": f.hasta_exclusivo})

    # 4. La línea temporal resultante, en memoria, antes de escribir nada.
    desde_control: dict[uuid.UUID, date] = {}
    for c in cambios:
        ultima = ultimas[c.persona_id]
        for equipo in (ultima.equipo_id, c.equipo_id):
            desde_control[equipo] = min(desde_control.get(equipo, c.fecha_efectiva), c.fecha_efectiva)
        for fila in filas_equipo[ultima.equipo_id]:
            if fila["id"] == ultima.id:
                fila["hasta"] = c.fecha_efectiva
        filas_equipo[c.equipo_id].append({"id": None, "persona": c.persona_id, "rol": c.rol, "desde": c.fecha_efectiva, "hasta": None})
    for i, c in enumerate(cambios):
        ultima = ultimas[c.persona_id]
        tramos = [Tramo(c.persona_id, f.rol, f.desde, f.hasta_exclusivo) for f in por_persona[c.persona_id][:-1]]
        tramos += [Tramo(c.persona_id, ultima.rol, ultima.desde, c.fecha_efectiva), Tramo(c.persona_id, c.rol, c.fecha_efectiva, None)]
        irregularidad = primera_irregularidad_de_persona(tramos)
        if irregularidad is not None:
            raise _invalida(irregularidad, i)
    for equipo in sorted(equipos, key=str):
        violacion = primera_violacion_de_supervision(
            [Tramo(f["persona"], f["rol"], f["desde"], f["hasta"]) for f in filas_equipo[equipo]], desde_control[equipo])
        if violacion is not None:
            motivo = "el_equipo_quedaria_sin_supervisor" if violacion.motivo == "sin_supervisor" else "el_equipo_tendria_mas_de_un_supervisor"
            raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"campo": "equipo", "equipo": str(equipo), "motivo": motivo,
                                                              "fecha": violacion.fecha.isoformat()}])

    # 5. Se aplica: PRIMERO todos los cierres y DESPUÉS todas las aperturas (las restricciones de exclusión se comprueban
    # sentencia a sentencia y un relevo solo es válido con la salida ya registrada).
    nuevas: dict[uuid.UUID, uuid.UUID] = {}
    try:
        for i, c in enumerate(cambios):
            cerradas = conexion.execute(
                text("update pertenencia set hasta_exclusivo = :f where id = :i and hasta_exclusivo is null returning id"),
                {"f": c.fecha_efectiva, "i": ultimas[c.persona_id].id}).all()
            if len(cerradas) != 1:
                raise _invalida("la_pertenencia_ya_no_esta_abierta", i)
        for c in cambios:
            nuevas[c.persona_id] = conexion.execute(
                text("insert into pertenencia (persona_id, equipo_id, rol, desde, hasta_exclusivo) "
                     "values (:p, :e, :r, :d, null) returning id"),
                {"p": c.persona_id, "e": c.equipo_id, "r": c.rol, "d": c.fecha_efectiva}).scalar_one()
        # Fuerza ahora la comprobación diferida de IR-03 e IR-32 de la base: así su rechazo es de ESTA orden.
        conexion.execute(text("set constraints pertenencia_supervision_del_equipo immediate"))
    except IntegrityError as error:
        restriccion = _restriccion(error)
        if restriccion == "pertenencia_supervision_del_equipo":
            raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"campo": "equipo", "motivo": "la_supervision_del_equipo_no_se_cumple"}]) from error
        if restriccion in ("pertenencia_un_supervisor_por_equipo_y_fecha", "pertenencia_sin_solape_por_persona",
                           "pertenencia_solo_cambia_lo_programado", "pertenencia_intervalo_valido"):
            raise ErrorDeProvision("PERTENENCIA_INVALIDA") from error
        raise

    aplicados = tuple(CambioAplicado(
        c.persona_id,
        "traslado_y_cambio_de_rol" if (ultimas[c.persona_id].equipo_id != c.equipo_id and ultimas[c.persona_id].rol != c.rol)
        else "traslado" if ultimas[c.persona_id].equipo_id != c.equipo_id else "cambio_de_rol",
        ultimas[c.persona_id].equipo_id, ultimas[c.persona_id].rol, c.equipo_id, c.rol, c.fecha_efectiva) for c in cambios)

    # 6. IR-35: UNA entrada con los valores anterior y nuevo de TODOS los cambios; sin credenciales ni identificadores de acceso.
    # La operación afecta a varias personas y equipos, así que el objeto de la entrada es la propia operación (su invocación).
    _auditar(
        conexion, operador, invocacion, tipo_objeto="operacion_de_pertenencia", objeto_id=invocacion, propietaria=None,
        operacion="cambio_pertenencia",
        valor_anterior={"cambios": [
            {"persona": str(c.persona_id),
             "pertenencia": {"id": str(ultimas[c.persona_id].id), "equipo": str(ultimas[c.persona_id].equipo_id),
                             "rol": ultimas[c.persona_id].rol, "desde": ultimas[c.persona_id].desde.isoformat(), "hasta_exclusivo": None}}
            for c in cambios]},
        valor_nuevo={"cambios": [
            {"persona": str(a.persona_id), "tipo": a.tipo, "fecha_efectiva": a.fecha_efectiva.isoformat(),
             "pertenencia_cerrada": {"id": str(ultimas[a.persona_id].id), "hasta_exclusivo": a.fecha_efectiva.isoformat()},
             "pertenencia_nueva": {"id": str(nuevas[a.persona_id]), "equipo": str(a.equipo_id), "rol": a.rol,
                                   "desde": a.fecha_efectiva.isoformat(), "hasta_exclusivo": None}}
            for a in aplicados]},
    )

    # 7. CA-13: el historial completo de cada persona afectada (los intervalos anteriores, intactos, y los nuevos).
    historiales: dict[uuid.UUID, list[PertenenciaDelHistorial]] = {p: [] for p in personas}
    for f in conexion.execute(
        text("select p.persona_id, p.id, p.equipo_id, e.nombre, p.rol, p.desde, p.hasta_exclusivo from pertenencia p "
             "join equipo e on e.id = p.equipo_id where p.persona_id = any(cast(:ids as uuid[])) order by p.persona_id, p.desde"),
        {"ids": personas}):
        historiales[f.persona_id].append(PertenenciaDelHistorial(f.id, f.equipo_id, f.nombre, f.rol, f.desde, f.hasta_exclusivo))
    return TrasladoRegistrado(invocacion, aplicados, {p: tuple(h) for p, h in historiales.items()})
