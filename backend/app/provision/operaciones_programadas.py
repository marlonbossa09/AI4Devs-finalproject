"""Operaciones de pertenencia PROGRAMADAS de una persona: finalizar, cancelar y sustituir (M1-06 y M1-07). Funciones puras, sin
acceso a la base de datos: trabajan sobre la línea temporal de UNA persona y devuelven la línea resultante.

Una «operación programada» no se almacena: se DERIVA de los intervalos ``[desde, hasta_exclusivo)`` de la persona y de la fecha
actual ``hoy`` de su organización (modelo de datos, 7.1 y IR-30, IR-31, IR-39):

- ``alta``: el primer intervalo empieza después de ``hoy``.
- ``traslado``, ``cambio_de_rol`` o ``traslado_y_cambio_de_rol``: un intervalo posterior al primero empieza después de ``hoy``
  (según cambie el equipo, el rol o ambos respecto del intervalo anterior).
- ``finalizacion``: el último intervalo tiene un fin posterior a ``hoy``.

Todo lo demás es historial EFECTIVO y no se modifica nunca (IR-30). Cancelar una operación retira el intervalo programado y
restituye el fin del intervalo anterior (IR-39). Una operación de la que dependen otras posteriores no se cancela sola: se
cancela un SUFIJO de las operaciones programadas de la persona (S-13); lo que se quiera conservar se vuelve a registrar en la
misma operación atómica (sustituir = cancelar y registrar de nuevo).

Las reglas de IR-03 e IR-32 (supervisión de un equipo) no se comprueban aquí: son de la línea temporal de un EQUIPO y se
validan sobre el resultado de todas las personas afectadas (``linea_temporal.primera_violacion_de_supervision``).
"""

from collections.abc import Hashable, Sequence
from dataclasses import dataclass, replace
from datetime import date

TIPOS_DE_TRANSICION = ("traslado", "cambio_de_rol", "traslado_y_cambio_de_rol")
TIPOS = ("alta", *TIPOS_DE_TRANSICION, "finalizacion")


class Incumplimiento(Exception):
    """Una regla de pertenencia no se cumple. ``codigo`` es el código de error de la orden de provisión y ``motivo`` su detalle."""

    def __init__(self, codigo: str, motivo: str, **extra) -> None:
        self.codigo, self.motivo, self.extra = codigo, motivo, extra
        super().__init__(f"{codigo}:{motivo}")


@dataclass(frozen=True)
class Intervalo:
    """Un intervalo de pertenencia. ``id`` es ``None`` mientras no se ha escrito en la base de datos."""

    id: Hashable | None
    equipo: Hashable
    rol: str
    desde: date
    hasta: date | None


@dataclass(frozen=True)
class OperacionProgramada:
    tipo: str
    fecha: date
    indice: int          # posición del intervalo donde empieza (alta y transiciones) o del último intervalo (finalización)


@dataclass(frozen=True)
class OperacionCancelada:
    tipo: str
    fecha: date
    retirados: tuple[Intervalo, ...]              # intervalos programados que se retiran (con sus valores completos)
    restituido: tuple[Hashable, date | None, date | None] | None   # (id del intervalo anterior, fin anterior, fin nuevo)


def tipo_de_transicion(anterior: Intervalo, siguiente: Intervalo) -> str:
    cambia_equipo, cambia_rol = anterior.equipo != siguiente.equipo, anterior.rol != siguiente.rol
    if cambia_equipo and cambia_rol:
        return "traslado_y_cambio_de_rol"
    return "traslado" if cambia_equipo else "cambio_de_rol"


def operaciones_programadas(intervalos: Sequence[Intervalo], hoy: date) -> list[OperacionProgramada]:
    """Las operaciones programadas de la persona (efecto posterior a ``hoy``), ordenadas por fecha."""
    ordenados = sorted(intervalos, key=lambda i: i.desde)
    ops: list[OperacionProgramada] = []
    for indice, intervalo in enumerate(ordenados):
        if intervalo.desde <= hoy:
            continue
        ops.append(OperacionProgramada("alta" if indice == 0 else tipo_de_transicion(ordenados[indice - 1], intervalo), intervalo.desde, indice))
    if ordenados and ordenados[-1].hasta is not None and ordenados[-1].hasta > hoy:
        ops.append(OperacionProgramada("finalizacion", ordenados[-1].hasta, len(ordenados) - 1))
    return ops


