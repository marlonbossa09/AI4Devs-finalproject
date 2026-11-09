"""Casos de uso de M2: consultar, abrir, planificar, registrar avances y consultar actividades
(M2-01a, M2-01b, M2-03, M2-05, M2-07, M2-08)."""

import base64
import binascii
import json
import re
from datetime import date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido.auditoria import registrar_operacion_de_persona
from app.compartido.dependencias import Operador
from app.compartido.fechas import parsear_fecha_laboral
from app.compartido.idempotencia import Resultado, calcular_huella, ejecutar_con_clave
from app.compartido.politica_acceso import fecha_cubierta
from app.config import get_settings
from app.errores import AppError
from app.modulos.bitacoras import repositorio, secuencia
from app.modulos.bitacoras.esquemas import (
    AvanceEntrada, ContinuacionEntrada, NoPlanificadaEntrada, PlanificarEntrada, ReaperturaEntrada, ResumenEntrada,
    actividad_a_dict, momento,
    avance_a_dict, bitacora_a_dict, planificacion_a_dict,
)

OPERACION_PLANIFICAR = "M2-03"
OPERACION_AVANCE = "M2-05"
OPERACION_NO_PLANIFICADA = "M2-06"
OPERACION_CONTINUACION = "M2-04"
OPERACION_CIERRE = "M3-01"
OPERACION_REAPERTURA = "M3-02"

# Parámetros de consulta que admite M2-08. Cualquier otro se rechaza (convenciones 2: no hay búsquedas
# ni filtros que el producto no contemple).
PARAMETROS_LISTADO = frozenset({"estado", "limite", "continuar_desde"})


def validar_texto(valor: str | None, campo: str, *, obligatorio: bool, maximo: int) -> str:
    """Obligatoriedad y longitud (convenciones 6.2). La longitud se mide en caracteres Unicode,
    tras recortar los espacios de los extremos. El texto se conserva tal como se recibe."""
    recortado = (valor or "").strip()
    if obligatorio and not recortado:
        raise AppError("CAMPO_OBLIGATORIO", [{"campo": campo, "motivo": "obligatorio"}])
    if len(recortado) > maximo:
        raise AppError("TEXTO_DEMASIADO_LARGO", [{"campo": campo, "maximo": maximo}])
    return valor or ""


def _exigir_fecha_cubierta(db: Session, op: Operador, fecha: date) -> None:
    if not fecha_cubierta(db, op.persona_id, fecha):
        raise AppError("FECHA_NO_CUBIERTA", [{"campo": "fecha_laboral", "motivo": "fuera_de_la_pertenencia"}])


def consultar_bitacora(db: Session, op: Operador, fecha_laboral: str) -> dict:
    """M2-01a. Nunca crea nada (D-01): sin bitácora, el recurso no está disponible."""
    fecha = parsear_fecha_laboral(fecha_laboral)
    bitacora = repositorio.obtener_bitacora(db, op.persona_id, fecha)
    if bitacora is None:
        raise AppError("RECURSO_NO_DISPONIBLE")
    return {
        "bitacora": bitacora_a_dict(bitacora, op.contexto.fecha_actual),
        "planificaciones": [planificacion_a_dict(p, fecha) for p in repositorio.listar_planificaciones(db, bitacora.id)],
        "avances": [avance_a_dict(a, fecha) for a in repositorio.listar_avances(db, bitacora.id)],
        "actividades": [
            actividad_a_dict(a, a.fecha_laboral_origen)
            for a in repositorio.listar_actividades_referenciadas(db, op.persona_id, bitacora.id)
        ],
    }


def abrir_bitacora(db: Session, op: Operador, fecha_laboral: str) -> tuple[int, dict]:
    """M2-01b. Idempotente por naturaleza: 201 si la crea, 200 si ya existía (sin modificarla, sin
    auditoría y sin reabrirla). Abrir una bitácora vacía no es una escritura efectiva (D-02)."""
    fecha = parsear_fecha_laboral(fecha_laboral)
    _exigir_fecha_cubierta(db, op, fecha)
    bitacora, creada = repositorio.obtener_o_crear_bitacora(db, op.persona_id, fecha)
    return (201 if creada else 200), {"creada": creada, "bitacora": bitacora_a_dict(bitacora, op.contexto.fecha_actual)}


