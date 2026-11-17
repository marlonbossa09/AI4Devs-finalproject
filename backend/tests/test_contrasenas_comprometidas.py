"""M1-T8.6 — contraseñas comprometidas con Pwned Passwords instalado en LOCAL (formato oficial por rangos SHA-1) y su efecto en el primer acceso y la recuperación.

El conjunto real (unos 81 GB) no está en el repositorio ni se usa en las pruebas: se construyen instalaciones SINTÉTICAS COMPLETAS de 16 rangos (con ``TOTAL_DE_RANGOS`` reducido) en
el formato oficial: un archivo ``<PREFIJO>.txt`` por rango con líneas ``<SUFIJO de 35 hex>:<cuenta>`` ordenadas y terminadas en CRLF. Pruebas esenciales (metodología ligera): el
formato oficial; verificación de la instalación (completa, procedencia, huella); contraseña comprometida rechazada y no incluida aceptada; mismo control en primer acceso y en
recuperación, sin consumir el código ni dar un oráculo; contraseña y código fuera de los registros; y que no hay ninguna comunicación externa en la comprobación.
"""

import ast
import hashlib
import json
import logging
from datetime import date
from functools import cache
from pathlib import Path

import pytest

from app.config import get_settings
from app.main import crear_app
from app.seguridad import contrasenas_comprometidas as conjunto
from scripts import lista_contrasenas
from tests.test_canje_primer_acceso import canjear as canjear_primer_acceso
from tests.test_canje_primer_acceso import cliente, estado as estado_primer_acceso, huella, mundo as mundo_primer_acceso, password_establecida  # noqa: F401
from tests.test_canje_recuperacion import canjear as canjear_recuperacion
from tests.test_canje_recuperacion import estado as estado_recuperacion, mundo as mundo_recuperacion, sesiones_de, vigentes  # noqa: F401
from tests.utiles_http import API
from tests.utiles_m2 import filas

BUENA = "una-contraseña-segura-1"
RANGOS = 16                                  # la instalación sintética completa: prefijos 00000 a 0000F


def sha1(contrasena: str) -> str:
    return hashlib.sha1(contrasena.encode("utf-8")).hexdigest().upper()


@cache
def candidatas() -> tuple[str, str, str]:
    """Tres contraseñas sintéticas (≥ 10 caracteres) cuyo SHA-1 cae en un rango de la instalación sintética (0000x)."""
    encontradas, i = [], 0
    while len(encontradas) < 3:
        c = f"sintetica-de-prueba-{i}"
        i += 1
        if sha1(c).startswith("0000"):
            encontradas.append(c)
    return tuple(encontradas)


COMPROMETIDA, RELLENO, AUSENTE = candidatas()          # en el conjunto; en el conjunto con cuenta 0 (relleno); no está


# Nota: una instalación real completa tiene los 1.048.576 rangos; la sintética solo los 16 primeros, así que en los flujos con la instalación activa las contraseñas
# «válidas» deben ser las que caen en uno de esos rangos (AUSENTE). Una contraseña cuyo rango falte falla cerrado (500), que es lo que se quiere ante una instalación dañada.


def instalar(carpeta: Path, *, rangos: int = RANGOS, indice: bool = True, herramienta: str = "herramienta-de-prueba 1.0") -> Path:
    """Instalación sintética en el formato oficial. ``COMPROMETIDA`` figura con cuenta 3, ``RELLENO`` con cuenta 0 y ``AUSENTE`` no figura (su rango sí existe)."""
    for i in range(rangos):
        prefijo = "%05X" % i
        entradas = {f"{j:035X}": 1 + j for j in range(1, 6)}                                       # sufijos de relleno que no coinciden con ninguna candidata
        for contrasena, cuenta in ((COMPROMETIDA, 3), (RELLENO, 0)):
            if sha1(contrasena)[:5] == prefijo:
                entradas[sha1(contrasena)[5:]] = cuenta
        (carpeta / f"{prefijo}.txt").write_bytes("".join(f"{s}:{c}\r\n" for s, c in sorted(entradas.items())).encode("ascii"))
    if indice:
        (carpeta / "sha1.index").write_text("".join(f"{'%05X' % i}\t\"etag-{i}\"\n" for i in range(rangos)), encoding="utf-8")
    conjunto.generar_procedencia(carpeta, herramienta=herramienta, fecha_obtencion=date(2026, 11, 17))
    return carpeta