def cancelar(intervalos: Sequence[Intervalo], hoy: date, cancelaciones: Sequence[tuple[str, date]]) -> tuple[list[Intervalo], list[OperacionCancelada]]:
    """Cancela operaciones programadas. Devuelve la línea resultante y el detalle de lo cancelado.

    ``cancelaciones`` son pares (tipo, fecha efectiva de la operación que se cancela). Rechaza con ``Incumplimiento``:
    una fecha igual o anterior a ``hoy`` (la operación ya es efectiva, CA-245), una operación que no existe, un tipo que no
    corresponde, una operación repetida y la cancelación de una operación de la que dependen otras posteriores no canceladas."""
    ordenados = sorted(intervalos, key=lambda i: i.desde)
    fechas = [fecha for _, fecha in cancelaciones]
    if len(set(fechas)) != len(fechas):
        raise Incumplimiento("SOLICITUD_INVALIDA", "operacion_repetida")
    for _, fecha in cancelaciones:
        if fecha <= hoy:
            raise Incumplimiento("FECHA_EFECTIVA_INVALIDA", "la_operacion_ya_es_efectiva", fecha=fecha)
    ops = operaciones_programadas(ordenados, hoy)
    elegidas: dict[date, OperacionProgramada] = {}
    for tipo, fecha in cancelaciones:
        if tipo not in TIPOS:
            raise Incumplimiento("SOLICITUD_INVALIDA", "tipo_no_valido")
        encontrada = next((o for o in ops if o.fecha == fecha), None)
        if encontrada is None:
            raise Incumplimiento("RECURSO_NO_DISPONIBLE", "operacion_no_encontrada", fecha=fecha)
        if encontrada.tipo != tipo:
            raise Incumplimiento("SOLICITUD_INVALIDA", "tipo_no_coincide", fecha=fecha, tipo_real=encontrada.tipo)
        elegidas[fecha] = encontrada
    if not elegidas:
        return list(ordenados), []

    # Solo se cancela un SUFIJO de las operaciones programadas: todas las posteriores a la primera elegida también (S-13).
    primera = min(k for k, o in enumerate(ops) if o.fecha in elegidas)
    sufijo = ops[primera:]
    if {o.fecha for o in sufijo} != set(elegidas):
        raise Incumplimiento("PERTENENCIA_INVALIDA", "hay_operaciones_posteriores_que_dependen_de_ella")

    resultado = list(ordenados)
    transiciones = [o for o in sufijo if o.tipo != "finalizacion"]
    finalizacion = next((o for o in sufijo if o.tipo == "finalizacion"), None)
    detalle: list[OperacionCancelada] = []

    if finalizacion is not None:
        ultimo = ordenados[-1]
        # Si el último intervalo también se retira, no hay fin que restituir: se retira entero con su fin.
        retirado_tambien = bool(transiciones) and transiciones[-1].indice == len(ordenados) - 1
        detalle.append(OperacionCancelada("finalizacion", finalizacion.fecha, (),
                                          None if retirado_tambien else (ultimo.id, ultimo.hasta, None)))
        resultado[-1] = replace(ultimo, hasta=None)

    if transiciones:
        inicio = transiciones[0].indice
        anterior = ordenados[inicio - 1] if inicio > 0 else None
        for k, op in enumerate(transiciones):
            restituido = (anterior.id, anterior.hasta, None) if (k == 0 and anterior is not None) else None
            detalle.append(OperacionCancelada(op.tipo, op.fecha, (ordenados[op.indice],), restituido))
        resultado = resultado[:inicio]
        if anterior is not None:
            resultado[-1] = replace(resultado[-1], hasta=None)

    detalle.sort(key=lambda d: d.fecha)
    return resultado, detalle


def aplicar_cambio(intervalos: Sequence[Intervalo], hoy: date, equipo: Hashable, rol: str, fecha: date) -> list[Intervalo]:
    """Un traslado o cambio de rol con efecto ``fecha`` sobre el último intervalo, que debe seguir sin fin (M1-05)."""
    ordenados = sorted(intervalos, key=lambda i: i.desde)
    if not ordenados:
        raise Incumplimiento("PERTENENCIA_INVALIDA", "sin_pertenencia")
    ultimo = ordenados[-1]
    if fecha <= hoy:
        raise Incumplimiento("FECHA_EFECTIVA_INVALIDA", "fecha_efectiva_no_posterior_a_hoy")
    if ultimo.hasta is not None:
        raise Incumplimiento("PERTENENCIA_INVALIDA", "pertenencia_finalizada")
    if fecha <= ultimo.desde:
        raise Incumplimiento("PERTENENCIA_INVALIDA", "fecha_no_posterior_al_inicio_de_la_ultima_pertenencia")
    if ultimo.equipo == equipo and ultimo.rol == rol:
        raise Incumplimiento("PERTENENCIA_INVALIDA", "sin_cambio")
    return [*ordenados[:-1], replace(ultimo, hasta=fecha), Intervalo(None, equipo, rol, fecha, None)]


def aplicar_finalizacion(intervalos: Sequence[Intervalo], hoy: date, fecha: date) -> list[Intervalo]:
    """La finalización con efecto ``fecha``: cierra el último intervalo sin fin y no crea otro (IR-31, CA-258)."""
    ordenados = sorted(intervalos, key=lambda i: i.desde)
    if not ordenados:
        raise Incumplimiento("PERTENENCIA_INVALIDA", "sin_pertenencia")
    ultimo = ordenados[-1]
    if fecha <= hoy:
        raise Incumplimiento("FECHA_EFECTIVA_INVALIDA", "fecha_efectiva_no_posterior_a_hoy")
    if ultimo.hasta is not None:
        raise Incumplimiento("PERTENENCIA_INVALIDA", "pertenencia_finalizada")
    if fecha <= ultimo.desde:
        raise Incumplimiento("PERTENENCIA_INVALIDA", "fecha_no_posterior_al_inicio_de_la_ultima_pertenencia")
    return [*ordenados[:-1], replace(ultimo, hasta=fecha)]
