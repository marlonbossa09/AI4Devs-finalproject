"""Emisión administrativa de códigos de primer acceso y de recuperación (M1-T8.2; contratos M1-03a y M1-09a; ADR-002, 6 y 8; decisiones del 2026-11-17).

SOLO la emisión: no existe canje (T8.3 y T8.4), así que el primer acceso y la recuperación siguen sin ser funcionales. La API no emite códigos: esta
función solo la usa la CLI de provisión, con el rol de provisión, que no puede leer el hash de ningún código.

Qué hace, en UNA transacción (la abre quien la llama) y sin efectos parciales:

1. Valida la forma de la solicitud (finalidad y, en la recuperación, la verificación de identidad estructurada) y que existe el secreto de los códigos.
2. Toma el bloqueo por persona que ya comparten el inicio de sesión y la desactivación del acceso, y SOLO DESPUÉS lee el estado: ninguna comprobación
   previa sin bloqueo sustituye a esta. Una desactivación concurrente se serializa con la emisión (gana quien tome el bloqueo primero; si gana la
   desactivación, la emisión la ve y se rechaza; si gana la emisión, la desactivación invalida el código en su misma transacción).
3. Elegibilidad: la persona e identidad existen; el acceso NO está desactivado (DD-05); el primer acceso solo si la contraseña no está establecida y la
   recuperación solo si lo está. No se exige pertenencia vigente: una persona puede recibir su primer acceso antes de que empiece su pertenencia.
4. Genera el código (128 bits), invalida el pendiente anterior de la misma finalidad y registra el nuevo (solo su HMAC), con la vigencia que calcula PostgreSQL.
5. Audita la emisión reutilizando ``entrega_acceso`` (primer acceso) y ``recuperacion_acceso`` (recuperación), con la fase ``emision``, la finalidad, la persona
   afectada, la persona operadora (por la referencia de provisión) y, en la recuperación, la verificación DECLARADA. Nunca el código ni su hash.
6. Presenta el código con ``presentar`` como último paso, aún dentro de la transacción: si no se puede mostrar, la transacción se deshace y NO queda ningún
   código guardado que nadie haya visto. El código no se guarda en claro en ningún sitio y no puede volver a mostrarse: si algo falla, se emite uno nuevo.

Verificación de identidad (A5): la persona operadora identifica el procedimiento (PRESENCIAL, VIDEOLLAMADA o PROCEDIMIENTO_INTERNO, que debe
corresponder a un protocolo documentado por la organización) y una referencia administrativa de la evidencia. Es lo que DECLARA la persona operadora:
elegir una opción no equivale a que el sistema haya verificado la identidad, y así queda registrado. No se almacenan documentos, imágenes ni descripciones.
"""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, text

from app.provision import codigos as registro
from app.provision.errores import ErrorDeProvision
from app.provision.operadores import Operador
from app.provision.servicio import _auditar, _referencia
from app.seguridad import codigos

PRIMER_ACCESO, RECUPERACION = "primer_acceso", "recuperacion"
PROCEDIMIENTOS = ("PRESENCIAL", "VIDEOLLAMADA", "PROCEDIMIENTO_INTERNO")
# Una REFERENCIA (de un ticket, un acta o un expediente), no una descripción: sin espacios, de 3 a 64 caracteres.
REFERENCIA = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/#-]{2,63}")
OPERACION_DE_AUDITORIA = {PRIMER_ACCESO: "entrega_acceso", RECUPERACION: "recuperacion_acceso"}


@dataclass(frozen=True)
class VerificacionDeIdentidad:
    procedimiento: str
    referencia: str


@dataclass(frozen=True)
class CodigoEmitido:
    """Resultado de una emisión. NO contiene el código ni su hash."""

    invocacion: uuid.UUID
    persona_id: uuid.UUID
    finalidad: str
    codigo_id: uuid.UUID
    caduca_en: datetime
    codigo_anterior_invalidado: bool
    verificacion: VerificacionDeIdentidad | None


def validar_verificacion(procedimiento: str | None, referencia: str | None) -> VerificacionDeIdentidad:
    if procedimiento not in PROCEDIMIENTOS:
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": "procedimiento", "motivo": "no_permitido"}])
    referencia = (referencia or "").strip()
    if not referencia:
        raise ErrorDeProvision("CAMPO_OBLIGATORIO", [{"campo": "referencia", "motivo": "vacia"}])
    if not REFERENCIA.fullmatch(referencia):
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": "referencia", "motivo": "formato"}])
    return VerificacionDeIdentidad(procedimiento, referencia)