def planificar_actividad(
    db: Session, op: Operador, fecha_laboral: str, entrada: PlanificarEntrada, clave: str | None
) -> Resultado:
    """M2-03. Crea la actividad (Pendiente) y su planificación original en una sola transacción; si
    la bitácora no existe, se crea en la misma (D-01). En una jornada pasada la operación se audita
    con una única entrada, que incluye la creación implícita de la bitácora (RN-45, RN-111)."""
    fecha = parsear_fecha_laboral(fecha_laboral)
    huella = calcular_huella({
        "fecha_laboral": fecha.isoformat(), "titulo": entrada.titulo, "descripcion": entrada.descripcion,
    })
    settings = get_settings()

    def ejecutar() -> tuple[int, dict]:
        titulo = validar_texto(entrada.titulo, "titulo", obligatorio=True, maximo=settings.text_max_title)
        descripcion = validar_texto(entrada.descripcion, "descripcion", obligatorio=False,
                                    maximo=settings.text_max_description)
        _exigir_fecha_cubierta(db, op, fecha)
        bitacora, creada = repositorio.obtener_o_crear_bitacora(db, op.persona_id, fecha)
        # La fila se bloquea antes de mirar si está cerrada: un cierre simultáneo (M3-01) se serializa con
        # esta escritura, así que nunca entra contenido en una jornada que ya se cerró (RN-108)
        bitacora = repositorio.bloquear_bitacora(db, bitacora.id)
        if bitacora.estado == "cerrada":
            raise AppError("BITACORA_CERRADA")
        actividad = repositorio.insertar_actividad(db, op.persona_id, bitacora.id, titulo)
        planificacion = repositorio.insertar_planificacion_original(db, actividad.id, bitacora.id, descripcion)
        cuerpo = {
            "actividad": actividad_a_dict(actividad, fecha),
            "planificacion": planificacion_a_dict(planificacion, fecha),
            "bitacora_creada": creada,
        }
        if fecha < op.contexto.fecha_actual:  # jornada pasada: toda escritura efectiva se audita
            registrar_operacion_de_persona(
                db,
                autor_persona_id=op.persona_id,
                operacion="modificacion_jornada_pasada",
                tipo_objeto="actividad",
                objeto_id=actividad.id,
                propietaria_registro_id=op.persona_id,
                fecha_laboral_registro=fecha,
                valor_anterior={"bitacora_existia": not creada},
                valor_nuevo={
                    "bitacora_id": str(bitacora.id),
                    "bitacora_creada": creada,
                    "actividad": {"id": str(actividad.id), "titulo": actividad.titulo,
                                  "origen": actividad.origen, "estado_actual": actividad.estado_actual},
                    "planificacion": {"id": str(planificacion.id), "tipo": planificacion.tipo,
                                      "descripcion": planificacion.descripcion},
                },
            )
        return 201, cuerpo

    return ejecutar_con_clave(
        db, persona_id=op.persona_id, operacion=OPERACION_PLANIFICAR, clave=clave, huella=huella, ejecutar=ejecutar
    )


def _validar_avance(entrada: AvanceEntrada | NoPlanificadaEntrada, maximo: int) -> tuple[str, str, str | None]:
    """Estado, descripción y motivo de bloqueo de un avance (CA-48, CA-49, CA-68, CA-69)."""
    estado = entrada.estado
    if estado not in secuencia.ESTADOS:
        raise AppError("ESTADO_INVALIDO", [{"campo": "estado", "motivo": "no_es_uno_de_los_cuatro"}])
    if not (entrada.descripcion or "").strip():
        raise AppError("DESCRIPCION_OBLIGATORIA", [{"campo": "descripcion", "motivo": "obligatorio"}])
    descripcion = validar_texto(entrada.descripcion, "descripcion", obligatorio=True, maximo=maximo)
    if estado == secuencia.BLOQUEADA:
        if not (entrada.motivo_bloqueo or "").strip():
            raise AppError("MOTIVO_BLOQUEO_OBLIGATORIO", [{"campo": "motivo_bloqueo", "motivo": "obligatorio"}])
        return estado, descripcion, validar_texto(entrada.motivo_bloqueo, "motivo_bloqueo", obligatorio=True,
                                                  maximo=maximo)
    if entrada.motivo_bloqueo is not None:  # el motivo solo existe para el estado Bloqueada (M2-05)
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "motivo_bloqueo", "motivo": "solo_si_el_estado_es_bloqueada"}])
    return estado, descripcion, None


