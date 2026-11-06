# HU-3.7 — Corregir una actividad registrada por error

| | |
|---|---|
| **Módulo** | M3 — Seguimiento de actividades y auditoría |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-59, RN-60, RN-23, RN-101, RN-109, RN-113 |
| **Requisitos** | RF-77, RF-78, RF-79, RF-111, RF-119, RF-123 |
| **Dependencias** | HU-2.2, HU-3.6 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero marcar como registrada por error una actividad creada por equivocación, sin perder su historial, para mantener limpias mis vistas y recuentos.

## Criterios de aceptación

- **CA-115** · positivo · RF-77 — DADO una actividad mía sin avances en jornadas posteriores a su creación CUANDO la marco como registrada por error indicando un motivo ENTONCES queda marcada.
- **CA-116** · negativo · RF-77 — DADO una actividad mía CUANDO intento marcarla como registrada por error sin indicar un motivo ENTONCES no se permite.
- **CA-117** · negativo · RF-77 — DADO una actividad con avances en jornadas posteriores a su creación CUANDO intento marcarla como registrada por error ENTONCES no se permite.
- **CA-118** · permisos · RF-77 — DADO una actividad de otra persona CUANDO intento marcarla como registrada por error ENTONCES no es posible.
- **CA-119** · positivo · RF-78 — DADO una actividad marcada como registrada por error CUANDO se consultan las vistas operativas y los recuentos ordinarios ENTONCES no aparece en ellos.
- **CA-120** · positivo · RF-78 — DADO una actividad marcada como registrada por error CUANDO una persona autorizada consulta el historial o la auditoría ENTONCES permanece consultable.
- **CA-121** · límite · RF-78 — DADO una actividad marcada como registrada por error CUANDO se consulta ENTONCES no se ha borrado y su estado sigue siendo uno de los cuatro.
- **CA-122** · positivo · RF-79 — DADO una actividad marcada como registrada por error CUANDO su propietario revierte la marca ENTONCES vuelve a las vistas operativas y a los recuentos, y consta una entrada de auditoría.
- **CA-123** · permisos · RF-79 — DADO una actividad marcada por error de otra persona CUANDO intento revertir la marca ENTONCES no es posible.
- **CA-268** · permisos · RF-111 — DADO una actividad iniciada en un equipo T y marcada como registrada por error CUANDO la consulta el supervisor de otro equipo U ENTONCES no se muestra la actividad ni el motivo de la marca.
- **CA-287** · positivo · RF-119 — DADO una jornada cerrada con dos actividades válidas creadas en ella CUANDO marco una como registrada por error ENTONCES se acepta, la jornada sigue cerrada y no hace falta reabrirla.
- **CA-288** · negativo · RF-119 — DADO una jornada cerrada cuya única actividad válida es una creada en ella CUANDO intento marcarla como registrada por error ENTONCES se rechaza y ningún registro cambia.
- **CA-289** · positivo · RF-119 — DADO una jornada cerrada con una actividad creada en ella y otra iniciada en una jornada anterior con un avance de esa fecha laboral CUANDO marco como registrada por error la actividad creada en ella ENTONCES se acepta, porque la jornada conserva una actividad válida continuada.
- **CA-290** · límite · RF-119 — DADO una jornada cerrada con una actividad marcada por error CUANDO revierto la marca ENTONCES la jornada sigue cerrada, la reversión consta en la auditoría y la actividad vuelve a contar para las condiciones de cierre.
- **CA-297** · negativo · RF-123 — DADO una actividad marcada como registrada por error CUANDO intento corregir uno de sus avances ENTONCES no se permite mientras la marca esté vigente.
- **CA-298** · positivo · RF-123 — DADO una actividad cuya marca de error he revertido CUANDO corrijo uno de sus avances conforme a las reglas de corrección ENTONCES se permite.
- La marca de error y su motivo no se exponen a equipos sin autorización sobre la jornada de origen de la actividad (RN-101).
- Marcar o revertir una marca es un cambio de validez de la actividad, no una corrección del contenido de la bitácora: no obliga a reabrir la jornada, se audita y valida la integridad de los registros relacionados (RN-109).
- Para corregir los avances de una actividad marcada, primero se revierte la marca (RN-113).
