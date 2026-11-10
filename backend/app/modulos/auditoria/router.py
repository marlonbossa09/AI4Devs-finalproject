"""Consulta de la auditoría (M3-07). Solo lectura: ninguna otra operación existe sobre ``/auditoria``."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador, operador
from app.db import get_db
from app.modulos.auditoria import servicio

router = APIRouter(prefix="/auditoria", tags=["M3 Auditoría"])


@router.get("", summary="M3-07 Consultar la auditoría de un registro")
def consultar_auditoria(request: Request, op: Operador = Depends(operador), db: Session = Depends(get_db)):
    parametros: dict[str, list[str]] = {}
    for nombre, valor in request.query_params.multi_items():
        parametros.setdefault(nombre, []).append(valor)
    return JSONResponse(servicio.consultar_auditoria(db, op, parametros), headers={"Cache-Control": "no-store"})