def registrar_avance(
    db: Session, op: Operador, actividad_id: UUID, entrada: AvanceEntrada, clave: str | None
) -> Resultado:
    """M2-05. Registra un avance de ejecución sobre una actividad PROPIA: cambia el estado y describe
    el trabajo. En una sola transacción, serializada por actividad (DM-01): crea el avance, recalcula
    ``estado_actual`` (IR-12) y, si la jornada es pasada, deja una única entrada de auditoría (RN-45).

    Solo debe estar abierta la bitácora de la fecha del avance (D-04): no se reabren las jornadas
    anteriores en las que la actividad ya tiene avances (CA-96). Si esa bitácora no existe, se crea en
    la misma transacción (D-01). Sin reactivación (M3-04, fuera de esta entrega) no se admite un avance
    que quede tras una finalización (CA-190, CA-206, CA-207), pero sí uno retroactivo anterior a ella
    (CA-203 a CA-205)."""
    fecha = parsear_fecha_laboral(entrada.fecha_laboral)
    huella = calcular_huella({
        "actividad_id": str(actividad_id), "fecha_laboral": fecha.isoformat(), "estado": entrada.estado,
        "descripcion": entrada.descripcion, "motivo_bloqueo": entrada.motivo_bloqueo,
    })
    settings = get_settings()

    def ejecutar() -> tuple[int, dict]:
        # Visibilidad primero (T-01): una actividad ajena es indistinguible de una inexistente.
        actividad = repositorio.obtener_actividad_propia(db, op.persona_id, actividad_id, bloquear=True)
        if actividad is None:
            raise AppError("RECURSO_NO_DISPONIBLE")
        if actividad.registrada_por_error:
            raise AppError("ACTIVIDAD_MARCADA_POR_ERROR")
        estado, descripcion, motivo = _validar_avance(entrada, settings.text_max_description)
        if fecha > op.contexto.fecha_actual:
            raise AppError("FECHA_FUTURA_NO_PERMITIDA", [{"campo": "fecha_laboral", "motivo": "ejecucion_futura"}])
        _exigir_fecha_cubierta(db, op, fecha)
        bitacora, creada = repositorio.obtener_o_crear_bitacora(db, op.persona_id, fecha)
        # La fila se bloquea antes de mirar si está cerrada: un cierre simultáneo (M3-01) se serializa con
        # esta escritura, así que nunca entra contenido en una jornada que ya se cerró (RN-108)
        bitacora = repositorio.bloquear_bitacora(db, bitacora.id)
        if bitacora.estado == "cerrada":
            raise AppError("BITACORA_CERRADA")
        existentes = [
            secuencia.AvanceEnSecuencia(r.id, r.fecha_laboral, r.registrado_en, r.estado, r.es_reactivacion)
            for r in repositorio.listar_avances_de_actividad(db, actividad.id)
        ]
        if secuencia.quedaria_tras_una_finalizacion(existentes, fecha):
            raise AppError("ACTIVIDAD_COMPLETADA")

        avance = repositorio.insertar_avance(db, actividad.id, bitacora.id, estado, descripcion, motivo)
        estado_anterior = actividad.estado_actual
        estado_nuevo = secuencia.estado_actual_tras_insertar(existentes, fecha, estado)
        if estado_nuevo != estado_anterior:
            repositorio.actualizar_estado_actual(db, actividad.id, estado_nuevo)

        if fecha < op.contexto.fecha_actual:  # jornada pasada: toda escritura efectiva se audita
            registrar_operacion_de_persona(
                db,
                autor_persona_id=op.persona_id,
                operacion="modificacion_jornada_pasada",
                tipo_objeto="avance",
                objeto_id=avance.id,
                propietaria_registro_id=op.persona_id,
                fecha_laboral_registro=fecha,
                valor_anterior={"actividad_id": str(actividad.id), "estado_actual": estado_anterior,
                                "bitacora_existia": not creada},
                valor_nuevo={
                    "actividad_id": str(actividad.id),
                    "estado_actual": estado_nuevo,
                    "bitacora_id": str(bitacora.id),
                    "bitacora_creada": creada,
                    "avance": {"id": str(avance.id), "estado": avance.estado, "descripcion": avance.descripcion,
                               "motivo_bloqueo": avance.motivo_bloqueo},
                },
            )
        final = repositorio.obtener_actividad_propia(db, op.persona_id, actividad.id)
        return 201, {
            "avance": avance_a_dict(avance, fecha),
            "actividad": actividad_a_dict(final, final.fecha_laboral_origen),
            "bitacora_creada": creada,
        }

    return ejecutar_con_clave(
        db, persona_id=op.persona_id, operacion=OPERACION_AVANCE, clave=clave, huella=huella, ejecutar=ejecutar
    )


