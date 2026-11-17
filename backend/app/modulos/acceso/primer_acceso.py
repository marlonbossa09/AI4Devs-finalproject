"""M1-03b — Completar el primer acceso (``POST /api/v1/acceso/primer-acceso``; M1-T8.3) y M1-09b — Completar la recuperación
(``POST /api/v1/acceso/recuperacion``; M1-T8.4).

Primer acceso: una identidad sin contraseña la establece con un código de primer acceso válido. Recuperación: una identidad CON contraseña la cambia con un
código de recuperación válido y se revocan todas sus sesiones; nunca reactiva un acceso desactivado. Ninguna abre sesión: la persona inicia sesión después con
M1-01a. Públicas (el código es quien las limita); se verifica el origen como en el inicio de sesión. 204 sin cuerpo. Las dos comparten TODO lo que sigue
(solo cambia la función de la base), también el comportamiento de la política de contraseña, y comparten el contador de intentos de canje.

Orden, pensado para que nada permita sondear códigos ni cuentas:

1. Origen y forma de la petición (sin tocar la base). Un error de forma es 400 y no cuenta como intento.
2. Control de intentos de M1-T7 con un dominio de clave propio para el canje (identificador normalizado y origen), ANTES de hacer ningún trabajo:
   reserva atómica, curva de esperas, límites por origen y 429 con ``Retry-After``. Todo canje fallido cuenta; solo un canje efectivo lo reinicia.
3. Política de contraseña (A8: longitud mínima y listado local de contraseñas comprometidas), ANTES de mirar el código: así una contraseña débil recibe la misma respuesta con un código válido que con uno
   inventado (``CONTRASENA_NO_VALIDA``) y NO hay forma de saber si un código es válido por esa vía; tampoco consume el código (D7). Esta rama no prueba
   ningún código, así que devuelve su reserva.
4. Hash Argon2id de la contraseña, SIEMPRE que haya llegado hasta aquí (código válido o no) y fuera de toda transacción: mismo trabajo en todos los casos.
5. UNA transacción con la función ``canjear_codigo_primer_acceso`` (migración 0015) y, solo si el canje es efectivo, el reinicio del contador, todo
   atómico. Un código desconocido, usado, caducado, invalidado, de otra identidad, de una identidad que ya tiene contraseña o de un acceso desactivado
   da el MISMO ``CODIGO_NO_VALIDO``: la función devuelve nulo sin distinguir la causa. El intento fallido de un código pendiente se confirma en esa misma
   transacción (a los 10, el código se invalida).

La aplicación no tiene permisos sobre ``identidad`` ni ``codigo_unico``: solo ejecuta esa función. Ni el código, ni su HMAC, ni la contraseña, ni su hash
se registran ni se devuelven.
"""

from fastapi import APIRouter, Request, Response
from sqlalchemy import text

from app.db import get_engine
from app.errores import AppError
from app.modulos.acceso.esquemas import PrimerAccesoEntrada
from app.seguridad import codigos
from app.seguridad import control_de_intentos as control
from app.seguridad.contrasenas import calcular_hash
from app.seguridad.identificadores import normalizar_identificador
from app.seguridad.origen import direccion_del_cliente, origen_permitido
from app.seguridad.contrasenas_comprometidas import es_comprometida
from app.seguridad.politica_contrasenas import evaluar_contrasena

router = APIRouter(prefix="/acceso", tags=["M1 Acceso"])

SIN_CACHE = {"Cache-Control": "no-store"}


@router.post("/primer-acceso", status_code=204, summary="M1-03b Completar el primer acceso")
def completar_primer_acceso(cuerpo: PrimerAccesoEntrada, request: Request) -> Response:
    return _canjear(cuerpo, request, "canjear_codigo_primer_acceso")


@router.post("/recuperacion", status_code=204, summary="M1-09b Completar la recuperación del acceso")
def completar_recuperacion(cuerpo: PrimerAccesoEntrada, request: Request) -> Response:
    return _canjear(cuerpo, request, "canjear_codigo_recuperacion")


FUNCIONES = {"canjear_codigo_primer_acceso": text("select public.canjear_codigo_primer_acceso(:i, :hc, :hp)"),
             "canjear_codigo_recuperacion": text("select public.canjear_codigo_recuperacion(:i, :hc, :hp)")}


def _canjear(cuerpo: PrimerAccesoEntrada, request: Request, funcion: str) -> Response:
    if not origen_permitido(request):
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "Origin", "motivo": "origen_no_permitido"}])

    normalizado = normalizar_identificador(cuerpo.identificador_acceso)
    motor = get_engine()
    reserva = control.reservar(motor, normalizado, direccion_del_cliente(request), canje=True)
    if isinstance(reserva, control.Denegado):
        raise AppError.demasiadas_solicitudes(reserva.espera_segundos)

    motivo = evaluar_contrasena(cuerpo.contrasena_nueva, es_comprometida=es_comprometida)
    if motivo is not None:
        control.liberar(motor, reserva)                        # no se probó ningún código: la contraseña no consume intentos ni el código
        raise AppError("CONTRASENA_NO_VALIDA", [{"campo": "contrasena_nueva", "motivo": motivo}], cabeceras=SIN_CACHE)

    hash_contrasena = calcular_hash(cuerpo.contrasena_nueva)
    # Un código mal formado no llega a compararse con nada: se usa un HMAC señuelo para hacer el mismo trabajo y dar la misma respuesta.
    hash_codigo = codigos.hash_de_codigo(cuerpo.codigo) or codigos.hash_senuelo()

    with motor.begin() as c:
        persona = c.execute(FUNCIONES[funcion], {"i": normalizado, "hc": hash_codigo, "hp": hash_contrasena}).scalar_one()
        if persona is not None:
            control.liberar_en(c, reserva)                     # canje efectivo: reinicia el contador, en la misma transacción que la contraseña
    if persona is None:
        raise AppError("CODIGO_NO_VALIDO", cabeceras=SIN_CACHE)
    return Response(status_code=204, headers=SIN_CACHE)
