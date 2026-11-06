# HU-2.9 — Estado actual y orden de los avances

| | |
|---|---|
| **Módulo** | M2 — Bitácoras laborales híbridas (con efecto en M3) |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-42, RN-65, RN-66, RN-67, RN-71, RN-75 |
| **Requisitos** | RF-61, RF-62, RF-82, RF-85 |
| **Dependencias** | HU-2.8, HU-2.3 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador o supervisor, quiero que el estado actual de una actividad se determine de forma consistente con la secuencia de sus avances de ejecución, para confiar en lo que veo.

## Criterios de aceptación

- **CA-73** · positivo · RF-61 — DADO una actividad planificada sin avances CUANDO se consulta su estado actual ENTONCES es Pendiente.
- **CA-74** · positivo · RF-62 — DADO dos avances de una actividad con distinta fecha laboral CUANDO se ordena la secuencia ENTONCES el de fecha laboral posterior es posterior, con independencia del momento en que se registraron.
- **CA-75** · límite · RF-62 — DADO dos avances de la misma fecha laboral registrados en momentos distintos CUANDO se ordena la secuencia ENTONCES el registrado después es posterior.
- **CA-76** · límite · RF-62 — DADO dos avances con la misma fecha laboral y el mismo momento de registro CUANDO se ordena la secuencia ENTONCES el orden lo determina un identificador estable y es siempre el mismo.
- **CA-77** · positivo · RF-61 — DADO una actividad con avances CUANDO se consulta su estado actual ENTONCES es el del último avance de la secuencia.
- **CA-78** · límite · RF-61 — DADO una actividad con un avance En progreso con fecha laboral del martes CUANDO se registra después un avance Completada con fecha laboral del lunes ENTONCES el estado actual sigue siendo En progreso.
- **CA-79** · positivo · RF-82 — DADO una corrección que cambia el estado del último avance de una actividad CUANDO se aplica ENTONCES el estado actual se recalcula y la corrección queda auditada.
- **CA-80** · límite · RF-82 — DADO una corrección que cambia el estado de un avance que no es el último CUANDO se aplica ENTONCES el estado actual no cambia y la corrección queda auditada.
- **CA-185** · límite · RF-85 — DADO una actividad con avances de ejecución y una continuación planificada para una fecha futura CUANDO se consulta su estado actual ENTONCES es el del último avance de ejecución, sin que la continuación planificada intervenga.
- **CA-186** · positivo · RF-61 — DADO una actividad planificada con una continuación planificada y sin avances de ejecución CUANDO se consulta su estado actual ENTONCES es Pendiente.

## Notas

- Solo los avances de ejecución forman la secuencia y determinan el estado actual. La planificación, incluida la futura, no participa (RN-71, RN-75).
