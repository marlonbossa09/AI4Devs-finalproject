"""Fábricas de datos de prueba (siempre ficticios) usando el rol propietario."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, text

from app.seguridad.contrasenas import calcular_hash
from app.seguridad.identificadores import normalizar_identificador

ZONA = "America/Bogota"


def hoy(zona: str = ZONA) -> date:
    return datetime.now(ZoneInfo(zona)).date()


def crear_organizacion(c: Connection, zona: str = ZONA):
    return c.execute(
        text("insert into organizacion (nombre, zona_horaria) values ('Org de prueba', :z) returning id"),
        {"z": zona},
    ).scalar_one()


def crear_equipo(c: Connection, organizacion, nombre: str = "Equipo de prueba"):
    return c.execute(
        text("insert into equipo (organizacion_id, nombre) values (:o, :n) returning id"),
        {"o": organizacion, "n": nombre},
    ).scalar_one()


def crear_persona(c: Connection, nombre: str = "Persona de prueba"):
    return c.execute(text("insert into persona (nombre) values (:n) returning id"), {"n": nombre}).scalar_one()


def crear_pertenencia(c: Connection, persona, equipo, rol: str = "colaborador",
                      desde: date | None = None, hasta: date | None = None):
    return c.execute(
        text("insert into pertenencia (persona_id, equipo_id, rol, desde, hasta_exclusivo) "
             "values (:p, :e, :r, :d, :h) returning id"),
        {"p": persona, "e": equipo, "r": rol, "d": desde or hoy() - timedelta(days=30), "h": hasta},
    ).scalar_one()


def crear_identidad(c: Connection, persona, identificador: str, contrasena: str | None):
    return c.execute(
        text("insert into identidad (persona_id, identificador_acceso, hash_contrasena) "
             "values (:p, :i, :h) returning id"),
        {"p": persona, "i": normalizar_identificador(identificador),
         "h": calcular_hash(contrasena) if contrasena else None},
    ).scalar_one()


@dataclass
class Escenario:
    organizacion: object
    equipo: object
    persona: object
    identificador: str
    contrasena: str


def escenario_basico(c: Connection, identificador: str = "ana.prueba",
                     contrasena: str = "contraseña-de-prueba-123", desde: date | None = None) -> Escenario:
    org = crear_organizacion(c)
    equipo = crear_equipo(c, org)
    persona = crear_persona(c, "Ana de prueba")
    crear_pertenencia(c, persona, equipo, "colaborador", desde=desde)
    crear_identidad(c, persona, identificador, contrasena)
    return Escenario(org, equipo, persona, normalizar_identificador(identificador), contrasena)
