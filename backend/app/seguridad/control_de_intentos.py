"""Protección frente a intentos fallidos de autenticación (M1-T7; ADR-002, A9 y A11; decisiones del 2026-11-17).

DISEÑO, COMO MÁQUINA DE ESTADOS (por clave de control; ``clave`` es un HMAC, nunca el identificador ni el origen en claro)
-----------------------------------------------------------------------------------------------------------------------
Una clave de cuenta es el HMAC del par (identificador normalizado, origen). Su estado es ``(intentos, permitido_desde,
ultimo_intento_en)``; sin fila, el estado es «limpio».

* **RESERVAR** (antes de calcular Argon2, en una transacción corta que se confirma enseguida y bajo un bloqueo consultivo por
  clave; nunca se mantiene una transacción ni un bloqueo mientras se calcula el hash):
    1. Si ``ahora - ultimo_intento_en >= 24 h``, el contador se OLVIDA (estado limpio).
    2. Si ``ahora < permitido_desde``: DENEGADO (HTTP 429, ``Retry-After`` = lo que falta). No se verifica la contraseña ni,
       por tanto, se distingue una cuenta que existe de otra que no. Una petición denegada NO cambia el estado: no prolonga
       la espera, de modo que nadie puede alargar la espera de otra persona repitiendo peticiones.
    3. En otro caso, CONCEDIDO: ``intentos += 1`` y ``ultimo_intento_en = ahora``. La reserva cuenta el intento COMO FALLIDO
       (pesimista) y fija ya la espera que seguirá si falla: tras el intento n >= ``libres`` (5), el siguiente intento debe
       esperar ``min(base * 2 ** (n - libres), máximo)`` (30 s, 1, 2, 4, 8, 16, 32 min y 1 hora, que es el máximo).
* **LIBERAR** (autenticación COMPLETA: contraseña correcta, acceso habilitado y pertenencia vigente): se borra la fila de la clave
  de cuenta y la reserva del origen. Es el reinicio del contador tras una autenticación válida. Con una contraseña correcta pero el
  acceso desactivado o sin pertenencia vigente NO se libera: el intento sigue contando como los demás.
* **FALLO CONFIRMADO** (credenciales incorrectas): no cambia el estado, que la reserva ya había contado; solo deja el evento
  técnico (y, si el intento fijó una espera, el evento ``espera_aplicada``, una vez por espera y no por cada 429).

Por qué se reserva ANTES de verificar y se cuenta COMO FALLIDO: si se comprobara primero y se contara después, N peticiones en
paralelo verían todas el mismo estado y harían N intentos. La reserva es atómica: solo caben tantos intentos simultáneos como
quedan. La contradicción con «un acierto reinicia el contador» se resuelve con LIBERAR: un acierto devuelve lo reservado. Una
carrera entre un acierto y un fallo de la misma clave puede dejar sin contar a lo sumo los fallos en vuelo de esa carrera (la
persona ya conocía la contraseña); se documenta y no abre ninguna vía para adivinarla.

LÍMITES POR ORIGEN: ventana deslizante sobre las reservas del origen (30 en 5 minutos y 200 en 1 hora, configurables). Un acierto
devuelve su reserva, así que solo cuentan los intentos fallidos y una red compartida no se penaliza por sus inicios correctos.
Las filas salen solas de la ventana. NO hay ningún bloqueo permanente: todo lo que se escribe caduca.

IMPOSIBILIDAD DE BLOQUEAR A TERCEROS: la clave de cuenta incluye el origen, de modo que los fallos de otro origen no esperan a
la víctima; las peticiones denegadas no cambian nada; y no existe ningún estado que dure más de 24 horas sin nuevos intentos.
Riesgo residual (documentado): quien comparte origen con la víctima puede retrasarla hasta el máximo de 1 hora por espera.

PERSONAS OPERADORAS (CLI): la misma curva y el mismo olvido, con un contador SEPARADO (tabla propia, solo accesible al rol de
provisión) y sin origen (no hay red: es una orden local del servidor). Nunca se deshabilita a la persona operadora.

NO IMPLEMENTADO (decisión del 2026-11-17): el tope agregado de 100 fallos por cuenta con deshabilitación automática de la
contraseña. Los intentos repartidos entre muchos orígenes no los frena este contador (solo los límites por origen).

Este módulo no registra ni devuelve ninguna contraseña ni identificador en claro.
"""

