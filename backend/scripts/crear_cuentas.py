"""Crea cuentas locales de prueba (persona, identidad y pertenencia) de forma idempotente.

Uso (desde backend/), con el rol propietario del esquema, como la semilla de desarrollo:

    uv run python -m scripts.crear_cuentas --base smartwork_app --puerto 5432 --simular
    uv run python -m scripts.crear_cuentas --base smartwork_app --puerto 5432 \\
        --archivo-contrasena backend/.local/contrasena

Qué hace y qué no:
- Las cuentas (nombre, usuario y rol) se leen de un archivo LOCAL e ignorado por git
  (``backend/.local/cuentas.json`` por defecto). El script no contiene datos personales.
- La contraseña NUNCA va en ese archivo (se rechaza si aparece). Debe tener al menos
  ``PASSWORD_MIN_LENGTH`` caracteres (10 por defecto, ADR-002). Se lee de un archivo local
  (``--archivo-contrasena``), de la variable ``SMARTWORK_CUENTAS_PASSWORD`` o, en una terminal,
  se pide sin eco. Se guarda con Argon2id y no se imprime ni se registra.
- Antes de escribir, comprueba CON EL SERVIDOR que la conexión es exactamente la base y el
  puerto indicados, que el servidor es local y que el rol no es administrador.
- Idempotente: si el usuario ya existe no se modifica nada (tampoco su contraseña); si el
  nombre ya pertenece a otra identidad, se rechaza para no duplicar. No borra ni actualiza.
- Respeta el modelo: la persona entra en el equipo con el rol funcional indicado (colaborador o
  supervisor; no existe un rol de administrador), con pertenencia desde la fecha actual (IR-30),
  como máximo un supervisor por equipo (IR-03), y deja una entrada de auditoría de provisión sin
  credenciales ni identificadores de acceso (IR-34).
- ``--simular`` ejecuta todo dentro de una transacción y la deshace.
"""

import argparse
import getpass
import json
import os
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db import get_owner_engine
from app.seguridad.contrasenas import calcular_hash
from app.seguridad.identificadores import normalizar_identificador

ROLES = ("colaborador", "supervisor")
HOSTS_LOCALES = ("127.0.0.1", "localhost", "::1")
VARIABLE_CONTRASENA = "SMARTWORK_CUENTAS_PASSWORD"
ESPECIFICACION_POR_DEFECTO = Path(__file__).resolve().parent.parent / ".local" / "cuentas.json"
REFERENCIA_PROVISION = "scripts.crear_cuentas"
CLAVES_PROHIBIDAS = {"password", "contrasena", "contraseña", "clave", "secret", "secreto", "token"}


class CreacionRechazada(RuntimeError):
    """La operación no se realiza. El mensaje nunca incluye contraseñas ni datos de las cuentas."""


@dataclass(frozen=True)
class Resultado:
    nombre: str
    rol: str
    accion: str  # "creada" o "ya existía"


# --- Especificación y contraseña ----------------------------------------------------------------

def _claves(objeto):
    if isinstance(objeto, dict):
        for clave, valor in objeto.items():
            yield str(clave)
            yield from _claves(valor)
    elif isinstance(objeto, list):
        for elemento in objeto:
            yield from _claves(elemento)


def validar_especificacion(spec: dict) -> dict:
    if any(clave.lower() in CLAVES_PROHIBIDAS for clave in _claves(spec)):
        raise CreacionRechazada("La especificación no puede contener contraseñas ni secretos")
    for campo in ("organizacion", "equipo"):
        if not str(spec.get(campo) or "").strip():
            raise CreacionRechazada(f"Falta «{campo}» en la especificación")
    cuentas = spec.get("cuentas")
    if not isinstance(cuentas, list) or not cuentas:
        raise CreacionRechazada("La especificación no tiene cuentas")
    vistos: set[str] = set()
    for cuenta in cuentas:
        if not str(cuenta.get("nombre") or "").strip() or not str(cuenta.get("usuario") or "").strip():
            raise CreacionRechazada("Cada cuenta necesita nombre y usuario")
        if cuenta.get("rol") not in ROLES:
            raise CreacionRechazada(f"El rol debe ser uno de {ROLES}: no existe un rol de administrador")
        identificador = normalizar_identificador(cuenta["usuario"])
        if identificador in vistos:
            raise CreacionRechazada("Hay usuarios repetidos en la especificación")
        vistos.add(identificador)
    if sum(1 for c in cuentas if c["rol"] == "supervisor") > 1:
        raise CreacionRechazada("Un equipo tiene como máximo un supervisor (IR-03)")
    return spec