@pytest.fixture(autouse=True)
def pocos_rangos_y_sin_conjunto_por_defecto(monkeypatch):
    monkeypatch.setattr(conjunto, "TOTAL_DE_RANGOS", RANGOS)                 # la instalación «completa» de las pruebas tiene 16 rangos
    monkeypatch.setattr(get_settings(), "compromised_passwords_dir", None)
    conjunto.reiniciar()
    yield
    conjunto.reiniciar()


@pytest.fixture()
def instalado(tmp_path, monkeypatch):
    carpeta = instalar(tmp_path)
    monkeypatch.setattr(get_settings(), "compromised_passwords_dir", str(carpeta))
    conjunto.reiniciar()
    return carpeta


def rango_de(contrasena: str) -> str:
    return "%05X.txt" % int(sha1(contrasena)[:5], 16)


# ===================================================== formato oficial ======================================================

def test_el_formato_oficial_sufijo_cuenta_en_crlf_se_interpreta_y_la_cuenta_cero_no_cuenta():
    s1, s2, s3 = "0" * 34 + "1", "A" * 35, "F" * 35
    datos = f"{s1}:1\r\n{s2}:42\r\n{s3}:0\r\n".encode()
    assert conjunto._contiene_sufijo(datos, s1)                                  # la primera línea
    assert conjunto._contiene_sufijo(datos, s2)                                  # una intermedia
    assert not conjunto._contiene_sufijo(datos, s3)                              # relleno de cuenta 0: no es una contraseña comprometida
    assert not conjunto._contiene_sufijo(datos, "B" * 35)                        # ausente
    assert conjunto._contiene_sufijo(f"{s1}:7".encode(), s1)                     # última línea sin terminador
    assert conjunto._contiene_sufijo(f"{s1}:1\n{s2}:2\n".encode(), s2)           # también con LF
    assert not conjunto._contiene_sufijo(f"{s1}:\r\n".encode(), s1)              # sin cuenta no es una línea válida
    assert not conjunto._contiene_sufijo(b"", s1)


def test_el_sha1_se_calcula_sobre_el_utf8_tal_como_llega_y_una_cadena_no_utf8_no_esta(instalado):
    assert conjunto.es_comprometida(COMPROMETIDA) is True
    assert conjunto.es_comprometida("\ud800-surrogado-suelto-1") is False        # JSON puede traer un sustituto suelto: no es UTF-8 y no puede estar en el conjunto


# ===================================================== verificación de la instalación =======================================

def test_una_instalacion_completa_con_procedencia_valida_se_carga(tmp_path):
    inst = conjunto.cargar(instalar(tmp_path))
    p = inst.procedencia
    assert p.rangos == RANGOS and p.formato == "sha1-por-rangos" and p.fecha_obtencion == date(2026, 11, 17) and p.herramienta == "herramienta-de-prueba 1.0"
    assert "Pwned Passwords" in p.fuente and p.url == "https://haveibeenpwned.com/Passwords" and p.terminos_url == "https://haveibeenpwned.com/termsofuse"
    assert "cualquier fin lícito" in p.terminos and p.sha256_del_indice is not None
    assert inst.contiene(COMPROMETIDA) and not inst.contiene(AUSENTE) and not inst.contiene(RELLENO)