import hashlib
import hmac
import ipaddress
import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Connection, Engine, text

from app.config import get_settings

# Filas caducadas que cada reserva elimina, como máximo, de entre las de OTRAS claves (limpieza acotada sin planificador;
# se omiten las filas bloqueadas por otra transacción). Es un detalle de implementación, no una regla del producto.
LIMITE_DE_LIMPIEZA = 50

AMBITO_PERSONA = "persona"
AMBITO_OPERADOR = "operador"

TABLA_PERSONAS = "control_de_intentos"
TABLA_OPERADORES = "control_de_intentos_operador"


class ProteccionNoConfigurada(RuntimeError):
    """Falta AUTH_PEPPER: sin él no se puede proteger el inicio de sesión y se falla cerrado."""


# ------------------------------------------------------------------------------------------------ claves (HMAC)

def _pepper() -> bytes:
    secreto = get_settings().auth_pepper
    if secreto is None:
        raise ProteccionNoConfigurada("Falta AUTH_PEPPER: el control de intentos no puede funcionar sin él")
    return secreto.get_secret_value().encode("utf-8")


def _hmac(dominio: str, *partes: str) -> str:
    """HMAC-SHA256 con separación de dominio y longitudes explícitas (dos pares distintos nunca dan la misma entrada)."""
    mensaje = b"".join(f"{len(p.encode('utf-8'))}:".encode() + p.encode("utf-8") for p in (dominio, *partes))
    return hmac.new(_pepper(), mensaje, hashlib.sha256).hexdigest()


def clave_de_cuenta(identificador_normalizado: str, origen: str) -> str:
    return _hmac("smartwork-intentos-cuenta-v1", identificador_normalizado, origen)


def clave_de_origen(origen: str) -> str:
    return _hmac("smartwork-intentos-origen-v1", origen)


def clave_de_canje(identificador_normalizado: str, origen: str) -> str:
    """Clave del control de intentos del CANJE de códigos (M1-T8; D9 del 2026-11-17): dominio propio, distinto del de las cuentas, para que los
    fallos de canje y los de inicio de sesión no se mezclen. Aún no la usa ninguna ruta."""
    return _hmac("smartwork-intentos-canje-v1", identificador_normalizado, origen)


def clave_de_operador(identificador_normalizado: str) -> str:
    return _hmac("smartwork-intentos-operador-v1", identificador_normalizado)


def comprobar_configuracion() -> None:
    """Falla al arrancar, no en la primera petición, si falta el secreto."""
    _pepper()


# ------------------------------------------------------------------------------------------------ curva de espera

def espera_tras_el_intento(n: int) -> int | None:
    """Segundos que debe esperar el intento SIGUIENTE si el intento número ``n`` falla; ``None`` mientras queden intentos libres.

    n < libres: sin espera. n = libres: la espera base (30 s). Cada fallo más la duplica, hasta el máximo (1 hora)."""
    s = get_settings()
    if n < s.login_free_attempts:
        return None
    exponente = n - s.login_free_attempts
    # Se acota el exponente antes de calcular: nunca se construye un entero enorme.
    if exponente >= 40:
        return s.login_wait_max_seconds
    return min(s.login_wait_base_seconds * (2 ** exponente), s.login_wait_max_seconds)


def segundos_de_espera(restante: timedelta) -> int:
    """``Retry-After``: segundos enteros, redondeando hacia arriba y como mínimo 1."""
    return max(1, math.ceil(restante.total_seconds()))


# ------------------------------------------------------------------------------------------------ reloj

def _ahora(conexion: Connection) -> datetime:
    """Hora actual del servidor de base de datos (una sola referencia de tiempo para todas las instancias). Las pruebas
    sustituyen esta función para controlar el tiempo sin esperar."""
    return conexion.execute(text("select clock_timestamp()")).scalar_one()


# ------------------------------------------------------------------------------------------------ resultados

@dataclass(frozen=True)
class Reserva:
    """Un intento concedido. ``espera_resultante`` es la espera que seguirá si el intento falla (None si no hay)."""

    clave: str
    id_origen: uuid.UUID | None
    espera_resultante: int | None
    tabla: str = TABLA_PERSONAS


