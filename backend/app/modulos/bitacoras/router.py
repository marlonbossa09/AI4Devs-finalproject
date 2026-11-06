"""Operaciones de M2 sobre registros propios (``/mi/...``)."""

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador, operador, operador_que_modifica
from app.db import get_db
from app.modulos.bitacoras import servicio
from app.modulos.bitacoras.esquemas import AbrirBitacoraEntrada, PlanificarEntrada

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
    cabeceras = dict(SIN_CACHE)
    if resultado.reproducido:
        cabeceras["Idempotency-Replayed"] = "true"
    return JSONResponse(resultado.cuerpo, status_code=resultado.estado_http, headers=cabeceras)
