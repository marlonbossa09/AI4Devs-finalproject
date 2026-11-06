# HU-2.4 — Registrar avances conservando el estado histórico

| | |
|---|---|
| **Módulo** | M2 — Bitácoras laborales híbridas |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-08, RN-17 |
| **Requisitos** | RF-08, RF-40 |
| **Dependencias** | HU-2.2, HU-2.8 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero que cada avance conserve el estado que tenía mi actividad en ese momento, para que el historial de la actividad no cambie cuando cambia su estado actual.

## Criterios de aceptación

- **CA-45** · positivo · RF-40 — DADO una actividad mía CUANDO registro un avance en una jornada ENTONCES el avance conserva el estado que tenía la actividad en ese momento.
- **CA-46** · positivo · RF-40 — DADO una actividad con avances anteriores CUANDO su estado actual cambia ENTONCES los avances anteriores siguen mostrando el estado que tenían.
- **CA-47** · límite · RF-08 — DADO cualquier actividad CUANDO se consulta su estado ENTONCES es uno de estos cuatro: Pendiente, En progreso, Bloqueada o Completada.
- **CA-48** · negativo · RF-08 — DADO una actividad CUANDO intento asignarle un valor que no es uno de los cuatro estados ENTONCES no se acepta.