def emitir_codigo(conexion: Connection, operador: Operador, *, persona_id: uuid.UUID, finalidad: str,
                  verificacion: VerificacionDeIdentidad | None, presentar: Callable[[str, datetime], None],
                  invocacion: uuid.UUID | None = None) -> CodigoEmitido:
    invocacion = invocacion or uuid.uuid4()
    if finalidad not in (PRIMER_ACCESO, RECUPERACION):
        raise ValueError("Finalidad de código desconocida")
    if finalidad == RECUPERACION and verificacion is None:
        raise ErrorDeProvision("CAMPO_OBLIGATORIO", [{"campo": "verificacion", "motivo": "ausente"}])
    if finalidad == PRIMER_ACCESO and verificacion is not None:
        raise ValueError("El primer acceso no lleva verificación de identidad en este contrato")
    try:
        codigos.comprobar_configuracion()
    except codigos.SecretoDeCodigosNoConfigurado:
        raise ErrorDeProvision("SECRETO_DE_CODIGOS_NO_CONFIGURADO") from None

    # 2. Bloqueo de la persona (el mismo que el inicio de sesión y la desactivación) ANTES de leer su estado.
    conexion.execute(text("select pg_advisory_xact_lock(hashtextextended(:c, 0))"), {"c": f"smartwork:acceso:persona:{persona_id}"})
    fila = conexion.execute(
        text("select p.acceso_desactivado_en, i.id as identidad_id, i.contrasena_establecida_en from persona p "
             "left join identidad i on i.persona_id = p.id where p.id = :p"), {"p": persona_id}).one_or_none()
    if fila is None or fila.identidad_id is None:
        raise ErrorDeProvision("RECURSO_NO_DISPONIBLE", [{"campo": "persona"}])
    if fila.acceso_desactivado_en is not None:
        raise ErrorDeProvision("ACCESO_DESACTIVADO_ADMINISTRATIVAMENTE")
    if finalidad == PRIMER_ACCESO and fila.contrasena_establecida_en is not None:
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": "persona", "motivo": "primer_acceso_ya_completado"}])
    if finalidad == RECUPERACION and fila.contrasena_establecida_en is None:
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": "persona", "motivo": "sin_contrasena_establecida"}])

    # 4. Generación, invalidación del anterior y registro (solo el HMAC), todo en esta transacción.
    codigo, hash_codigo = codigos.generar_codigo_y_hash()
    registrado = registro.registrar_codigo(conexion, identidad_id=fila.identidad_id, finalidad=finalidad, hash_codigo=hash_codigo,
                                           emitido_por=_referencia(operador, invocacion))

    # 5. Auditoría de la emisión: sin el código ni su hash.
    nuevo = {"fase": "emision", "finalidad": finalidad, "codigo_id": str(registrado.id), "caduca_en": registrado.caduca_en.isoformat()}
    if verificacion is not None:
        declarada_en = conexion.execute(text("select clock_timestamp()")).scalar_one()
        nuevo["verificacion"] = {"procedimiento": verificacion.procedimiento, "referencia": verificacion.referencia,
                                 "declarada_en": declarada_en.isoformat(), "declarada_por_la_persona_operadora": True,
                                 "verificada_por_el_sistema": False}
    _auditar(conexion, operador, invocacion, tipo_objeto="persona", objeto_id=persona_id, propietaria=persona_id,
             operacion=OPERACION_DE_AUDITORIA[finalidad], valor_anterior={"codigo_pendiente_invalidado": bool(registrado.invalidados)},
             valor_nuevo=nuevo)

    # 6. Presentación: último paso. Si falla, la transacción se deshace entera y no queda ningún código sin ver.
    try:
        presentar(codigos.formatear(codigo), registrado.caduca_en)
    except Exception:  # noqa: BLE001 - el motivo no se propaga: podría contener texto del código
        raise ErrorDeProvision("CODIGO_NO_PRESENTADO") from None
    return CodigoEmitido(invocacion, persona_id, finalidad, registrado.id, registrado.caduca_en, bool(registrado.invalidados), verificacion)