@dataclass(frozen=True)
class Denegado:
    """Un intento denegado por espera o por límite de origen: 429 con ``Retry-After`` = ``espera_segundos``."""

    espera_segundos: int
    motivo: str          # 'espera' | 'limite_de_origen' (solo para las pruebas y el diagnóstico, nunca se envía al cliente)


# ------------------------------------------------------------------------------------------------ contador por clave

def _bloquear(conexion: Connection, clave: str) -> None:
    conexion.execute(text("select pg_advisory_xact_lock(hashtextextended(:c, 0))"), {"c": clave})


def _limpiar_caducados(conexion: Connection, tabla: str, columna: str, limite: datetime, clave_col: str) -> None:
    """Elimina, como máximo, ``LIMITE_DE_LIMPIEZA`` filas caducadas (las más antiguas primero). Solo limpia una transacción a la
    vez (candado consultivo NO bloqueante: si otra está limpiando, esta sigue sin esperar), así que dos limpiezas nunca se esperan
    en círculo. Las consultas ignoran de todos modos lo caducado: esto solo acota el tamaño de las tablas, sin planificador."""
    if not conexion.execute(text("select pg_try_advisory_xact_lock(hashtextextended(:c, 0))"),
                            {"c": f"smartwork:intentos:limpieza:{tabla}"}).scalar_one():
        return
    conexion.execute(text(
        f"delete from {tabla} where {clave_col} in (select {clave_col} from {tabla} where {columna} < :l "
        f"order by {columna} limit :n)"), {"l": limite, "n": LIMITE_DE_LIMPIEZA})


def _evaluar(c: Connection, tabla: str, clave: str, ahora: datetime):
    """Estado de la clave tras aplicar el olvido: (fila o None, Denegado o None). No escribe nada salvo el borrado del
    contador olvidado."""
    s = get_settings()
    fila = c.execute(text(f"select intentos, permitido_desde, ultimo_intento_en from {tabla} where clave = :k for update"),
                     {"k": clave}).one_or_none()
    if fila is not None and ahora - fila.ultimo_intento_en >= timedelta(hours=s.login_counter_forget_hours):
        c.execute(text(f"delete from {tabla} where clave = :k"), {"k": clave})
        fila = None                                                   # el contador se olvida tras 24 h sin nuevos intentos
    if fila is not None and fila.permitido_desde is not None and ahora < fila.permitido_desde:
        return fila, Denegado(segundos_de_espera(fila.permitido_desde - ahora), "espera")
    return fila, None


def _contar_intento(c: Connection, tabla: str, clave: str, fila, ahora: datetime) -> int | None:
    """Cuenta el intento concedido (pesimista) y fija la espera que seguirá si falla. Devuelve esa espera, en segundos."""
    n = (fila.intentos if fila is not None else 0) + 1
    espera = espera_tras_el_intento(n)
    permitido_desde = ahora + timedelta(seconds=espera) if espera is not None else None
    if fila is None:
        c.execute(text(f"insert into {tabla} (clave, intentos, permitido_desde, ultimo_intento_en) values (:k, :n, :p, :a)"),
                  {"k": clave, "n": n, "p": permitido_desde, "a": ahora})
    else:
        c.execute(text(f"update {tabla} set intentos = :n, permitido_desde = :p, ultimo_intento_en = :a where clave = :k"),
                  {"k": clave, "n": n, "p": permitido_desde, "a": ahora})
    return espera


# ------------------------------------------------------------------------------------------------ límites por origen

def _denegacion_por_origen(conexion: Connection, clave_origen: str, ahora: datetime) -> Denegado | None:
    s = get_settings()
    espera = timedelta(0)
    for intentos, ventana in ((s.login_origin_short_attempts, s.login_origin_short_window_seconds),
                              (s.login_origin_long_attempts, s.login_origin_long_window_seconds)):
        desde = ahora - timedelta(seconds=ventana)
        # El intento que libera sitio es el n-ésimo más reciente de la ventana: sale de ella a los ``ventana`` segundos.
        fila = conexion.execute(text(
            "select en from intento_de_origen where clave_origen = :o and en > :d order by en desc offset :k limit 1"),
            {"o": clave_origen, "d": desde, "k": intentos - 1}).first()
        if fila is not None:
            espera = max(espera, fila.en + timedelta(seconds=ventana) - ahora)
    return Denegado(segundos_de_espera(espera), "limite_de_origen") if espera > timedelta(0) else None


