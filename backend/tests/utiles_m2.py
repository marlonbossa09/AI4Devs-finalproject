"""Utilidades compartidas por las pruebas HTTP de M2 (siempre con datos ficticios)."""

import uuid
from datetime import timedelta

from sqlalchemy import text

from app.db import get_owner_engine
from tests.fabricas import hoy
from tests.utiles_http import API, cabeceras


def iso(dias: int) -> str:
    """Fecha laboral relativa a hoy (en la zona de la organización de pruebas)."""
    return (hoy() + timedelta(days=dias)).isoformat()


def contar(tabla: str) -> int:
    with get_owner_engine().connect() as c:
        return c.execute(text(f"select count(*) from {tabla}")).scalar_one()


def filas(consulta: str, **parametros):
    with get_owner_engine().connect() as c:
        return c.execute(text(consulta), parametros).all()


def con_clave(csrf: str, clave: str | None = "__auto__") -> dict[str, str]:
    encabezados = cabeceras(csrf)
    if clave == "__auto__":
        clave = str(uuid.uuid4())
    if clave is not None:
        encabezados["Idempotency-Key"] = clave
    return encabezados


def planificar_actividad(cliente, csrf, fecha: str, titulo: str = "Preparar informe"):
    """M2-03. Devuelve el identificador de la actividad creada."""
    r = cliente.post(f"{API}/mi/bitacoras/{fecha}/planificaciones",
                     json={"titulo": titulo, "descripcion": "Revisar cifras"}, headers=con_clave(csrf))
    assert r.status_code == 201, r.text
    return r.json()["actividad"]["id"]


def avanzar(cliente, csrf, actividad_id, fecha: str, estado: str | None = "En progreso",
            descripcion: str | None = "Avancé con el informe", motivo_bloqueo: str | None = None,
            clave: str | None = "__auto__", **extra):
    """M2-05. Solo envía los campos que no son None (para probar campos ausentes)."""
    cuerpo = {"fecha_laboral": fecha, "estado": estado, "descripcion": descripcion,
              "motivo_bloqueo": motivo_bloqueo, **extra}
    cuerpo = {k: v for k, v in cuerpo.items() if v is not None}
    return cliente.post(f"{API}/mi/actividades/{actividad_id}/avances", json=cuerpo, headers=con_clave(csrf, clave))


def estado_actual_de(actividad_id) -> str:
    return filas("select estado_actual from actividad where id = :a", a=actividad_id)[0].estado_actual