# =============================== M2-07 y M2-08: consultar actividades propias ===========================

def consultar_actividad(db: Session, op: Operador, actividad_id: UUID) -> dict:
    """M2-07. La actividad completa de la propietaria: planificación original, continuaciones
    planificadas (que no forman parte de la secuencia), avances en el orden de la secuencia y estado
    actual. Solo lectura. Una actividad marcada por error sigue siendo consultable (CA-120, CA-121).
    Una actividad ajena es indistinguible de una inexistente (T-01); la visibilidad histórica de M4
    (403 para registros visibles de otras personas) no existe todavía."""
    actividad = repositorio.obtener_actividad_propia(db, op.persona_id, actividad_id)
    if actividad is None:
        raise AppError("RECURSO_NO_DISPONIBLE")
    planificaciones = repositorio.listar_planificaciones_de_actividad(db, actividad.id)
    original = next((p for p in planificaciones if p.tipo == "original"), None)
    return {
        "actividad": actividad_a_dict(actividad, actividad.fecha_laboral_origen),
        "planificacion_original": planificacion_a_dict(original, original.fecha_laboral) if original else None,
        "continuaciones_planificadas": [
            planificacion_a_dict(p, p.fecha_laboral) for p in planificaciones if p.tipo == "continuacion"
        ],
        "avances": [avance_a_dict(a, a.fecha_laboral) for a in repositorio.listar_avances_con_fecha(db, actividad.id)],
        "estado_actual": actividad.estado_actual,
    }


def _error_de_listado(campo: str, motivo: str, **extra: object) -> AppError:
    return AppError("SOLICITUD_INVALIDA", [{"campo": campo, "motivo": motivo, **extra}])


def _limite_de(valor: str | None) -> int:
    """``limite`` con su valor por defecto y su máximo configurables (convenciones 6.1)."""
    settings = get_settings()
    if valor is None:
        return settings.pagination_default_limit
    if not re.fullmatch(r"[0-9]{1,9}", valor) or not 1 <= int(valor) <= settings.pagination_max_limit:
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "limite", "maximo": settings.pagination_max_limit}])
    return int(valor)


def _cursor_de(valor: str | None) -> tuple[str, str] | None:
    """El cursor es opaco para quien consulta: (``creada_en``, ``id``) del último elemento entregado.
    Uno inválido se rechaza igual que un ``limite`` inválido (convenciones 6.1)."""
    if valor is None:
        return None
    try:
        contenido = json.loads(base64.urlsafe_b64decode(valor.encode("ascii") + b"=" * (-len(valor) % 4)))
        creada = datetime.fromisoformat(contenido["c"])
        identificador = UUID(contenido["i"])
        if creada.tzinfo is None:
            raise ValueError("sin zona horaria")
    except (ValueError, KeyError, TypeError, binascii.Error, UnicodeError):
        raise _error_de_listado("continuar_desde", "cursor_invalido") from None
    return creada.isoformat(), str(identificador)


def _emitir_cursor(fila) -> str:
    contenido = json.dumps({"c": fila.creada_en.isoformat(), "i": str(fila.id)}, separators=(",", ":"))
    return base64.urlsafe_b64encode(contenido.encode("ascii")).decode("ascii").rstrip("=")


def listar_actividades(
    db: Session, op: Operador, estados: list[str] | None, limite: str | None, continuar_desde: str | None,
    parametros_recibidos: set[str],
) -> dict:
    """M2-08. Mis actividades, sin las marcadas por error (CA-119), más reciente primero (momento de
    creación y, de desempate, identificador). Cada actividad cuenta una sola vez aunque tenga avances en
    varias jornadas (CA-82); dos con el mismo título siguen siendo distintas (CA-85). Solo las propias
    (CA-88): la autorización se aplica al seleccionar, antes de paginar (convenciones 3.3 y 6.1).

    Orden de evaluación (convenciones 3.2): primero el formato de los parámetros."""
    for nombre in sorted(parametros_recibidos - PARAMETROS_LISTADO):
        raise _error_de_listado(nombre, "parametro_no_soportado")
    filtro = None
    if estados:
        if any(e not in secuencia.ESTADOS for e in estados):
            raise _error_de_listado("estado", "estado_no_valido")
        filtro = sorted(set(estados))
    cantidad = _limite_de(limite)
    cursor = _cursor_de(continuar_desde)

    filas = repositorio.listar_actividades_propias(db, op.persona_id, filtro, cursor, cantidad + 1)
    pagina = filas[:cantidad]
    return {
        "elementos": [
            {"id": str(a.id), "titulo": a.titulo, "origen": a.origen, "estado_actual": a.estado_actual}
            for a in pagina
        ],
        "siguiente": _emitir_cursor(pagina[-1]) if len(filas) > cantidad else None,
    }