def cargar_especificacion(ruta: Path) -> dict:
    try:
        spec = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CreacionRechazada(f"No existe el archivo de especificación: {ruta}") from error
    except json.JSONDecodeError as error:
        raise CreacionRechazada("La especificación no es un JSON válido") from error
    return validar_especificacion(spec)


def leer_contrasena(archivo: Path | None = None, entorno=os.environ, pedir=getpass.getpass,
                    interactivo: bool | None = None) -> str:
    """Contraseña inicial por un canal local: archivo, variable de entorno o petición sin eco.

    Exige la longitud mínima de la política (``PASSWORD_MIN_LENGTH``, ADR-002) y no supera el
    máximo de entrada del inicio de sesión.
    """
    if archivo is not None:
        try:
            valor = Path(archivo).read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise CreacionRechazada("No existe el archivo de la contraseña") from error
        valor = valor.rstrip("\r\n")
    elif entorno.get(VARIABLE_CONTRASENA):
        valor = entorno[VARIABLE_CONTRASENA]
    elif interactivo if interactivo is not None else sys.stdin.isatty():
        valor = pedir("Contraseña inicial de las cuentas (no se muestra): ")
    else:
        raise CreacionRechazada(
            f"Falta la contraseña: use --archivo-contrasena, la variable {VARIABLE_CONTRASENA} "
            "o una terminal interactiva"
        )
    settings = get_settings()
    maximo, minimo = settings.login_password_max_length, settings.password_min_length
    if len(valor) < minimo:
        raise CreacionRechazada(f"La contraseña debe tener al menos {minimo} caracteres (ADR-002)")
    if len(valor) > maximo:
        raise CreacionRechazada(f"La contraseña supera el máximo de {maximo} caracteres")
    return valor


# --- Destino ------------------------------------------------------------------------------------

def comprobar_destino(conexion: Connection, *, base: str, puerto: int) -> None:
    """Confirma con la configuración Y con el propio servidor a qué base y puerto se escribe."""
    url = make_url(get_settings().migrations_database_url)
    if (url.host or "") not in HOSTS_LOCALES:
        raise CreacionRechazada("Solo se puede operar contra un servidor local")
    if url.database != base or url.port != puerto:
        raise CreacionRechazada("La configuración no apunta exactamente a la base y el puerto indicados")
    real_base, real_puerto, superusuario = conexion.execute(
        text("select current_database(), inet_server_port(), "
             "(select rolsuper from pg_roles where rolname = current_user)")
    ).one()
    if real_base != base or real_puerto != puerto:
        raise CreacionRechazada("El servidor confirma una base o un puerto distintos de los indicados")
    if superusuario:
        raise CreacionRechazada("El rol de conexión no debe ser administrador")


# --- Creación -----------------------------------------------------------------------------------

