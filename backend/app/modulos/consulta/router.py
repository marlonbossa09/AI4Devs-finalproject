"""Operaciones de M4 (consulta histórica y supervisión). Todas son de solo lectura (``GET``): no existe ninguna ruta de escritura sobre
registros de otras personas."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador, operador
from app.db import get_db
from app.modulos.consulta import servicio

router = APIRouter(tags=["M4 Consulta y supervisión"])

SIN_CACHE = {"Cache-Control": "no-store"}


@router.get("/personas/{persona_id}/bitacoras/{fecha_laboral}", summary="M4-01 Consultar la bitácora de un compañero")
def consultar_bitacora_de_persona(persona_id: str, fecha_laboral: str, op: Operador = Depends(operador), db: Session = Depends(get_db)):
    return JSONResponse(servicio.consultar_bitacora_de_persona(db, op, persona_id, fecha_laboral), headers=SIN_CACHE)