def test_un_subconjunto_no_se_acepta_ni_regenerando_la_procedencia(tmp_path):
    carpeta = instalar(tmp_path)
    (carpeta / "00007.txt").unlink()                                                     # falta un rango
    with pytest.raises(conjunto.ListaNoValida, match="incompleta: 15 de 16"):
        conjunto.cargar(carpeta)
    conjunto.generar_procedencia(carpeta, herramienta="x", fecha_obtencion=date(2026, 11, 17))     # regenerar solo declara 15 rangos: sigue sin ser completa
    assert conjunto.leer_procedencia(carpeta).rangos == 15
    with pytest.raises(conjunto.ListaNoValida, match="se exige la instalación completa"):
        conjunto.cargar(carpeta)


@pytest.mark.parametrize("cambio", [
    {"fuente": None}, {"url": None}, {"terminos_url": None}, {"terminos": None}, {"herramienta": None}, {"fecha_obtencion": None}, {"formato": None}, {"rangos": None},
    {"fuente": " "}, {"herramienta": ""}, {"fecha_obtencion": "17/11/2026"}, {"formato": "ntlm-por-rangos"}, {"rangos": "16"}, {"rangos": True}, {"sha256_del_indice": "ABC"},
])
def test_una_procedencia_incompleta_o_mal_formada_no_se_acepta(tmp_path, cambio):
    carpeta = instalar(tmp_path)
    datos = json.loads((carpeta / "procedencia.json").read_text(encoding="utf-8"))
    for campo, valor in cambio.items():
        datos.pop(campo) if valor is None else datos.__setitem__(campo, valor)
    (carpeta / "procedencia.json").write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(conjunto.ListaNoValida):
        conjunto.cargar(carpeta)


def test_con_rangos_declarados_distintos_un_indice_alterado_o_sin_procedencia_no_se_carga(tmp_path):
    carpeta = instalar(tmp_path)
    datos = json.loads((carpeta / "procedencia.json").read_text(encoding="utf-8"))
    (carpeta / "procedencia.json").write_text(json.dumps({**datos, "rangos": 15}), encoding="utf-8")                      # declara menos de los que hay
    with pytest.raises(conjunto.ListaNoValida, match="incompleta"):
        conjunto.cargar(carpeta)
    (carpeta / "procedencia.json").write_text(json.dumps(datos), encoding="utf-8")
    (carpeta / "sha1.index").write_text("alterado\n", encoding="utf-8")                                                   # el índice cambió sin regenerar la procedencia
    with pytest.raises(conjunto.ListaNoValida, match="huella del índice"):
        conjunto.cargar(carpeta)
    (carpeta / "sha1.index").unlink()                                                                                      # y si falta, tampoco coincide
    with pytest.raises(conjunto.ListaNoValida, match="huella del índice"):
        conjunto.cargar(carpeta)
    (carpeta / "procedencia.json").unlink()
    with pytest.raises(conjunto.ListaNoValida, match="procedencia"):
        conjunto.cargar(carpeta)
    with pytest.raises(conjunto.ListaNoValida, match="no existe"):
        conjunto.cargar(tmp_path / "no-existe")


def test_los_archivos_ajenos_no_cuentan_como_rangos_y_el_indice_es_opcional(tmp_path):
    carpeta = instalar(tmp_path, indice=False)
    (carpeta / ".00003.0123456789abcdef.tmp").write_bytes(b"temporal de la herramienta")
    (carpeta / "LEEME.txt").write_text("no es un rango", encoding="utf-8")
    (carpeta / "0000g.txt").write_text("no es hexadecimal", encoding="utf-8")
    assert conjunto.cargar(carpeta).procedencia.sha256_del_indice is None and len(conjunto.rangos_instalados(carpeta)) == RANGOS


