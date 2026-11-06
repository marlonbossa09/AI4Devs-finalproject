"""Operaciones de M2 sobre registros propios (``/mi/...``)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador, operador, operador_que_modifica
from app.db import get_db
from app.modulos.bitacoras import servicio
from app.modulos.bitacoras.esquemas import (
    AbrirBitacoraEntrada, AvanceEntrada, NoPlanificadaEntrada, PlanificarEntrada,
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
