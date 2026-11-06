# HU-1.4 — Visibilidad histórica de los registros tras un cambio de equipo

| | |
|---|---|
| **Módulo** | M1 — Autenticación, usuarios y equipos (con efecto en M4 y M5) |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-36, RN-12, RN-63, RN-23, RN-81, RN-82, RN-83, RN-87, RN-95 |
| **Requisitos** | RF-66, RF-83, RF-24, RF-25, RF-91, RF-92, RF-93, RF-97, RNF-01, RF-105 |
| **Dependencias** | HU-1.3, HU-2.1, HU-4.1 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero que mis registros pertenezcan históricamente al equipo en el que estaba en cada fecha, para que un cambio de equipo no exponga todo mi historial al equipo nuevo.

## Criterios de aceptación

En los criterios, P es una persona que perteneció al equipo T y después pasó al equipo U.

- **CA-15** · positivo · RF-66 — DADO P trasladada de T a U CUANDO un integrante autorizado de T consulta un registro de P de una fecha anterior al traslado ENTONCES puede consultarlo, aunque P ya pertenezca a U.
- **CA-16** · negativo · RF-66 — DADO P trasladada de T a U CUANDO un integrante de U intenta consultar un registro de P de una fecha anterior al traslado ENTONCES no puede consultarlo.
- **CA-17** · negativo · RF-66 — DADO P trasladada de T a U CUANDO un integrante de T intenta consultar un registro de P de una fecha posterior al traslado ENTONCES no puede consultarlo.
- **CA-18** · positivo · RF-66 — DADO P trasladada de T a U CUANDO un integrante autorizado de U consulta un registro de P de una fecha posterior al traslado ENTONCES puede consultarlo.
- **CA-19** · negativo · RF-83 — DADO P trasladada de T a U CUANDO el equipo U genera un informe o realiza una consulta que incluiría registros de P anteriores al traslado ENTONCES esos registros no se incluyen.
- **CA-20** · permisos · RF-83 — DADO P trasladada de T a U CUANDO un integrante de U intenta obtener por cualquier vía (consulta, informe o acceso directo) un registro de P anterior al traslado ENTONCES no se le entrega.
- **CA-21** · negativo · RF-24 — DADO un colaborador CUANDO intenta consultar un registro que pertenece históricamente a otro equipo ENTONCES no puede.
- **CA-176** · positivo · RF-66 — DADO P trasladada de T a U y una persona Q que se incorporó a T después del traslado CUANDO Q, integrante activo de T, consulta un registro de P de una fecha en que P pertenecía a T ENTONCES puede consultarlo, aunque se haya incorporado después.
- **CA-177** · negativo · RF-66 — DADO la misma situación CUANDO Q intenta consultar un registro de P de una fecha en que P pertenecía a U ENTONCES no puede consultarlo.
- **CA-178** · permisos · RF-25 — DADO P trasladada de T a U CUANDO un integrante de T intenta modificar por cualquier vía un registro de P ENTONCES no es posible.
- **CA-212** · positivo · RF-91 — DADO una actividad de P iniciada en T CUANDO P pasa al equipo U ENTONCES sigue siendo la misma actividad y P sigue siendo su propietaria.
- **CA-213** · positivo · RF-91 — DADO una actividad de P iniciada en T CUANDO P registra en U un avance sobre ella ENTONCES no se crea otra actividad.
- **CA-214** · positivo · RF-93 — DADO P trasladada de T a U CUANDO P consulta el historial de una actividad que inició en T ENTONCES ve todos sus avances, los de T y los de U.
- **CA-215** · negativo · RF-92 — DADO P trasladada de T a U CUANDO un integrante de U consulta una actividad de P iniciada en T ENTONCES no obtiene su título, sus descripciones, sus motivos de bloqueo ni sus bitácoras de T.
- **CA-216** · positivo · RF-97 — DADO una planificación de P para una fecha laboral posterior al traslado de T a U, registrada antes del traslado CUANDO un integrante autorizado de U la consulta ENTONCES puede consultarla, porque su fecha laboral corresponde a U.
- **CA-217** · negativo · RF-97 — DADO esa misma planificación CUANDO un integrante de T intenta consultarla ENTONCES no puede.
- **CA-249** · límite · RF-105 — DADO una persona P de un equipo T con un traslado programado a U con efecto mañana CUANDO se consulta la bitácora que P creó hoy ENTONCES sigue perteneciendo a T.

## Notas

- La regla se aplica de igual manera a consultas, vistas de supervisión e informes, y en las interfaces y los controles de autorización (RN-36, RN-86).
- Un integrante activo puede consultar los registros históricos que corresponden a su equipo aunque se haya incorporado después (PA-18, resuelto en la versión 0.7).
- Implicación de seguridad de RN-87: la planificación futura registrada antes de un traslado pasa a ser visible para el equipo nuevo y deja de serlo para el anterior; la reevaluación queda trazada en el historial de pertenencias (CA-13).
- Un traslado ordinario nunca reasigna los registros de la jornada actual (RN-95).