def test_un_rango_que_desaparece_despues_de_arrancar_falla_cerrado_y_sin_datos_en_el_mensaje(instalado):
    conjunto.comprobar_configuracion()
    (instalado / rango_de(COMPROMETIDA)).unlink()
    with pytest.raises(conjunto.ListaNoValida, match="Falta o no se puede leer un rango") as error:
        conjunto.es_comprometida(COMPROMETIDA)
    assert COMPROMETIDA not in str(error.value) and sha1(COMPROMETIDA) not in str(error.value) and sha1(COMPROMETIDA)[5:] not in str(error.value)


def test_la_herramienta_escribe_la_procedencia_y_verifica_la_instalacion_y_una_muestra_del_formato(tmp_path, capsys):
    carpeta = tmp_path
    for i in range(RANGOS):                                                          # solo los archivos de rango: aún sin procedencia ni índice
        (carpeta / ("%05X.txt" % i)).write_bytes(f"{'0' * 34}1:5\r\n{'A' * 35}:2\r\n".encode())
    assert lista_contrasenas.main(["verificar", "--dir", str(carpeta)]) == 2                                              # sin procedencia: no válido
    assert lista_contrasenas.main(["procedencia", "--dir", str(carpeta), "--herramienta", "haveibeenpwned-downloader prueba", "--fecha-obtencion", "2026-11-17"]) == 0
    datos = json.loads((carpeta / "procedencia.json").read_text(encoding="utf-8"))
    assert datos["rangos"] == RANGOS and datos["fuente"] == conjunto.FUENTE and datos["formato"] == "sha1-por-rangos" and datos["sha256_del_indice"] is None
    capsys.readouterr()
    assert lista_contrasenas.main(["verificar", "--dir", str(carpeta), "--muestra", "5"]) == 0
    assert f"{RANGOS} rangos SHA-1" in capsys.readouterr().out
    (carpeta / "00004.txt").write_bytes(b"esto no es el formato oficial\r\n")                                            # un rango corrupto lo detecta la muestra
    assert lista_contrasenas.main(["verificar", "--dir", str(carpeta), "--muestra", str(RANGOS * 40)]) == 2
    assert lista_contrasenas.main(["procedencia", "--dir", str(carpeta), "--herramienta", "h", "--fecha-obtencion", "ayer"]) == 2


# ===================================================== configuración: inactiva sin conjunto, fallo cerrado con uno inválido ====

def test_sin_conjunto_la_comprobacion_esta_inactiva_y_se_avisa_al_arrancar(caplog):
    with caplog.at_level(logging.INFO, logger="smartwork.contrasenas_comprometidas"):
        assert conjunto.comprobar_configuracion() is None
    assert not conjunto.hay_listado() and not conjunto.es_comprometida(COMPROMETIDA)
    assert any("INACTIVA" in r.getMessage() for r in caplog.records)


def test_con_una_instalacion_incompleta_configurada_la_api_no_arranca(tmp_path, monkeypatch):
    carpeta = instalar(tmp_path)
    (carpeta / "00002.txt").unlink()
    monkeypatch.setattr(get_settings(), "compromised_passwords_dir", str(carpeta))
    conjunto.reiniciar()
    with pytest.raises(conjunto.ListaNoValida):
        crear_app()


def test_con_una_instalacion_completa_se_activa_y_dice_que_es_la_de_su_fecha(instalado, caplog):
    with caplog.at_level(logging.INFO, logger="smartwork.contrasenas_comprometidas"):
        assert conjunto.comprobar_configuracion() is not None
    assert conjunto.hay_listado() and conjunto.es_comprometida(COMPROMETIDA) and not conjunto.es_comprometida(AUSENTE) and not conjunto.es_comprometida(RELLENO)
    texto = " ".join(r.getMessage() for r in caplog.records)
    assert "completo a fecha 2026-11-17" in texto and "posteriores" in texto and COMPROMETIDA not in texto and sha1(COMPROMETIDA) not in texto


