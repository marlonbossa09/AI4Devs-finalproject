"""Operaciones de M4 (consulta histórica y supervisión). Todas son de solo lectura (``GET``): no existe ninguna ruta de escritura sobre
registros de otras personas."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador, operador
from app.db import get_db
from app.modulos.consulta import historial, servicio, supervision

router = APIRouter(tags=["M4 Consulta y supervisión"])

SIN_CACHE = {"Cache-Control": "no-store"}


@router.get("/personas/{persona_id}/bitacoras/{fecha_laboral}", summary="M4-01 Consultar la bitácora de un compañero")
def consultar_bitacora_de_persona(persona_id: str, fecha_laboral: str, op: Operador = Depends(operador), db: Session = Depends(get_db)):
    return JSONResponse(servicio.consultar_bitacora_de_persona(db, op, persona_id, fecha_laboral), headers=SIN_CACHE)


@router.get("/historico", summary="M4-02 Consultar el histórico por colaborador y fechas")
def consultar_historico(request: Request, op: Operador = Depends(operador), db: Session = Depends(get_db)):
    return JSONResponse(servicio.consultar_historico(db, op, list(request.query_params.multi_items())), headers=SIN_CACHE)


@router.get("/equipo/supervision", summary="M4-03 Obtener la vista de supervisión del equipo en un período")
def consultar_supervision(request: Request, op: Operador = Depends(operador), db: Session = Depends(get_db)):
    return JSONResponse(supervision.consultar_supervision(db, op, list(request.query_params.multi_items())), headers=SIN_CACHE)


@router.get("/equipo/actividades/{actividad_id}", summary="M4-04 Consultar el historial de una actividad de mi equipo")
def consultar_historial_de_actividad(actividad_id: str, op: Operador = Depends(operador), db: Session = Depends(get_db)):
    return JSONResponse(historial.consultar_historial_de_actividad(db, op, actividad_id), headers=SIN_CACHE)
