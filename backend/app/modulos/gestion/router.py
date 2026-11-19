"""Gestión de su equipo por el supervisor (ver ``servicio``): crear un colaborador, emitir su código de primer acceso y finalizar su pertenencia."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador, operador_que_modifica
from app.db import get_db
from app.modulos.gestion import servicio

router = APIRouter(prefix="/equipo", tags=["M1 Gestión del equipo"])

SIN_CACHE = {"Cache-Control": "no-store"}


class NuevoColaborador(BaseModel):
    """Sin rol, equipo ni fecha: siempre un colaborador del equipo de quien llama, desde hoy. Los campos desconocidos se rechazan."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = None
    identificador_acceso: str | None = None


@router.post("/integrantes", status_code=201, summary="M1-11 Crear un colaborador en mi equipo")
def crear_colaborador(cuerpo: NuevoColaborador, op: Operador = Depends(operador_que_modifica), db: Session = Depends(get_db)):
    return JSONResponse(servicio.crear_colaborador(db, op, cuerpo.nombre, cuerpo.identificador_acceso), status_code=201, headers=SIN_CACHE)


@router.post("/integrantes/{persona_id}/codigo-primer-acceso", status_code=201, summary="M1-12 Emitir el código de primer acceso de un colaborador de mi equipo")
def emitir_codigo(persona_id: UUID, op: Operador = Depends(operador_que_modifica), db: Session = Depends(get_db)):
    return JSONResponse(servicio.emitir_codigo_de_primer_acceso(db, op, persona_id), status_code=201, headers=SIN_CACHE)


@router.post("/integrantes/{persona_id}/finalizacion", summary="M1-13 Finalizar la pertenencia de un colaborador de mi equipo")
def finalizar(persona_id: UUID, op: Operador = Depends(operador_que_modifica), db: Session = Depends(get_db)):
    return JSONResponse(servicio.finalizar_pertenencia(db, op, persona_id), headers=SIN_CACHE)