# ------------------------------------------------------------------------------------------------ personas (HTTP)

def reservar(motor: Engine, identificador_normalizado: str, origen: str, *, canje: bool = False) -> Reserva | Denegado:
    """Reserva atómica de un intento HTTP: de inicio de sesión o, con ``canje``, de canje de un código (M1-T8.3; dominio de clave propio, mismo contador,
    misma curva y los mismos límites por origen). Transacción propia y corta: se confirma aunque la petición falle."""
    clave = clave_de_canje(identificador_normalizado, origen) if canje else clave_de_cuenta(identificador_normalizado, origen)
    clave_org = clave_de_origen(origen)
    s = get_settings()
    with motor.begin() as c:
        # Orden fijo de bloqueos (origen y luego cuenta): ninguna pareja de peticiones puede esperarse en círculo.
        _bloquear(c, f"smartwork:intentos:origen:{clave_org}")
        _bloquear(c, f"smartwork:intentos:cuenta:{clave}")
        ahora = _ahora(c)
        limite_origen = ahora - timedelta(seconds=s.login_origin_long_window_seconds)
        _limpiar_caducados(c, "intento_de_origen", "en", limite_origen, "id")
        _limpiar_caducados(c, TABLA_PERSONAS, "ultimo_intento_en", ahora - timedelta(hours=s.login_counter_forget_hours), "clave")

        denegado = _denegacion_por_origen(c, clave_org, ahora)
        fila, por_espera = _evaluar(c, TABLA_PERSONAS, clave, ahora)
        if por_espera is not None and (denegado is None or por_espera.espera_segundos > denegado.espera_segundos):
            denegado = por_espera
        if denegado is not None:
            return denegado                                           # una petición denegada no cambia ningún estado

        espera = _contar_intento(c, TABLA_PERSONAS, clave, fila, ahora)
        id_origen = c.execute(text("insert into intento_de_origen (clave_origen, en) values (:o, :a) returning id"),
                              {"o": clave_org, "a": ahora}).scalar_one()
        return Reserva(clave, id_origen, espera)


def liberar_en(conexion: Connection, reserva: Reserva) -> None:
    """Se reinicia el contador de la cuenta y se devuelve la reserva del origen, en la transacción de ``conexion``.

    SOLO se llama cuando la autenticación es COMPLETA: contraseña correcta Y acceso habilitado Y pertenencia vigente (decisión del
    2026-11-17). Con credenciales válidas pero sin poder operar, el intento sigue contando: así no se pueden sondear sin límite
    contraseñas de cuentas desactivadas. Bloqueo de la persona (ya tomado por quien llama) y después el de la cuenta: nadie toma
    esos dos en orden inverso (la reserva solo toma origen y cuenta)."""
    _bloquear(conexion, f"smartwork:intentos:cuenta:{reserva.clave}")
    conexion.execute(text(f"delete from {reserva.tabla} where clave = :k"), {"k": reserva.clave})
    if reserva.id_origen is not None:
        conexion.execute(text("delete from intento_de_origen where id = :i"), {"i": reserva.id_origen})


def liberar(motor: Engine, reserva: Reserva) -> None:
    """Igual que ``liberar_en``, en una transacción propia."""
    with motor.begin() as c:
        liberar_en(c, reserva)


# ------------------------------------------------------------------------------------------------ personas operadoras (CLI)

def reservar_operador(conexion: Connection, identificador_normalizado: str) -> Reserva | Denegado:
    """Reserva del intento de una persona operadora. Lo llama quien abre una transacción corta con el rol de provisión; el
    contador es distinto del de las personas y solo ese rol puede tocarlo. Nunca deshabilita a la persona operadora."""
    clave = clave_de_operador(identificador_normalizado)
    s = get_settings()
    _bloquear(conexion, f"smartwork:intentos:operador:{clave}")
    ahora = _ahora(conexion)
    _limpiar_caducados(conexion, TABLA_OPERADORES, "ultimo_intento_en", ahora - timedelta(hours=s.login_counter_forget_hours), "clave")
    fila, denegado = _evaluar(conexion, TABLA_OPERADORES, clave, ahora)
    if denegado is not None:
        return denegado
    return Reserva(clave, None, _contar_intento(conexion, TABLA_OPERADORES, clave, fila, ahora), TABLA_OPERADORES)


