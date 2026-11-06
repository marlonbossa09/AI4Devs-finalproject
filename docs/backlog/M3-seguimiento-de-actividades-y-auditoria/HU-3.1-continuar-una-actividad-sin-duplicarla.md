# HU-3.1 — Continuar una actividad sin duplicarla

| | |
|---|---|
| **Módulo** | M3 — Seguimiento de actividades y auditoría |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-04, RN-09, RN-32, RN-62, RN-104 |
| **Requisitos** | RF-13, RF-14, RF-15, RF-16, RF-114 |
| **Dependencias** | HU-2.8, HU-3.2 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero continuar una actividad en jornadas posteriores, para mantener su seguimiento sin duplicarla.

## Criterios de aceptación

- **CA-81** · positivo · RF-15 — DADO una actividad existente mía CUANDO registro un avance en una jornada posterior ENTONCES no se crea otra actividad y la actividad incluye el nuevo avance.
- **CA-82** · positivo · RF-13 — DADO una actividad con avances en tres jornadas distintas CUANDO se cuentan las actividades ENTONCES sigue existiendo una única actividad.
- **CA-83** · positivo · RF-14 — DADO una actividad con avances en tres fechas laborales CUANDO la consulto ENTONCES muestra los tres avances, cada uno con su fecha laboral.
- **CA-84** · positivo · RF-16 — DADO una actividad con avances CUANDO la consulto ENTONCES veo cada avance con su fecha laboral y el estado que tenía.
- **CA-85** · límite · RF-13 — DADO dos actividades distintas con el mismo título o con títulos similares CUANDO el sistema las procesa ENTONCES no las trata como una misma actividad ni como una duplicación por esa sola razón.
- **CA-265** · límite · RF-114 — DADO una actividad continuada en varias jornadas CUANDO se consulta ENTONCES su título es el mismo en todas ellas.
- El título de una actividad no se edita en el flujo ordinario (RN-104). La propuesta PP-45 no está aprobada.