def _aplicar(conexion: Connection, spec: dict, contrasena: str) -> list[Resultado]:
    organizacion = conexion.execute(
        text("select id, zona_horaria from organizacion where nombre = :n"), {"n": spec["organizacion"]}
    ).one_or_none()
    if organizacion is None:
        zona = str(spec.get("zona_horaria") or "").strip()
        if not zona:
            raise CreacionRechazada("La organización no existe y la especificación no indica «zona_horaria»")
        ZoneInfo(zona)  # falla si no es una zona válida
        organizacion = conexion.execute(
            text("insert into organizacion (nombre, zona_horaria) values (:n, :z) returning id, zona_horaria"),
            {"n": spec["organizacion"], "z": zona},
        ).one()
    equipo = conexion.execute(
        text("select id from equipo where organizacion_id = :o and nombre = :n"),
        {"o": organizacion.id, "n": spec["equipo"]},
    ).scalar_one_or_none()
    if equipo is None:
        equipo = conexion.execute(
            text("insert into equipo (organizacion_id, nombre) values (:o, :n) returning id"),
            {"o": organizacion.id, "n": spec["equipo"]},
        ).scalar_one()
    hoy = datetime.now(ZoneInfo(organizacion.zona_horaria)).date()

    # IR-32: un equipo con colaboradores siempre tiene supervisor
    hay_supervisor_en_spec = any(c["rol"] == "supervisor" for c in spec["cuentas"])
    if not hay_supervisor_en_spec and any(c["rol"] == "colaborador" for c in spec["cuentas"]):
        existente = conexion.execute(
            text("select 1 from pertenencia where equipo_id = :e and rol = 'supervisor' "
                 "and daterange(desde, hasta_exclusivo, '[)') @> :h limit 1"),
            {"e": equipo, "h": hoy},
        ).first()
        if existente is None:
            raise CreacionRechazada("El equipo tendría colaboradores sin supervisor (IR-32)")

    resultados: list[Resultado] = []
    for cuenta in spec["cuentas"]:
        nombre, rol = cuenta["nombre"].strip(), cuenta["rol"]
        identificador = normalizar_identificador(cuenta["usuario"])
        existente = conexion.execute(
            text("select 1 from identidad where identificador_acceso = :i"), {"i": identificador}
        ).first()
        if existente is not None:
            resultados.append(Resultado(nombre, rol, "ya existía"))
            continue

        mismas = conexion.execute(
            text("select p.id, exists (select 1 from identidad i where i.persona_id = p.id) as con_identidad, "
                 "exists (select 1 from pertenencia x where x.persona_id = p.id) as con_pertenencia "
                 "from persona p where lower(btrim(p.nombre)) = lower(btrim(:n))"),
            {"n": nombre},
        ).all()
        if any(m.con_identidad for m in mismas):
            raise CreacionRechazada(f"Ya existe una persona llamada «{nombre}» con otra identidad: no se duplica")
        if any(m.con_pertenencia for m in mismas):
            raise CreacionRechazada(f"La persona «{nombre}» ya tiene pertenencias: requiere revisión manual")
        if mismas:
            persona = mismas[0].id
        else:
            persona = conexion.execute(
                text("insert into persona (nombre) values (:n) returning id"), {"n": nombre}
            ).scalar_one()

        conexion.execute(
            text("insert into identidad (persona_id, identificador_acceso, hash_contrasena) values (:p, :i, :h)"),
            {"p": persona, "i": identificador, "h": calcular_hash(contrasena)},
        )
        conexion.execute(
            text("insert into pertenencia (persona_id, equipo_id, rol, desde) values (:p, :e, :r, :d)"),
            {"p": persona, "e": equipo, "r": rol, "d": hoy},
        )
        # IR-34: alta por provisión; sin credenciales ni identificadores de acceso
        conexion.execute(
            text("insert into auditoria (tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id, "
                 "propietaria_registro_id, valor_nuevo) "
                 "values ('provision', :ref, 'alta', 'persona', :p, :p, cast(:nuevo as jsonb))"),
            {"ref": REFERENCIA_PROVISION, "p": persona,
             "nuevo": json.dumps({"persona": str(persona), "equipo": str(equipo), "rol": rol, "desde": hoy.isoformat()})},
        )
        resultados.append(Resultado(nombre, rol, "creada"))
    return resultados


def crear_cuentas(engine: Engine, spec: dict, contrasena: str, *, base: str, puerto: int,
                  simular: bool = False) -> list[Resultado]:
    validar_especificacion(spec)
    with engine.connect() as conexion:
        transaccion = conexion.begin()
        try:
            comprobar_destino(conexion, base=base, puerto=puerto)
            resultados = _aplicar(conexion, spec, contrasena)
        except IntegrityError as error:
            transaccion.rollback()
            # Sin el texto original: podría incluir valores de las cuentas
            motivo = {"23P01": "conflicto de pertenencias (por ejemplo, dos supervisores en el mismo equipo)",
                      "23505": "valor duplicado"}.get(getattr(error.orig, "sqlstate", ""), "restricción de integridad")
            raise CreacionRechazada(f"La base de datos rechazó la operación: {motivo}") from None
        except BaseException:
            transaccion.rollback()
            raise
        if simular:
            transaccion.rollback()
        else:
            transaccion.commit()
    return resultados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crea cuentas locales de prueba de forma idempotente.")
    parser.add_argument("--base", required=True, help="nombre exacto de la base de datos de destino")
    parser.add_argument("--puerto", required=True, type=int, help="puerto exacto del servidor de destino")
    parser.add_argument("--cuentas", type=Path, default=ESPECIFICACION_POR_DEFECTO)
    parser.add_argument("--archivo-contrasena", type=Path, default=None)
    parser.add_argument("--simular", action="store_true", help="valida todo y deshace la transacción")
    args = parser.parse_args(argv)
    try:
        spec = cargar_especificacion(args.cuentas)
        # Al simular no hace falta la contraseña real: el hash de una aleatoria desechable basta
        contrasena = secrets.token_urlsafe(24) if args.simular else leer_contrasena(args.archivo_contrasena)
        resultados = crear_cuentas(get_owner_engine(), spec, contrasena, base=args.base,
                                   puerto=args.puerto, simular=args.simular)
    except CreacionRechazada as error:
        print(f"Operación rechazada: {error}", file=sys.stderr)
        return 1
    print(f"Destino confirmado por el servidor: base {args.base}, puerto {args.puerto}"
          + (" (simulación: se deshizo)" if args.simular else ""))
    for r in resultados:
        print(f"  {r.accion:<10} {r.nombre} ({r.rol})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