def liberar_operador(conexion: Connection, reserva: Reserva) -> None:
    _bloquear(conexion, f"smartwork:intentos:operador:{reserva.clave}")
    conexion.execute(text(f"delete from {TABLA_OPERADORES} where clave = :k"), {"k": reserva.clave})


# ------------------------------------------------------------------------------------------------ eventos técnicos (A11)

TIPOS_DE_EVENTO = ("inicio_correcto", "inicio_fallido", "espera_aplicada", "cierre_sesion",
                   "acceso_desactivado_en_inicio", "revocacion_por_desactivacion")


def registrar_evento(conexion: Connection, tipo: str, *, ambito: str = AMBITO_PERSONA, persona_id: uuid.UUID | None = None,
                     sesion_id: uuid.UUID | None = None, clave_cuenta: str | None = None, clave_origen: str | None = None,
                     detalle: dict | None = None) -> None:
    """Un evento técnico de autenticación, de solo anexado, separado de la auditoría funcional. Sin secretos: ``detalle`` solo
    lleva datos que fija el código (motivo estable, segundos de espera, número de sesiones)."""
    if tipo not in TIPOS_DE_EVENTO:
        raise ValueError("Tipo de evento de autenticación desconocido")
    conexion.execute(text(
        "insert into evento_autenticacion (tipo, ambito, persona_id, sesion_id, clave_cuenta, clave_origen, detalle) "
        "values (:t, :a, :p, :s, :c, :o, cast(:d as jsonb))"),
        {"t": tipo, "a": ambito, "p": persona_id, "s": sesion_id, "c": clave_cuenta, "o": clave_origen,
         "d": json.dumps(detalle) if detalle is not None else None})


def registrar_fallo(conexion: Connection, reserva: Reserva, *, ambito: str = AMBITO_PERSONA, clave_origen: str | None = None,
                    motivo: str | None = None) -> None:
    """Confirma un fallo: deja el evento ``inicio_fallido`` y, si el intento fijó una espera, ``espera_aplicada``. Lo llama quien
    abre una transacción propia, para que el evento se conserve aunque la petición termine en error."""
    registrar_evento(conexion, "inicio_fallido", ambito=ambito, clave_cuenta=reserva.clave, clave_origen=clave_origen,
                     detalle={"motivo": motivo} if motivo else None)
    if reserva.espera_resultante is not None:
        registrar_evento(conexion, "espera_aplicada", ambito=ambito, clave_cuenta=reserva.clave, clave_origen=clave_origen,
                         detalle={"espera_segundos": reserva.espera_resultante})


# ------------------------------------------------------------------------------------------------ origen de la petición

def _como_direccion(valor: str):
    direccion = ipaddress.ip_address(valor.strip())
    if isinstance(direccion, ipaddress.IPv6Address) and direccion.ipv4_mapped is not None:
        return direccion.ipv4_mapped
    return direccion


def _es_de_confianza(direccion, redes) -> bool:
    return any(direccion in red for red in redes)


def direccion_del_cliente(host: str | None, reenviado: list[str]) -> str:
    """Dirección de origen de una petición (DT-07). ``host`` es la dirección de la conexión TCP; ``reenviado`` son los valores de
    ``X-Forwarded-For``. La cabecera SOLO se acepta si la conexión viene de un proxy expresamente configurado como de confianza
    (``TRUSTED_PROXIES``), y aun así se recorre de derecha a izquierda saltando los proxies de confianza: lo que escribe el
    cliente (a la izquierda) nunca se acepta mientras haya una dirección anterior añadida por un proxy propio."""
    if not host:
        return "desconocido"
    try:
        par = _como_direccion(host)
    except ValueError:
        return host[:64]                     # no es una dirección (por ejemplo, un socket Unix): se usa tal cual, acotada
    redes = [ipaddress.ip_network(r, strict=False) for r in get_settings().trusted_proxies]
    if not redes or not _es_de_confianza(par, redes):
        return str(par)
    entradas = [e for valor in reenviado for e in valor.split(",") if e.strip()]
    for entrada in reversed(entradas):
        try:
            direccion = _como_direccion(entrada)
        except ValueError:
            return str(par)                  # cabecera mal formada: no se interpreta; se usa el proxy
        if not _es_de_confianza(direccion, redes):
            return str(direccion)
    return str(par)
