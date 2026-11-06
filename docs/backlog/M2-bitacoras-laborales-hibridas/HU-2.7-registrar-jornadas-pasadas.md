# HU-2.7 — Registrar jornadas pasadas

| | |
|---|---|
| **Módulo** | M2 — Bitácoras laborales híbridas |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-14, RN-18, RN-05, RN-44, RN-94 |
| **Requisitos** | RF-10, RF-11, RF-58, RNF-03, RF-104 |
| **Dependencias** | HU-2.1 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero registrar o completar una jornada pasada, para no perder información por un olvido.

## Criterios de aceptación

- **CA-59** · positivo · RF-11 — DADO una fecha laboral anterior a la actual CUANDO registro esa jornada ENTONCES se acepta sin un límite fijo de días.
- **CA-60** · límite · RF-11 — DADO una jornada de hace varios meses CUANDO la registro ENTONCES no se rechaza por su antigüedad.
- **CA-61** · positivo · RF-10 — DADO un registro creado hoy para una jornada pasada CUANDO se consulta ENTONCES muestra por separado la fecha laboral y la fecha real de registro.
- **CA-62** · positivo · RF-10 — DADO un registro modificado posteriormente CUANDO se consulta ENTONCES muestra además la fecha de modificación.
- **CA-63** · positivo · RF-58 — DADO una organización con una zona horaria configurada CUANDO dos personas registran en el mismo instante ENTONCES obtienen la misma fecha laboral actual, con independencia de dónde estén.
- **CA-64** · límite · RF-58 — DADO un día festivo CUANDO registro mi jornada ENTONCES el registro no se restringe.
- **CA-65** · límite · RNF-03 — DADO un registro corregido posteriormente CUANDO lo consulto ENTONCES las tres fechas siguen siendo consultables y el cambio consta en la auditoría.
- **CA-264** · negativo · RF-104 — DADO una persona cuya primera pertenencia empieza el día D CUANDO intenta registrar una bitácora con fecha anterior a D ENTONCES no se permite.

## Notas

- La modificación de una jornada pasada se audita (HU-3.5).
- No se admiten bitácoras anteriores a la primera pertenencia ni fuera del período de actividad de la persona (RN-94).
