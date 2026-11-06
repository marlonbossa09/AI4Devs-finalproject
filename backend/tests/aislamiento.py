"""Aislamiento de las pruebas: solo pueden tocar la base ``smartwork_test``.

Las pruebas son destructivas (vacían tablas y revierten migraciones), y el servicio PostgreSQL
local es compartido con otras bases. Esta validación se aplica en tres momentos:

1. ANTES de importar la aplicación: la URL debe apuntar exactamente a ``smartwork_test`` en un
   servidor local, y no puede ser la de desarrollo.
2. AL ABRIR LA SESIÓN de pruebas: el servidor confirma a qué base y con qué rol se conectó cada
   conexión (``current_database()``, ``current_user``), y que ninguno es superusuario.
3. ANTES DE CADA LIMPIEZA: se vuelve a comprobar ``current_database()`` en la misma conexión que
   vacía las tablas.

Cualquier fallo aborta toda la sesión con un mensaje claro, sin ejecutar nada.
"""

from sqlalchemy import Connection, text
from sqlalchemy.engine import URL, make_url

BASE_DE_PRUEBAS = "smartwork_test"
HOSTS_LOCALES = frozenset({"127.0.0.1", "localhost", "::1"})
# Clúster alternativo de desarrollo, descartado: las pruebas no deben usarlo.
PUERTOS_NO_PERMITIDOS = frozenset({5433})


class ErrorDeAislamiento(RuntimeError):
    """La configuración de pruebas no garantiza que solo se toque smartwork_test."""


def validar_url_de_pruebas(url: str) -> URL:
    """Valida una URL de pruebas y la devuelve ya analizada."""
    try:
        u = make_url(url)
    except Exception as error:  # URL ilegible
        raise ErrorDeAislamiento("La URL de pruebas no se puede interpretar") from error
    if not (u.drivername or "").startswith("postgresql"):
        raise ErrorDeAislamiento("La URL de pruebas debe ser de PostgreSQL")
    if (u.host or "") not in HOSTS_LOCALES:
        raise ErrorDeAislamiento("Las pruebas solo pueden usar un servidor local")
    if u.port in PUERTOS_NO_PERMITIDOS:
        raise ErrorDeAislamiento(f"Las pruebas no pueden usar el puerto {u.port}")
    if u.database != BASE_DE_PRUEBAS:
        raise ErrorDeAislamiento(
            f"Las pruebas solo pueden usar la base {BASE_DE_PRUEBAS!r} (recibida: {u.database!r})"
        )
    return u


def validar_distinta_de_desarrollo(url_de_pruebas: str, urls_de_desarrollo: list[str | None]) -> None:
    """La base de pruebas no puede ser la misma que usa la aplicación en desarrollo."""
    prueba = make_url(url_de_pruebas)
    for otra in urls_de_desarrollo:
        if not otra:
            continue
        u = make_url(otra)
        if (u.host, u.port, u.database) == (prueba.host, prueba.port, prueba.database):
            raise ErrorDeAislamiento("La base de pruebas coincide con la de desarrollo")


def validar_conexion(conexion: Connection, *, puerto_esperado: int | None) -> dict[str, object]:
    """Pregunta al propio servidor a qué se conectó. Devuelve la evidencia (sin secretos)."""
    base, usuario, puerto, superusuario, crea_bases = conexion.execute(
        text(
            "select current_database(), current_user, inet_server_port(), "
            "(select rolsuper from pg_roles where rolname = current_user), "
            "(select rolcreatedb from pg_roles where rolname = current_user)"
        )
    ).one()
    if base != BASE_DE_PRUEBAS:
        raise ErrorDeAislamiento(f"El servidor confirma la base {base!r}, no {BASE_DE_PRUEBAS!r}")
    if superusuario or crea_bases:
        raise ErrorDeAislamiento(f"El rol {usuario!r} tiene privilegios de administración")
    if puerto_esperado is not None and puerto != puerto_esperado:
        raise ErrorDeAislamiento(f"El servidor responde en el puerto {puerto}, no en {puerto_esperado}")
    return {"base": base, "usuario": usuario, "puerto": puerto}


def exigir_base_de_pruebas(conexion: Connection) -> None:
    """Comprobación barata, justo antes de una operación destructiva en esta conexión."""
    base = conexion.execute(text("select current_database()")).scalar_one()
    if base != BASE_DE_PRUEBAS:
        raise ErrorDeAislamiento(f"Operación destructiva rechazada: la conexión está en {base!r}")