# =============================== M2-06: actividad no planificada ==========================================

def registrar_no_planificada(
    db: Session, op: Operador, entrada: NoPlanificadaEntrada, clave: str | None
) -> Resultado:
    """M2-06. Registra trabajo que no se había planificado: crea la actividad (origen
    ``no_planificada``, que es una identificación y no un quinto estado, RN-20) y su primer avance en
    UNA transacción atómica (IR-13). La actividad empieza con el estado de ese primer avance (RN-69).

    No existe planificación original: no se inventa una (IR-16). Si la bitácora de la fecha no existe,
    se crea en la misma transacción (D-01); si está cerrada, ``BITACORA_CERRADA`` (D-04). La fecha no
    puede ser futura: no se registra ejecución futura (CA-43, RN-27); sí cualquier fecha pasada o la
    actual, con cualquiera de los cuatro estados (CA-44, CA-59, CA-60). En una jornada pasada la
    operación es una modificación auditable, con una única entrada que incluye la creación implícita de
    la bitácora (RN-45, D-02)."""
    fecha = parsear_fecha_laboral(entrada.fecha_laboral)
    huella = calcular_huella({
        "fecha_laboral": fecha.isoformat(), "titulo": entrada.titulo, "estado": entrada.estado,
        "descripcion": entrada.descripcion, "motivo_bloqueo": entrada.motivo_bloqueo,
    })
    settings = get_settings()

    def ejecutar() -> tuple[int, dict]:
        titulo = validar_texto(entrada.titulo, "titulo", obligatorio=True, maximo=settings.text_max_title)
        estado, descripcion, motivo = _validar_avance(entrada, settings.text_max_description)
        if fecha > op.contexto.fecha_actual:
            raise AppError("FECHA_FUTURA_NO_PERMITIDA", [{"campo": "fecha_laboral", "motivo": "ejecucion_futura"}])
        _exigir_fecha_cubierta(db, op, fecha)
        bitacora, creada = repositorio.obtener_o_crear_bitacora(db, op.persona_id, fecha)
        # La fila se bloquea antes de mirar si está cerrada: un cierre simultáneo (M3-01) se serializa con
        # esta escritura, así que nunca entra contenido en una jornada que ya se cerró (RN-108)
        bitacora = repositorio.bloquear_bitacora(db, bitacora.id)
        if bitacora.estado == "cerrada":
            raise AppError("BITACORA_CERRADA")

        actividad = repositorio.insertar_actividad(
            db, op.persona_id, bitacora.id, titulo, origen="no_planificada", estado_actual=estado
        )
        avance = repositorio.insertar_avance(db, actividad.id, bitacora.id, estado, descripcion, motivo)

        if fecha < op.contexto.fecha_actual:  # jornada pasada: toda escritura efectiva se audita
            registrar_operacion_de_persona(
                db,
                autor_persona_id=op.persona_id,
                operacion="modificacion_jornada_pasada",
                tipo_objeto="actividad",
                objeto_id=actividad.id,
                propietaria_registro_id=op.persona_id,
                fecha_laboral_registro=fecha,
                valor_anterior={"bitacora_existia": not creada},
                valor_nuevo={
                    "bitacora_id": str(bitacora.id),
                    "bitacora_creada": creada,
                    "actividad": {"id": str(actividad.id), "titulo": actividad.titulo,
                                  "origen": actividad.origen, "estado_actual": actividad.estado_actual},
                    "avance": {"id": str(avance.id), "estado": avance.estado, "descripcion": avance.descripcion,
                               "motivo_bloqueo": avance.motivo_bloqueo},
                },
            )
        return 201, {
            "actividad": actividad_a_dict(actividad, fecha),
            "avance": avance_a_dict(avance, fecha),
            "bitacora_creada": creada,
        }

    return ejecutar_con_clave(
        db, persona_id=op.persona_id, operacion=OPERACION_NO_PLANIFICADA, clave=clave, huella=huella,
        ejecutar=ejecutar,
    )


