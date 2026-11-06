"""Esquemas de M1-01a/b/c (docs/api/m1-acceso-usuarios-equipos.md)."""

from pydantic import BaseModel, ConfigDict, field_validator

from app.config import get_settings


class InicioSesionEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identificador_acceso: str
    contrasena: str

    @field_validator("identificador_acceso")
    @classmethod
    def _longitud_identificador(cls, valor: str) -> str:
        if len(valor) > get_settings().login_identifier_max_length:
            raise ValueError("demasiado_largo")
        return valor

    @field_validator("contrasena")
    @classmethod
    def _longitud_contrasena(cls, valor: str) -> str:
        if len(valor) > get_settings().login_password_max_length:
            raise ValueError("demasiado_larga")
        return valor


class PersonaSalida(BaseModel):
    id: str
    nombre: str


class SesionSalida(BaseModel):
    """M1-01a. La cookie de sesión viaja en la cabecera, nunca en el cuerpo."""

    persona: PersonaSalida
    rol_vigente: str
    csrf_token: str


class SesionActualSalida(SesionSalida):
    """M1-01c: además, la fecha actual del servidor en la zona de la organización."""

    fecha_actual: str