def test_la_comprobacion_no_tiene_ninguna_comunicacion_externa():
    """El módulo solo importa biblioteca estándar local (hashes, archivos, JSON, registros): ni red, ni clientes HTTP, ni procesos."""
    arbol = ast.parse(Path(conjunto.__file__).read_text(encoding="utf-8"))
    importados = {a.name.split(".")[0] for n in ast.walk(arbol) if isinstance(n, ast.Import) for a in n.names}
    importados |= {n.module.split(".")[0] for n in ast.walk(arbol) if isinstance(n, ast.ImportFrom) and n.module}
    assert importados <= {"hashlib", "json", "logging", "os", "re", "dataclasses", "datetime", "functools", "pathlib", "app"}, importados


# ===================================================== primer acceso ========================================================

def test_primer_acceso_rechaza_una_comprometida_sin_consumir_el_codigo_y_despues_acepta_una_valida(mundo_primer_acceso, instalado):
    c = cliente()
    r = canjear_primer_acceso(c, "ana", mundo_primer_acceso["codigo"]["ana"], COMPROMETIDA)
    assert r.status_code == 422 and r.json()["codigo"] == "CONTRASENA_NO_VALIDA" and r.json()["detalles"] == [{"campo": "contrasena_nueva", "motivo": "comprometida"}]
    assert r.headers["cache-control"] == "no-store"
    assert estado_primer_acceso("ana") == [(False, False, 0)] and password_establecida("ana") == (False, False)       # el código sigue vivo y sin intentos; nada cambió
    ok = canjear_primer_acceso(c, "ana", mundo_primer_acceso["codigo"]["ana"], AUSENTE)                                  # la MISMA clave de código, con una contraseña válida
    assert ok.status_code == 204 and estado_primer_acceso("ana") == [(True, False, 0)] and password_establecida("ana") == (True, True)


def test_una_contrasena_no_incluida_o_con_cuenta_cero_se_acepta_y_la_longitud_sigue_mandando(mundo_primer_acceso, instalado):
    corta = canjear_primer_acceso(cliente(), "ana", mundo_primer_acceso["codigo"]["ana"], "corta")
    assert corta.json()["detalles"][0]["motivo"] == "demasiado_corta"
    assert canjear_primer_acceso(cliente(), "ana", mundo_primer_acceso["codigo"]["ana"], AUSENTE).status_code == 204          # su rango existe pero no figura
    assert canjear_primer_acceso(cliente(), "beto", mundo_primer_acceso["codigo"]["beto"], RELLENO).status_code == 204        # relleno (cuenta 0): no es comprometida


def test_la_comprometida_no_es_un_oraculo_de_codigos(mundo_primer_acceso, instalado):
    uno = canjear_primer_acceso(cliente("203.0.113.9"), "ana", mundo_primer_acceso["codigo"]["ana"], COMPROMETIDA)
    otro = canjear_primer_acceso(cliente("203.0.113.9"), "ana", "ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZZ", COMPROMETIDA)
    inexistente = canjear_primer_acceso(cliente("203.0.113.9"), "no-existe", "ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZZ", COMPROMETIDA)
    assert huella(uno) == huella(otro) == huella(inexistente) and uno.status_code == 422


def test_sin_conjunto_la_comprobacion_no_actua_y_se_acepta_cualquier_contrasena_de_longitud_valida(mundo_primer_acceso):
    """Es el estado por defecto: inactiva. La prueba lo deja a la vista para que no se confunda con una cobertura."""
    assert not conjunto.hay_listado()
    assert canjear_primer_acceso(cliente(), "ana", mundo_primer_acceso["codigo"]["ana"], COMPROMETIDA).status_code == 204


# ===================================================== recuperación: el mismo control ========================================