# =============================== M2-02: resumen libre de la bitácora ==========================================

def guardar_resumen(db: Session, op: Operador, fecha_laboral: str, entrada: ResumenEntrada) -> dict:
    """M2-02. Guarda (reemplaza) el resumen libre de MI bitácora de una fecha.

    - Es un reemplazo, naturalmente idempotente: repetirlo deja lo mismo. Por eso el contrato no exige
      ``Idempotency-Key``.
    - Si la bitácora no existe se crea en la misma transacción, con las condiciones de M2-01b (D-01):
      fecha cubierta por una pertenencia, pasada sin límite de antigüedad, futura admitida.
    - Un resumen vacío (o solo espacios) se acepta: solo impide cerrar la jornada (RN-21, M3-01).
    - Una jornada cerrada exige reabrirla antes (RN-108, D-04): ``BITACORA_CERRADA``.
    - ``modificada_en`` se renueva siempre (RN-18).
    - Auditoría (RN-45, RN-49, IR-35): una única entrada, con el resumen anterior y el nuevo, si la fecha
      es pasada o la bitácora fue reabierta; ninguna en una jornada actual o futura. Guardar un resumen
      vacío donde no había contenido no es una escritura efectiva (D-02) y no se audita; vaciar un
      resumen que sí tenía contenido SÍ lo es, porque cambia el registro. La creación implícita de la
      bitácora va en la misma entrada.
    - Todo en una transacción; la fila de la bitácora se bloquea para serializar las escrituras
      simultáneas sobre la misma jornada."""
    fecha = parsear_fecha_laboral(fecha_laboral)
    resumen = validar_texto(entrada.resumen, "resumen", obligatorio=False, maximo=get_settings().text_max_summary)
    _exigir_fecha_cubierta(db, op, fecha)
    bitacora, creada = repositorio.obtener_o_crear_bitacora(db, op.persona_id, fecha)
    bitacora = repositorio.bloquear_bitacora(db, bitacora.id)
    if bitacora.estado == "cerrada":
        raise AppError("BITACORA_CERRADA")

    anterior = bitacora.resumen
    reabierta = repositorio.bitacora_fue_reabierta(db, bitacora.id)
    pasada = fecha < op.contexto.fecha_actual
    actualizada = repositorio.guardar_resumen(db, bitacora.id, resumen)

    efectiva = bool(anterior.strip()) or bool(resumen.strip())
    if (pasada or reabierta) and efectiva:
        registrar_operacion_de_persona(
            db,
            autor_persona_id=op.persona_id,
            operacion="modificacion_jornada_pasada" if pasada else "correccion",
            tipo_objeto="bitacora",
            objeto_id=bitacora.id,
            propietaria_registro_id=op.persona_id,
            fecha_laboral_registro=fecha,
            valor_anterior={"resumen": anterior, "bitacora_existia": not creada},
            valor_nuevo={"resumen": resumen, "bitacora_creada": creada, "bitacora_id": str(bitacora.id)},
        )
    return {"bitacora": bitacora_a_dict(actualizada, op.contexto.fecha_actual), "bitacora_creada": creada}


# =============================== M2-04: continuación planificada ==============================================

