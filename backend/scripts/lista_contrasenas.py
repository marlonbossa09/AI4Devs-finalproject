"""Instalación y verificación de Pwned Passwords en local (M1-T8.6): ``uv run python -m scripts.lista_contrasenas <orden>``.

El proyecto NO incluye el conjunto (unos 81 GB). Quien administra el servidor lo obtiene UNA vez con la herramienta oficial de Have I Been Pwned (ver
``docs/operacion/pwned-passwords.md``) y después:

    uv run python -m scripts.lista_contrasenas procedencia --dir <directorio> --herramienta "haveibeenpwned-downloader <versión>" --fecha-obtencion AAAA-MM-DD
    uv run python -m scripts.lista_contrasenas verificar --dir <directorio> [--muestra 200]

``procedencia`` escribe ``<directorio>/procedencia.json`` con la fuente y los términos fijos, el número REAL de rangos presentes y la huella del índice (si existe).
``verificar`` carga la instalación como lo hará la API (los 1.048.576 rangos presentes, procedencia y huella válidas) y comprueba el formato de una muestra aleatoria de rangos
(líneas ``<SUFIJO de 35 hex>:<cuenta>`` ordenadas por sufijo); nunca imprime contraseñas ni hashes. Después se indica ``COMPROMISED_PASSWORDS_DIR=<directorio>`` y se reinicia la API.
Para actualizar: volver a ejecutar la herramienta oficial en el mismo directorio (solo descarga lo que cambió), regenerar la procedencia, verificar y reiniciar.
"""

import argparse
import random
import re
import sys
from datetime import date

from app.seguridad import contrasenas_comprometidas as conjunto

LINEA = re.compile(r"[0-9A-F]{35}:\d+")


def verificar_muestra(directorio, cuantos: int) -> int:
    """Comprueba el formato de ``cuantos`` rangos al azar. Devuelve cuántas líneas leyó; lanza ``ListaNoValida`` si alguna no cumple."""
    leidas = 0
    for _ in range(cuantos):
        prefijo = "%05X" % random.randrange(conjunto.TOTAL_DE_RANGOS)
        try:
            lineas = [l for l in (directorio / f"{prefijo}.txt").read_bytes().decode("ascii").splitlines() if l]
        except (OSError, UnicodeDecodeError):
            raise conjunto.ListaNoValida("Un rango de la muestra no se puede leer o no es ASCII") from None
        if not lineas or not all(LINEA.fullmatch(l) for l in lineas) or [l[:35] for l in lineas] != sorted(l[:35] for l in lineas):
            raise conjunto.ListaNoValida("Un rango de la muestra no tiene el formato oficial (SUFIJO:CUENTA ordenado por sufijo)")
        leidas += len(lineas)
    return leidas


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lista_contrasenas", description="Pwned Passwords instalado en local (procedencia y verificación).")
    sub = p.add_subparsers(dest="orden", required=True)
    a = sub.add_parser("procedencia", help="escribe procedencia.json con el número real de rangos y la huella del índice")
    a.add_argument("--dir", required=True)
    a.add_argument("--herramienta", required=True, help='herramienta y versión con que se obtuvo, por ejemplo "haveibeenpwned-downloader 1.0"')
    a.add_argument("--fecha-obtencion", required=True, metavar="AAAA-MM-DD")
    v = sub.add_parser("verificar", help="carga la instalación como la API y comprueba el formato de una muestra de rangos")
    v.add_argument("--dir", required=True)
    v.add_argument("--muestra", type=int, default=200, help="cuántos rangos al azar se leen para comprobar el formato (0 = ninguno)")
    try:
        args = p.parse_args(argv)
    except SystemExit as fin:
        return 2 if fin.code else 0
    try:
        if args.orden == "procedencia":
            try:
                fecha = date.fromisoformat(args.fecha_obtencion)
            except ValueError:
                print("La fecha de obtención debe ser AAAA-MM-DD", file=sys.stderr)
                return 2
            destino = conjunto.generar_procedencia(args.dir, herramienta=args.herramienta, fecha_obtencion=fecha)
            print(f"Procedencia escrita en {destino}")
        else:
            instalacion = conjunto.cargar(args.dir)
            leidas = verificar_muestra(instalacion.directorio, max(args.muestra, 0))
            pr = instalacion.procedencia
            print(f"Instalación completa y válida: {pr.rangos} rangos SHA-1 | {pr.fuente} | obtenido el {pr.fecha_obtencion.isoformat()} con {pr.herramienta} | "
                  f"formato comprobado en {max(args.muestra, 0)} rangos al azar ({leidas} líneas).")
    except conjunto.ListaNoValida as e:
        print(f"Instalación no válida: {e}", file=sys.stderr)
        return 2
    except OSError:
        print("No se puede leer el directorio", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
