"""M1-T8.1 — generación y hash de códigos, secreto independiente y política de contraseñas (funciones puras y configuración).

Pruebas esenciales: entropía y forma canónica, entrada tolerante pero estricta, HMAC con secreto propio e independiente de ``AUTH_PEPPER``, fallo
cerrado sin secreto y política de contraseñas de A8. La base de datos (estados, uso único, permisos, migración) se prueba en ``test_db_codigo_unico.py``.
"""

import re

import pytest

from app.config import Settings, get_settings
from app.errores import CATALOGO
from app.seguridad import codigos, control_de_intentos as control
from app.seguridad.politica_contrasenas import (
    COMPROMETIDA, DEMASIADO_CORTA, DEMASIADO_LARGA, ContrasenaNoValida, evaluar_contrasena, exigir_contrasena,
)

# ===================================================== generación y entropía (A4: 128 bits) =================================

def test_un_codigo_nuevo_son_128_bits_en_26_caracteres_canonicos_y_vuelve_a_los_mismos_octetos():
    for _ in range(50):
        c = codigos.generar_codigo()
        assert re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", c)
        octetos = codigos.normalizar(c)
        assert octetos is not None and len(octetos) == 16 and codigos._codificar(octetos) == c


def test_los_codigos_no_se_repiten_y_cada_bit_se_reparte_como_un_generador_aleatorio():
    octetos = [codigos.generar_octetos() for _ in range(600)]
    assert len(set(octetos)) == 600
    for bit in range(128):
        unos = sum((o[bit // 8] >> (7 - bit % 8)) & 1 for o in octetos)
        assert 180 < unos < 420, bit                                    # ~300 ± 5 desviaciones típicas: un bit sesgado fallaría


# ===================================================== entrada: tolerante pero canónica ======================================

def test_la_entrada_admite_formato_minusculas_espacios_y_confusiones_habituales():
    c = codigos.generar_codigo()
    esperado = codigos.normalizar(c)
    variantes = [codigos.formatear(c), codigos.formatear(c).lower(), "  " + codigos.formatear(c).replace("-", " ") + " ",
                 c.replace("0", "O").replace("1", "I"), c.replace("1", "l")]
    assert all(codigos.normalizar(v) == esperado for v in variantes)


@pytest.mark.parametrize("texto", ["", "ABC", "U" * 26, "!" * 26, "0" * 25, "0" * 27, "Z" * 26, "0" * 300])
def test_lo_que_no_es_un_codigo_bien_formado_se_rechaza_sin_llegar_a_la_base(texto):
    assert codigos.normalizar(texto) is None and codigos.hash_de_codigo(texto) is None


def test_una_codificacion_no_canonica_no_da_un_segundo_codigo_valido():
    c = codigos.generar_codigo()
    otra = c[:-1] + _siguiente(c[-1])                          # cambia los bits de relleno del último carácter
    assert codigos.normalizar(otra) is None


def _siguiente(c):
    return codigos.ALFABETO[(codigos.ALFABETO.index(c) + 1) % 32]


def test_el_formato_para_mostrar_son_grupos_de_cinco():
    f = codigos.formatear(codigos.generar_codigo())
    assert re.fullmatch(r"[0-9A-Z]{5}(-[0-9A-Z]{5}){3}-[0-9A-Z]{6}", f)


# ===================================================== HMAC y secreto independiente (D1) =====================================

def test_el_hash_es_un_hmac_hexadecimal_determinista_que_no_contiene_el_codigo():
    c = codigos.generar_codigo()
    h = codigos.hash_de_codigo(codigos.formatear(c))
    assert re.fullmatch(r"[0-9a-f]{64}", h) and h == codigos.hash_de_codigo(c.lower()) and c.lower() not in h
    assert codigos.hash_de_codigo(codigos.generar_codigo()) != h
    assert codigos.hashes_coinciden(h, h) and not codigos.hashes_coinciden(h, codigos.hash_senuelo())


def test_otro_secreto_de_codigos_da_otro_hash_y_cambiar_auth_pepper_no_lo_altera(monkeypatch):
    c = codigos.generar_codigo()
    antes = codigos.hash_de_codigo(c)
    monkeypatch.setattr(get_settings(), "auth_pepper", type(get_settings().auth_pepper)("z" * 40))
    assert codigos.hash_de_codigo(c) == antes                           # el secreto de los códigos es independiente de AUTH_PEPPER
    monkeypatch.setattr(get_settings(), "code_pepper", type(get_settings().code_pepper)("y" * 40))
    assert codigos.hash_de_codigo(c) != antes


def test_el_secreto_de_los_codigos_no_puede_ser_el_de_las_claves_de_control_ni_corto():
    with pytest.raises(ValueError):
        Settings(_env_file=None, auth_pepper="a" * 40, code_pepper="a" * 40)
    with pytest.raises(ValueError):
        Settings(_env_file=None, code_pepper="corto")
    s = Settings(_env_file=None, code_pepper="b" * 40)
    assert "b" * 40 not in repr(s) and s.code_validity_minutes == 10


def test_sin_secreto_de_codigos_se_falla_cerrado(monkeypatch):
    monkeypatch.setattr(get_settings(), "code_pepper", None)
    with pytest.raises(codigos.SecretoDeCodigosNoConfigurado):
        codigos.hash_de_codigo(codigos.generar_codigo())
    with pytest.raises(codigos.SecretoDeCodigosNoConfigurado):
        codigos.comprobar_configuracion()


@pytest.mark.parametrize("minutos", [0, -1, 1441])
def test_la_vigencia_configurable_tiene_limites(minutos):
    with pytest.raises(ValueError):
        Settings(_env_file=None, code_validity_minutes=minutos)


def test_el_control_de_intentos_del_canje_tiene_un_dominio_propio():
    assert control.clave_de_canje("ana", "1.2.3.4") not in {control.clave_de_cuenta("ana", "1.2.3.4"), control.clave_de_origen("1.2.3.4"),
                                                            control.clave_de_operador("ana")}


def test_los_codigos_de_error_reservados_no_revelan_cuentas():
    assert CATALOGO["CODIGO_NO_VALIDO"][0] == 400 and CATALOGO["CONTRASENA_NO_VALIDA"][0] == 422
    for c in ("CODIGO_NO_VALIDO", "CONTRASENA_NO_VALIDA"):
        assert not re.search(r"identificador|usuario|cuenta|caduc|usado|desactiv", CATALOGO[c][1], re.I)


# ===================================================== política de contraseñas (A8) ==========================================

def test_la_contrasena_exige_diez_caracteres_y_ninguna_regla_de_composicion():
    assert evaluar_contrasena("a" * 9) == DEMASIADO_CORTA
    for valida in ("a" * 10, "          ", "1234567890", "contraseña larga con espacios", "ÁÉÍÓÚáéíóúñ"):
        assert evaluar_contrasena(valida) is None, valida


def test_se_cuentan_caracteres_unicode_no_octetos_y_hay_un_maximo():
    assert evaluar_contrasena("🙂" * 9) == DEMASIADO_CORTA and evaluar_contrasena("🙂" * 10) is None
    assert evaluar_contrasena("a" * (get_settings().login_password_max_length + 1)) == DEMASIADO_LARGA


def test_el_minimo_lo_gobierna_la_configuracion(monkeypatch):
    monkeypatch.setattr(get_settings(), "password_min_length", 12)
    assert evaluar_contrasena("a" * 11) == DEMASIADO_CORTA and evaluar_contrasena("a" * 12) is None


def test_el_enganche_de_contrasenas_comprometidas_se_aplica_si_se_da_y_el_error_no_lleva_la_contrasena():
    assert evaluar_contrasena("una-contraseña-larga", es_comprometida=lambda c: True) == COMPROMETIDA
    assert evaluar_contrasena("una-contraseña-larga") is None                       # sin lista local todavía (T8.6)
    with pytest.raises(ContrasenaNoValida) as error:
        exigir_contrasena("secreta-pero-comprometida", es_comprometida=lambda c: True)
    assert error.value.motivo == COMPROMETIDA and "secreta" not in str(error.value) and "secreta" not in repr(error.value)