def planificar_continuacion(
    db: Session, op: Operador, actividad_id: UUID, entrada: ContinuacionEntrada, clave: str | None
) -> Resultado:
    """M2-04. Registra la continuación planificada de una actividad PROPIA para una jornada futura.

    - Es una planificación: no crea otra actividad (CA-179), no crea ningún avance, no entra en la
      secuencia y no cambia el estado actual (RN-75, CA-180, CA-181, CA-185, CA-186).
    - La fecha debe ser posterior a la actual (``FECHA_NO_FUTURA``, RN-76) y estar cubierta por una
      pertenencia mía (``FECHA_NO_CUBIERTA``).
    - Una actividad Completada se rechaza con ``ACTIVIDAD_COMPLETADA`` mientras no se reactive (RN-78,
      CA-209; la reactivación es M3-04, fuera de esta entrega). Una marcada por error, con
      ``ACTIVIDAD_MARCADA_POR_ERROR``.
    - Si la bitácora de esa jornada futura no existe, se crea en la misma transacción (D-01); nunca está
      cerrada, porque no se cierran jornadas futuras (RN-46).
    - No audita: no modifica una jornada pasada.
    - La fila de la actividad se bloquea: un avance Completada simultáneo se serializa con esta
      planificación, así que nunca queda una continuación planificada tras una finalización (IR-17).
    - Dos continuaciones para la misma actividad y fecha, con claves distintas, son dos intenciones
      distintas y se registran las dos (las continuaciones son varias, IR-16); un reintento con la misma
      clave no duplica nada (T-04)."""
    fecha = parsear_fecha_laboral(entrada.fecha_laboral)
    huella = calcular_huella({
        "actividad_id": str(actividad_id), "fecha_laboral": fecha.isoformat(), "descripcion": entrada.descripcion,
    })
    settings = get_settings()

    def ejecutar() -> tuple[int, dict]:
        # Visibilidad primero (T-01): una actividad ajena es indistinguible de una inexistente.
        actividad = repositorio.obtener_actividad_propia(db, op.persona_id, actividad_id, bloquear=True)
        if actividad is None:
            raise AppError("RECURSO_NO_DISPONIBLE")
        if actividad.registrada_por_error:
            raise AppError("ACTIVIDAD_MARCADA_POR_ERROR")
        descripcion = validar_texto(entrada.descripcion, "descripcion", obligatorio=False,
                                    maximo=settings.text_max_description)
        if fecha <= op.contexto.fecha_actual:
            raise AppError("FECHA_NO_FUTURA", [{"campo": "fecha_laboral", "motivo": "no_es_posterior_a_la_actual"}])
        _exigir_fecha_cubierta(db, op, fecha)
        if actividad.estado_actual == secuencia.COMPLETADA:
            raise AppError("ACTIVIDAD_COMPLETADA")

        bitacora, creada = repositorio.obtener_o_crear_bitacora(db, op.persona_id, fecha)
        planificacion = repositorio.insertar_continuacion_planificada(db, actividad.id, bitacora.id, descripcion)
        final = repositorio.obtener_actividad_propia(db, op.persona_id, actividad.id)  # el estado no cambió
        return 201, {
            "planificacion": planificacion_a_dict(planificacion, fecha),
            "actividad": actividad_a_dict(final, final.fecha_laboral_origen),
            "bitacora_creada": creada,
        }

    return ejecutar_con_clave(
        db, persona_id=op.persona_id, operacion=OPERACION_CONTINUACION, clave=clave, huella=huella,
        ejecutar=ejecutar,
    )


# =============================== M3-01 y M3-02: cierre y reapertura de la jornada ================================

def cerrar_bitacora(db: Session, op: Operador, fecha_laboral: str, clave: str | None) -> Resultado:
    """M3-01. Cierra MI bitácora de una fecha, de forma manual (CA-89).

    - No crea la bitácora: si no existe (o no es mía), ``RECURSO_NO_DISPONIBLE`` (D-01, CA-98).
    - Una jornada futura no se cierra (``FECHA_FUTURA_NO_PERMITIDA``, CA-97); una ya cerrada devuelve
      ``BITACORA_CERRADA``.
    - Condiciones (RN-21, CA-90 a CA-94): un resumen con texto (ni vacío ni solo espacios) y al menos una
      actividad válida creada en la jornada o continuada en ella con un avance de esa fecha. Una
      continuación planificada no cuenta (CA-184) ni las actividades marcadas por error (RN-109, CA-283).
      Si falta algo, ``CONDICIONES_DE_CIERRE_NO_CUMPLIDAS`` con TODO lo que falta en ``detalles``.
    - Las actividades conservan su estado (CA-95): no se tocan.
    - Una entrada de auditoría por cierre, con el estado anterior y el nuevo (RN-103, CA-266), en la misma
      transacción. La fila de la bitácora se bloquea: las escrituras simultáneas sobre la jornada (resumen,
      actividades, avances) se serializan con el cierre, así que no se cierra con contenido a medias ni
      entra contenido en una jornada recién cerrada."""
    fecha = parsear_fecha_laboral(fecha_laboral)
    huella = calcular_huella({"fecha_laboral": fecha.isoformat()})

    def ejecutar() -> tuple[int, dict]:
        existente = repositorio.obtener_bitacora(db, op.persona_id, fecha)
        if existente is None:
            raise AppError("RECURSO_NO_DISPONIBLE")
        bitacora = repositorio.bloquear_bitacora(db, existente.id)
        if bitacora.estado == "cerrada":
            raise AppError("BITACORA_CERRADA")
        if fecha > op.contexto.fecha_actual:
            raise AppError("FECHA_FUTURA_NO_PERMITIDA", [{"campo": "fecha_laboral", "motivo": "cierre_futuro"}])
        faltan = []
        if not bitacora.resumen.strip():
            faltan.append({"campo": "resumen", "motivo": "vacio"})
        if repositorio.contar_actividades_efectivas(db, op.persona_id, bitacora.id) == 0:
            faltan.append({"campo": "actividades", "motivo": "sin_actividad_creada_ni_continuada"})
        if faltan:
            raise AppError("CONDICIONES_DE_CIERRE_NO_CUMPLIDAS", faltan)

        cerrada = repositorio.cerrar_bitacora(db, bitacora.id)
        registrar_operacion_de_persona(
            db,
            autor_persona_id=op.persona_id,
            operacion="cierre",
            tipo_objeto="bitacora",
            objeto_id=bitacora.id,
            propietaria_registro_id=op.persona_id,
            fecha_laboral_registro=fecha,
            valor_anterior={"estado": "abierta", "cerrada_en": None},
            valor_nuevo={"estado": "cerrada", "cerrada_en": momento(cerrada.cerrada_en)},
        )
        return 200, {"bitacora": bitacora_a_dict(cerrada, op.contexto.fecha_actual)}

    return ejecutar_con_clave(
        db, persona_id=op.persona_id, operacion=OPERACION_CIERRE, clave=clave, huella=huella, ejecutar=ejecutar
    )


