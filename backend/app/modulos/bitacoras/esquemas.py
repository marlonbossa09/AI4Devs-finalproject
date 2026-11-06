"""Esquemas de M2-01a, M2-01b y M2-03 (docs/api/m2-bitacoras.md y convenciones, sección 7)."""

from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict


class AbrirBitacoraEntrada(BaseModel):
    # Campos desconocidos -> SOLICITUD_INVALIDA. La fecha se valida a mano (formato estricto).
    model_config = ConfigDict(extra="forbid")

    fecha_laboral: str


class PlanificarEntrada(BaseModel):
    """No admite ``estado``, ``propietaria_id`` ni avances (campos desconocidos). El título y los
    máximos se validan en el servicio para devolver CAMPO_OBLIGATORIO y TEXTO_DEMASIADO_LARGO."""

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = None
    descripcion: str | None = None


def momento(valor: datetime | None) -> str | None:
    """Momentos reales en ISO 8601 y UTC."""
    if valor is None:
        return None
    return valor.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def clase_de_jornada(fecha: date, fecha_actual: date) -> str:
    if fecha < fecha_actual:
        return "pasada"
    return "actual" if fecha == fecha_actual else "futura"


def bitacora_a_dict(fila, fecha_actual: date) -> dict:
    return {
        "id": str(fila.id),
        "persona_id": str(fila.persona_id),
        "fecha_laboral": fila.fecha_laboral.isoformat(),
        "clase_jornada": clase_de_jornada(fila.fecha_laboral, fecha_actual),
        "estado": fila.estado,
        "resumen": fila.resumen,
        "cerrada_en": momento(fila.cerrada_en),
        "creada_en": momento(fila.creada_en),
        "modificada_en": momento(fila.modificada_en),
    }


def actividad_a_dict(fila, fecha_laboral_origen: date) -> dict:
    marca = None
    if fila.registrada_por_error:
        marca = {"motivo": fila.motivo_error, "marcada_en": momento(fila.marcada_en)}
    return {
        "id": str(fila.id),
        "propietaria_id": str(fila.propietaria_id),
        "titulo": fila.titulo,
        "origen": fila.origen,
        "estado_actual": fila.estado_actual,
        "marca_error": marca,
        "fecha_laboral_origen": fecha_laboral_origen.isoformat(),
        "creada_en": momento(fila.creada_en),
    }


def planificacion_a_dict(fila, fecha_laboral: date) -> dict:
    # Todas son vigentes: la clase «conservada» (DM-08) solo aparece al finalizar una pertenencia.
    return {
        "id": str(fila.id),
        "actividad_id": str(fila.actividad_id),
        "fecha_laboral": fecha_laboral.isoformat(),
        "tipo": fila.tipo,
        "descripcion": fila.descripcion,
        "registrada_en": momento(fila.registrada_en),
        "clase": "vigente",
    }


def avance_a_dict(fila, fecha_laboral: date) -> dict:
    return {
        "id": str(fila.id),
        "actividad_id": str(fila.actividad_id),
        "fecha_laboral": fecha_laboral.isoformat(),
        "estado": fila.estado,
        "descripcion": fila.descripcion,
        "motivo_bloqueo": fila.motivo_bloqueo,
        "es_reactivacion": fila.es_reactivacion,
        "registrado_en": momento(fila.registrado_en),
    }
