"""Reglas de la línea temporal de supervisión de un equipo (IR-03, IR-32). Funciones puras, sin acceso a la base.

Una pertenencia nueva de la provisión inicial es SIEMPRE de duración indefinida desde ``desde`` (no hay altas con fin ni
históricas, RN-106), así que basta comparar con los intervalos de supervisor del equipo: ``[desde, hasta_exclusivo)``, con
``hasta_exclusivo`` vacío si no tiene fin.

Los traslados y cambios de rol (M1-T3) validan además la línea temporal RESULTANTE completa, de una persona (IR-02, IR-28:
sin solapes ni huecos) y de un equipo (IR-03 e IR-32: como máximo un supervisor y exactamente uno mientras haya
colaboradores), con ``primera_irregularidad_de_persona`` y ``primera_violacion_de_supervision``. Las finalizaciones
(M1-T4) reutilizarán estas mismas funciones.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Hashable


@dataclass(frozen=True)
class IntervaloDeSupervisor:
    desde: date
    hasta_exclusivo: date | None


@dataclass(frozen=True)
class Tramo:
    """Un intervalo de pertenencia ``[desde, hasta_exclusivo)``: de quién, en qué rol. ``hasta_exclusivo`` vacío = sin fin."""

    persona_id: Hashable
    rol: str
    desde: date
    hasta_exclusivo: date | None

    def cubre(self, fecha: date) -> bool:
        return self.desde <= fecha and (self.hasta_exclusivo is None or fecha < self.hasta_exclusivo)


@dataclass(frozen=True)
class ViolacionDeSupervision:
    fecha: date
    motivo: str  # ``sin_supervisor`` (IR-32) o ``mas_de_un_supervisor`` (IR-03)


def primera_violacion_de_supervision(tramos: Sequence[Tramo], desde: date) -> ViolacionDeSupervision | None:
    """IR-03 e IR-32 sobre la línea temporal COMPLETA de un equipo, desde ``desde`` hasta el fin de los tiempos: en cada fecha
    hay como máximo un supervisor, y exactamente uno si hay algún colaborador. El estado de un equipo solo cambia en el
    ``desde`` o el ``hasta_exclusivo`` de algún tramo, así que basta comprobar ``desde`` y cada una de esas fechas posteriores
    (después de la última el estado es constante). Devuelve la primera fecha que incumple, o ``None``."""
    fechas = {desde}
    for t in tramos:
        if t.desde > desde:
            fechas.add(t.desde)
        if t.hasta_exclusivo is not None and t.hasta_exclusivo > desde:
            fechas.add(t.hasta_exclusivo)
    for fecha in sorted(fechas):
        supervisores = sum(1 for t in tramos if t.rol == "supervisor" and t.cubre(fecha))
        colaboradores = sum(1 for t in tramos if t.rol == "colaborador" and t.cubre(fecha))
        if supervisores > 1:
            return ViolacionDeSupervision(fecha, "mas_de_un_supervisor")
        if colaboradores > 0 and supervisores == 0:
            return ViolacionDeSupervision(fecha, "sin_supervisor")
    return None


@dataclass(frozen=True)
class SupervisionEnUnaFecha:
    """Estado de la supervisión de un equipo en una fecha (DM-09, RA-12)."""

    colaboradores: int
    supervisor: Hashable | None   # el supervisor ASIGNADO en esa fecha (IR-03: como máximo uno)
    pendiente: bool               # hay colaboradores y el supervisor asignado no tiene acceso efectivo (o no hay supervisor)


def supervision_en(tramos: Sequence[Tramo], fecha: date, sin_acceso: frozenset | set = frozenset()) -> SupervisionEnUnaFecha:
    """Supervisión efectiva de un equipo en ``fecha`` (DM-09 y RA-12). «Equipo pendiente de supervisión efectiva»: tiene colaboradores en
    la fecha y su supervisor asignado en ella no tiene acceso efectivo (``sin_acceso``: personas con el acceso desactivado). Un equipo
    sin colaboradores está en provisión y no está pendiente (IR-32). Es una condición DERIVADA: no se almacena (DD-04)."""
    colaboradores = sum(1 for t in tramos if t.rol == "colaborador" and t.cubre(fecha))
    supervisores = [t.persona_id for t in tramos if t.rol == "supervisor" and t.cubre(fecha)]
    supervisor = supervisores[0] if supervisores else None
    pendiente = colaboradores > 0 and (supervisor is None or supervisor in sin_acceso)
    return SupervisionEnUnaFecha(colaboradores, supervisor, pendiente)


def primera_irregularidad_de_persona(tramos: Sequence[Tramo]) -> str | None:
    """IR-02 e IR-28 sobre la línea temporal COMPLETA de una persona: cada fecha cubierta por exactamente un intervalo, sin
    solapes ni huecos, y solo el último puede carecer de fin. Hoy ninguna orden crea una inactividad (la reincorporación no
    existe, PA-24), así que cualquier hueco es una irregularidad. Devuelve ``solape``, ``hueco``, ``intervalo_invalido`` o ``None``."""
    ordenados = sorted(tramos, key=lambda t: t.desde)
    for t in ordenados:
        if t.hasta_exclusivo is not None and t.hasta_exclusivo <= t.desde:
            return "intervalo_invalido"
    for anterior, siguiente in zip(ordenados, ordenados[1:]):
        if anterior.hasta_exclusivo is None or anterior.hasta_exclusivo > siguiente.desde:
            return "solape"
        if anterior.hasta_exclusivo < siguiente.desde:
            return "hueco"
    return None


def solapa_con_supervisor(supervisores: list[IntervaloDeSupervisor], desde: date) -> bool:
    """IR-03: ¿algún supervisor del equipo cubre alguna fecha de ``[desde, fin de los tiempos)``?"""
    return any(s.hasta_exclusivo is None or s.hasta_exclusivo > desde for s in supervisores)


def supervision_cubre_desde(supervisores: list[IntervaloDeSupervisor], desde: date) -> bool:
    """IR-32: ¿el equipo tiene un supervisor en CADA fecha de ``[desde, fin de los tiempos)``? Un colaborador que empieza
    en ``desde`` y no termina exige supervisión sin huecos y sin fin desde esa fecha."""
    cursor = desde
    for s in sorted(supervisores, key=lambda s: s.desde):
        if s.desde <= cursor and (s.hasta_exclusivo is None or cursor < s.hasta_exclusivo):
            if s.hasta_exclusivo is None:
                return True
            cursor = s.hasta_exclusivo
    return False
