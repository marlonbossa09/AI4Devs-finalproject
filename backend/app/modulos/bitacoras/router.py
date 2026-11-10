"""Operaciones de M2 sobre registros propios (``/mi/...``)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador, operador, operador_que_modifica
from app.db import get_db
from app.modulos.bitacoras import servicio
from app.modulos.bitacoras.esquemas import (
    AbrirBitacoraEntrada, AvanceEntrada, ContinuacionEntrada, CorreccionEntrada, MarcaErrorEntrada,
    NoPlanificadaEntrada, PlanificarEntrada, ReactivacionEntrada, ReaperturaEntrada, ResumenEntrada,
)

router = APIRouter(prefix="/mi", tags=["M2 Bitácoras"])

SIN_CACHE = {"Cache-Control": "no-store"}


@router.get("/bitacoras/{fecha_laboral}", summary="M2-01a Consultar mi bitácora de una fecha laboral")
def consultar_bitacora(fecha_laboral: str, op: Operador = Depends(operador), db: Session = Depends(get_db)):
    return JSONResponse(servicio.consultar_bitacora(db, op, fecha_laboral), headers=SIN_CACHE)


@router.post("/bitacoras", summary="M2-01b Abrir mi bitácora de una fecha laboral")
def abrir_bitacora(
    cuerpo: AbrirBitacoraEntrada, op: Operador = Depends(operador_que_modifica), db: Session = Depends(get_db)
):
    estado, respuesta = servicio.abrir_bitacora(db, op, cuerpo.fecha_laboral)
    return JSONResponse(respuesta, status_code=estado, headers=SIN_CACHE)


@router.put("/bitacoras/{fecha_laboral}/resumen", summary="M2-02 Guardar el resumen libre de mi bitácora")
def guardar_resumen(
    fecha_laboral: str,
    cuerpo: ResumenEntrada,
    op: Operador = Depends(operador_que_modifica),
    db: Session = Depends(get_db),
):
    return JSONResponse(servicio.guardar_resumen(db, op, fecha_laboral, cuerpo), headers=SIN_CACHE)


@router.post("/bitacoras/{fecha_laboral}/cierre", summary="M3-01 Cerrar mi jornada")
def cerrar_bitacora(
    fecha_laboral: str,
    op: Operador = Depends(operador_que_modifica),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    return _respuesta_de_escritura(servicio.cerrar_bitacora(db, op, fecha_laboral, idempotency_key))


@router.post("/bitacoras/{fecha_laboral}/reapertura", summary="M3-02 Reabrir mi bitácora cerrada")
def reabrir_bitacora(
    fecha_laboral: str,
    cuerpo: ReaperturaEntrada,
    op: Operador = Depends(operador_que_modifica),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    return _respuesta_de_escritura(servicio.reabrir_bitacora(db, op, fecha_laboral, cuerpo, idempotency_key))


@router.post("/bitacoras/{fecha_laboral}/planificaciones", status_code=201,
             summary="M2-03 Planificar una actividad nueva")
def planificar_actividad(
    fecha_laboral: str,
    cuerpo: PlanificarEntrada,
    op: Operador = Depends(operador_que_modifica),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    resultado = servicio.planificar_actividad(db, op, fecha_laboral, cuerpo, idempotency_key)
    return _respuesta_de_escritura(resultado)


@router.post("/actividades/{actividad_id}/avances", status_code=201,
             summary="M2-05 Registrar un avance sobre una actividad propia")
def registrar_avance(
    actividad_id: UUID,
    cuerpo: AvanceEntrada,
    op: Operador = Depends(operador_que_modifica),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    resultado = servicio.registrar_avance(db, op, actividad_id, cuerpo, idempotency_key)
    return _respuesta_de_escritura(resultado)


@router.patch("/avances/{avance_id}", summary="M3-03 Corregir un avance ya registrado")
def corregir_avance(
    avance_id: UUID,
    cuerpo: CorreccionEntrada,
    op: Operador = Depends(operador_que_modifica),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    return _respuesta_de_escritura(servicio.corregir_avance(db, op, avance_id, cuerpo, idempotency_key))


@router.post("/actividades/{actividad_id}/reactivacion", status_code=201,
             summary="M3-04 Reactivar una actividad Completada")
def reactivar_actividad(
    actividad_id: UUID,
    cuerpo: ReactivacionEntrada,
    op: Operador = Depends(operador_que_modifica),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    return _respuesta_de_escritura(servicio.reactivar_actividad(db, op, actividad_id, cuerpo, idempotency_key))


@router.post("/actividades/{actividad_id}/marca-error", summary="M3-05 Marcar una actividad como registrada por error")
def marcar_actividad_por_error(
    actividad_id: UUID,
    cuerpo: MarcaErrorEntrada,
    op: Operador = Depends(operador_que_modifica),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    return _respuesta_de_escritura(servicio.marcar_actividad_por_error(db, op, actividad_id, cuerpo, idempotency_key))


@router.post("/actividades/{actividad_id}/marca-error/reversion", summary="M3-06 Revertir la marca de error")
def revertir_marca_de_error(
    actividad_id: UUID,
    op: Operador = Depends(operador_que_modifica),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    return _respuesta_de_escritura(servicio.revertir_marca_de_error(db, op, actividad_id, idempotency_key))


@router.post("/actividades/{actividad_id}/continuaciones-planificadas", status_code=201,
             summary="M2-04 Planificar la continuación de una actividad propia")
def planificar_continuacion(
    actividad_id: UUID,
    cuerpo: ContinuacionEntrada,
    op: Operador = Depends(operador_que_modifica),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    resultado = servicio.planificar_continuacion(db, op, actividad_id, cuerpo, idempotency_key)
    return _respuesta_de_escritura(resultado)


@router.post("/actividades-no-planificadas", status_code=201, summary="M2-06 Registrar una actividad no planificada")
def registrar_no_planificada(
    cuerpo: NoPlanificadaEntrada,
    op: Operador = Depends(operador_que_modifica),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    resultado = servicio.registrar_no_planificada(db, op, cuerpo, idempotency_key)
    return _respuesta_de_escritura(resultado)


@router.get("/actividades", summary="M2-08 Listar mis actividades")
def listar_actividades(
    request: Request,
    estado: list[str] | None = Query(default=None),
    limite: str | None = Query(default=None),
    continuar_desde: str | None = Query(default=None),
    op: Operador = Depends(operador),
    db: Session = Depends(get_db),
):
    cuerpo = servicio.listar_actividades(db, op, estado, limite, continuar_desde, set(request.query_params.keys()))
    return JSONResponse(cuerpo, headers=SIN_CACHE)


@router.get("/actividades/{actividad_id}", summary="M2-07 Consultar una actividad propia con sus avances")
def consultar_actividad(actividad_id: UUID, op: Operador = Depends(operador), db: Session = Depends(get_db)):
    return JSONResponse(servicio.consultar_actividad(db, op, actividad_id), headers=SIN_CACHE)


def _respuesta_de_escritura(resultado) -> JSONResponse:
    cabeceras = dict(SIN_CACHE)
    if resultado.reproducido:
        cabeceras["Idempotency-Replayed"] = "true"
    return JSONResponse(resultado.cuerpo, status_code=resultado.estado_http, headers=cabeceras)
