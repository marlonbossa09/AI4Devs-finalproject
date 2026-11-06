# HU-2.2 — Planificar mis actividades

| | |
|---|---|
| **Módulo** | M2 — Bitácoras laborales híbridas |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-07, RN-08, RN-20, RN-43, RN-71, RN-104, RN-112 |
| **Requisitos** | RF-06, RF-07, RF-38, RF-63, RF-81, RF-114, RF-122 |
| **Dependencias** | HU-2.1 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero registrar lo que tengo previsto hacer en mi jornada, para distinguir después lo previsto de lo realizado.

## Criterios de aceptación

- **CA-37** · positivo · RF-06 — DADO mi bitácora de una jornada CUANDO registro una actividad prevista ENTONCES aparece en la bitácora de esa jornada.
- **CA-38** · positivo · RF-07 — DADO una actividad recién planificada CUANDO se consulta su estado ENTONCES es Pendiente.
- **CA-39** · positivo · RF-38 — DADO una actividad planificada CUANDO después actualizo lo realizado ENTONCES sigue siendo posible consultar lo que se había previsto originalmente.
- **CA-40** · positivo · RF-81 — DADO una actividad recién planificada y sin avances CUANDO se consulta ENTONCES la planificación no constituye un avance de ejecución y se distingue de los registros de avance y del estado actual.
- **CA-41** · negativo · RF-63 — DADO una actividad con propietario CUANDO se intenta asignarle un segundo propietario ENTONCES no es posible.
- **CA-263** · límite · RF-114 — DADO una planificación original registrada CUANDO la actividad recibe avances posteriores ENTONCES la planificación original conserva su contenido sin cambios.
- **CA-295** · negativo · RF-122 — DADO mi bitácora CUANDO intento planificar una actividad con el título vacío o formado solo por espacios ENTONCES no se permite.
- Para el MVP la planificación original no se edita en el flujo ordinario (RN-104). La propuesta PP-43 de versionar la planificación no está aprobada.
- El título de una actividad es obligatorio (RN-112).
