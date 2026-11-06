# HU-2.3 — Planificar jornadas futuras

| | |
|---|---|
| **Módulo** | M2 — Bitácoras laborales híbridas |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-27, RN-46, RN-75, RN-76, RN-78, RN-21, RN-23 |
| **Requisitos** | RF-42, RF-43, RF-84, RF-85, RF-89, RF-18 |
| **Dependencias** | HU-2.2 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero planificar actividades nuevas y la continuación de mis actividades existentes para jornadas futuras, para organizar mi trabajo con antelación.

## Criterios de aceptación

- **CA-42** · positivo · RF-42 — DADO una jornada con fecha laboral posterior a la actual CUANDO registro una actividad prevista en estado Pendiente ENTONCES se acepta.
- **CA-43** · negativo · RF-43 — DADO una jornada con fecha laboral posterior a la actual CUANDO intento registrar un estado distinto de Pendiente ENTONCES no se acepta.
- **CA-44** · límite · RF-43 — DADO la jornada de la fecha actual CUANDO registro una actividad en cualquiera de los cuatro estados ENTONCES se acepta, porque la restricción solo afecta a fechas laborales futuras.
- **CA-179** · positivo · RF-84 — DADO una actividad propia existente y no completada CUANDO planifico su continuación para una jornada con fecha laboral posterior a la actual ENTONCES queda registrada la continuación planificada y no se crea otra actividad.
- **CA-180** · positivo · RF-85 — DADO una actividad propia con estado actual En progreso CUANDO planifico su continuación para una jornada futura ENTONCES su estado actual sigue siendo En progreso.
- **CA-181** · límite · RF-85 — DADO una continuación planificada CUANDO se consulta la secuencia de avances de la actividad o se calcula su estado actual ENTONCES no aparece en la secuencia, no es un avance de ejecución y no participa en el cálculo.
- **CA-182** · negativo · RF-43 — DADO una actividad existente CUANDO intento registrar sobre ella un avance de ejecución en una jornada con fecha laboral futura ENTONCES no se acepta.
- **CA-183** · permisos · RF-84 — DADO una actividad de otra persona CUANDO intento planificar su continuación ENTONCES no es posible.
- **CA-184** · límite · RF-18 — DADO una jornada que solo contiene continuaciones planificadas, sin actividades creadas en ella ni avances de ejecución CUANDO intento cerrarla ENTONCES no se permite, porque una continuación planificada no cuenta como actividad continuada.
- **CA-209** · negativo · RF-89 — DADO una actividad Completada CUANDO intento planificar su continuación para una jornada con fecha laboral futura sin reactivarla antes ENTONCES no se permite.
- **CA-210** · positivo · RF-89 — DADO una actividad Completada que he reactivado CUANDO planifico su continuación para una jornada con fecha laboral futura ENTONCES se permite y no se crea otra actividad.
