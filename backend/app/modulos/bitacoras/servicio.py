"""Casos de uso de M2: consultar, abrir y planificar (M2-01a, M2-01b, M2-03)."""

from datetime import date

from sqlalchemy.orm import Session

from app.compartido.auditoria import registrar_operacion_de_persona
from app.compartido.dependencias import Operador
from app.compartido.fechas import parsear_fecha_laboral
from app.compartido.idempotencia import Resultado, calcular_huella, ejecutar_con_clave
from app.compartido.politica_acceso import fecha_cubierta
from app.config import get_settings
from app.errores import AppError
from app.modulos.bitacoras import repositorio
from app.modulos.bitacoras.esquemas import (
    PlanificarEntrada, actividad_a_dict, avance_a_dict, bitacora_a_dict, planificacion_a_dict,
)

OPERACION_PLANIFICAR = "M2-03"


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
