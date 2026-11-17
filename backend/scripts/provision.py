"""Provisión administrativa oficial (M1-T2): ``uv run python -m scripts.provision <orden> ...``.

Es la forma oficial de crear equipos y personas (A2: CLI del servidor). ``seed_dev.py`` y ``crear_cuentas.py`` siguen
siendo HERRAMIENTAS DE DESARROLLO y de demostración: usan el rol propietario, asignan contraseñas directamente y no
identifican a una persona operadora. No sustituyen a esta provisión.
"""

import sys

from app.provision.cli import main

if __name__ == "__main__":
    sys.exit(main())
