# HU-3.2 — Seleccionar la actividad que se continúa

| | |
|---|---|
| **Módulo** | M3 — Seguimiento de actividades y auditoría |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-39, RN-43 |
| **Requisitos** | RF-64 |
| **Dependencias** | HU-2.8 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero indicar de forma explícita sobre qué actividad propia existente registro un avance, para continuarla sin crear otra.

## Criterios de aceptación

- **CA-86** · positivo · RF-64 — DADO que registro un avance en una jornada posterior CUANDO selecciono explícitamente una actividad propia existente ENTONCES el avance se asocia a esa actividad.
- **CA-87** · negativo · RF-64 — DADO un avance en una jornada posterior CUANDO no selecciono ninguna actividad existente ENTONCES el sistema no lo asocia por su cuenta a una actividad por la similitud de su título.
- **CA-88** · permisos · RF-64 — DADO actividades de otra persona CUANDO intento seleccionarlas para continuarlas ENTONCES no puedo.
