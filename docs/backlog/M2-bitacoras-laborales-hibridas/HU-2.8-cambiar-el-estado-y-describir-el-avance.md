# HU-2.8 — Cambiar el estado de una actividad y describir el avance

| | |
|---|---|
| **Módulo** | M2 — Bitácoras laborales híbridas |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-07, RN-08, RN-40, RN-41, RN-70, RN-23 |
| **Requisitos** | RF-09, RF-59, RF-60, RF-25 |
| **Dependencias** | HU-2.2, HU-2.4 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero registrar avances y cambiar el estado de mis actividades, describiendo el trabajo realizado, para dejar constancia de lo realizado.

## Criterios de aceptación

- **CA-66** · positivo · RF-09 — DADO una actividad mía no completada CUANDO registro un avance ENTONCES la actividad lo refleja y el avance queda asociado a la fecha laboral de la jornada.
- **CA-67** · positivo · RF-09 — DADO una actividad mía no completada CUANDO cambio su estado a otro de los cuatro estados ENTONCES el nuevo estado queda registrado en el avance.
- **CA-68** · negativo · RF-59 — DADO un avance CUANDO intento registrarlo sin descripción ENTONCES no se permite.
- **CA-69** · límite · RF-59 — DADO un avance CUANDO intento registrarlo con una descripción formada solo por espacios ENTONCES no se permite.
- **CA-70** · positivo · RF-59 — DADO un avance registrado CUANDO se consulta ENTONCES muestra su fecha laboral, el estado que tenía la actividad entonces y su descripción.
- **CA-71** · positivo · RF-60 — DADO una actividad CUANDO registro dos avances en la misma fecha laboral ENTONCES ambos constan.
- **CA-72** · permisos · RF-25 — DADO una actividad de otra persona CUANDO intento registrarle un avance ENTONCES no es posible.

## Notas

- Las actividades Completadas no se tratan aquí: se reactivan mediante HU-3.8.