def reabrir_bitacora(
    db: Session, op: Operador, fecha_laboral: str, entrada: ReaperturaEntrada, clave: str | None
) -> Resultado:
    """M3-02. Reabre MI bitácora cerrada, con un motivo obligatorio (RN-50, CA-100).

    - No crea la bitácora; la de otra persona no existe para quien pregunta, tampoco para un supervisor
      (CA-101, T-01).
    - Debe estar cerrada (``BITACORA_NO_CERRADA``). Reabrir una jornada no obliga a reabrir otras (D-04).
    - Una entrada de auditoría con el motivo, el autor, el momento y el estado anterior y el nuevo, en la
      misma transacción (CA-102, CA-109). Cada cierre y cada reapertura quedan como entradas propias, así
      que los ciclos se reconstruyen (CA-266).
    - Desde ese momento se admiten de nuevo las operaciones sobre la jornada, y las correcciones del
      resumen quedan auditadas (M2-02)."""
    fecha = parsear_fecha_laboral(fecha_laboral)
    huella = calcular_huella({"fecha_laboral": fecha.isoformat(), "motivo": entrada.motivo})

    def ejecutar() -> tuple[int, dict]:
        existente = repositorio.obtener_bitacora(db, op.persona_id, fecha)
        if existente is None:
            raise AppError("RECURSO_NO_DISPONIBLE")
        motivo = entrada.motivo or ""
        if not motivo.strip():
            raise AppError("MOTIVO_OBLIGATORIO", [{"campo": "motivo", "motivo": "obligatorio"}])
        motivo = validar_texto(motivo, "motivo", obligatorio=True, maximo=get_settings().text_max_description)
        bitacora = repositorio.bloquear_bitacora(db, existente.id)
        if bitacora.estado != "cerrada":
            raise AppError("BITACORA_NO_CERRADA")

        reabierta = repositorio.reabrir_bitacora(db, bitacora.id)
        registrar_operacion_de_persona(
            db,
            autor_persona_id=op.persona_id,
            operacion="reapertura",
            tipo_objeto="bitacora",
            objeto_id=bitacora.id,
            propietaria_registro_id=op.persona_id,
            fecha_laboral_registro=fecha,
            motivo=motivo,
            valor_anterior={"estado": "cerrada", "cerrada_en": momento(bitacora.cerrada_en)},
            valor_nuevo={"estado": "abierta", "cerrada_en": None},
        )
        return 200, {"bitacora": bitacora_a_dict(reabierta, op.contexto.fecha_actual)}

    return ejecutar_con_clave(
        db, persona_id=op.persona_id, operacion=OPERACION_REAPERTURA, clave=clave, huella=huella, ejecutar=ejecutar
    )
