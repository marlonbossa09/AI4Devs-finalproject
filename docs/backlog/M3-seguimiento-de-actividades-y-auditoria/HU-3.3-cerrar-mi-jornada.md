# HU-3.3 — Cerrar mi jornada

| | |
|---|---|
| **Módulo** | M3 — Seguimiento de actividades y auditoría |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-10, RN-21, RN-22, RN-46, RN-23, RN-109 |
| **Requisitos** | RF-17, RF-18, RF-19, RF-44, RF-68, RF-119 |
| **Dependencias** | HU-2.1, HU-2.8 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero cerrar manualmente mi jornada, para dejarla consolidada sin perder el seguimiento de lo no terminado.

## Criterios de aceptación

- **CA-89** · límite · RF-17 — DADO una jornada que cumple las condiciones de cierre CUANDO pasa el tiempo sin que yo la cierre ENTONCES permanece abierta.
- **CA-90** · positivo · RF-18 — DADO una jornada con al menos una actividad creada en ella y un resumen con texto CUANDO la cierro ENTONCES queda cerrada.
- **CA-91** · positivo · RF-18 — DADO una jornada con una actividad continuada (con al menos un avance de esa fecha laboral) y un resumen con texto CUANDO la cierro ENTONCES queda cerrada.
- **CA-92** · negativo · RF-18 — DADO una jornada sin ninguna actividad creada ni continuada CUANDO intento cerrarla ENTONCES no se permite.
- **CA-93** · negativo · RF-18 — DADO una jornada con el resumen vacío CUANDO intento cerrarla ENTONCES no se permite.
- **CA-94** · límite · RF-18 — DADO una jornada con el resumen formado solo por espacios CUANDO intento cerrarla ENTONCES no se permite.
- **CA-95** · positivo · RF-19 — DADO una jornada con actividades en los cuatro estados CUANDO la cierro ENTONCES se cierra y cada actividad conserva su estado.
- **CA-96** · positivo · RF-44 — DADO una actividad En progreso en una jornada cerrada CUANDO llega una jornada posterior ENTONCES puedo registrarle un avance y no se ha creado una copia.
- **CA-97** · negativo · RF-68 — DADO una jornada con fecha laboral posterior a la actual CUANDO intento cerrarla ENTONCES no se permite.
- **CA-98** · permisos · RF-17 — DADO la jornada de otra persona CUANDO intento cerrarla ENTONCES no es posible.
- **CA-283** · negativo · RF-119 — DADO una jornada cuya única actividad creada o continuada está marcada como registrada por error CUANDO intento cerrarla ENTONCES no se permite.
- Las actividades marcadas como registradas por error no cuentan para las condiciones de cierre (RN-109).