def test_recuperacion_aplica_el_mismo_control_sin_consumir_el_codigo_ni_revocar_sesiones_y_despues_acepta_una_valida(mundo_recuperacion, instalado):
    previas = sesiones_de("beto", 2)
    r = canjear_recuperacion(cliente(), "beto", mundo_recuperacion["codigo"], COMPROMETIDA)
    assert r.status_code == 422 and r.json()["detalles"] == [{"campo": "contrasena_nueva", "motivo": "comprometida"}] and r.headers["cache-control"] == "no-store"
    assert estado_recuperacion("beto") == [(False, False, 0)] and vigentes("beto") == 2 and all(c.get(f"{API}/sesion").status_code == 200 for c in previas)
    assert huella(canjear_recuperacion(cliente("203.0.113.8"), "beto", "ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZZ", COMPROMETIDA)) == huella(
        canjear_recuperacion(cliente("203.0.113.8"), "beto", mundo_recuperacion["codigo"], COMPROMETIDA))             # tampoco aquí hay oráculo
    ok = canjear_recuperacion(cliente(), "beto", mundo_recuperacion["codigo"], AUSENTE)
    assert ok.status_code == 204 and estado_recuperacion("beto") == [(True, False, 0)] and vigentes("beto") == 0


def test_primer_acceso_y_recuperacion_rechazan_la_misma_contrasena_con_la_misma_respuesta(mundo_recuperacion, instalado):
    a = canjear_primer_acceso(cliente("203.0.113.20"), "ana", mundo_recuperacion["primer"], COMPROMETIDA)
    b = canjear_recuperacion(cliente("203.0.113.21"), "beto", mundo_recuperacion["codigo"], COMPROMETIDA)
    assert huella(a) == huella(b) and a.status_code == 422


# ===================================================== la contraseña no se registra ni se guarda ============================

def test_ninguna_contrasena_hash_ni_codigo_queda_en_los_registros_ni_en_la_auditoria(mundo_primer_acceso, instalado, caplog):
    with caplog.at_level(logging.DEBUG):
        canjear_primer_acceso(cliente(), "ana", mundo_primer_acceso["codigo"]["ana"], COMPROMETIDA)
        canjear_primer_acceso(cliente(), "ana", mundo_primer_acceso["codigo"]["ana"], AUSENTE)
    codigo = mundo_primer_acceso["codigo"]["ana"]
    visibles = [COMPROMETIDA, AUSENTE, sha1(COMPROMETIDA), sha1(COMPROMETIDA)[5:], sha1(AUSENTE), sha1(AUSENTE)[5:], codigo, codigo.replace("-", "")]
    assert not any(v in caplog.text for v in visibles)
    auditoria = json.dumps(filas("select valor_anterior, valor_nuevo from auditoria"), default=str)
    assert not any(v in auditoria for v in visibles)


def test_un_fallo_de_la_base_durante_el_canje_no_registra_el_hash_de_la_contrasena_ni_el_del_codigo(mundo_primer_acceso, caplog, monkeypatch):
    """SQLAlchemy incluye por defecto los parámetros de la sentencia en el texto de sus errores, y el manejador de errores internos registra la traza: sin
    ``hide_parameters`` el hash Argon2 de la contraseña nueva y el HMAC del código acabarían en el registro."""
    from sqlalchemy import text
    from app.modulos.acceso import primer_acceso
    from app.seguridad import codigos
    averiada = text("select public.canjear_codigo_primer_acceso(:i, :hc, :hp) / 0")                    # error de la base, con los tres parámetros en la sentencia
    monkeypatch.setitem(primer_acceso.FUNCIONES, "canjear_codigo_primer_acceso", averiada)
    codigo = mundo_primer_acceso["codigo"]["ana"]
    with caplog.at_level(logging.DEBUG):
        r = canjear_primer_acceso(cliente(), "ana", codigo, BUENA)
    assert r.status_code == 500 and r.json()["codigo"] == "ERROR_INTERNO"
    assert "$argon2id$" not in caplog.text and codigos.hash_de_codigo(codigo) not in caplog.text
    assert BUENA not in caplog.text and codigo not in caplog.text
