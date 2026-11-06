# HU-2.5 — Bloquear una actividad con motivo

| | |
|---|---|
| **Módulo** | M2 — Bitácoras laborales híbridas |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-24 |
| **Requisitos** | RF-41 |
| **Dependencias** | HU-2.8 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero indicar el motivo cuando una actividad queda bloqueada, para que se sepa qué impide avanzar.

## Criterios de aceptación

- **CA-49** · negativo · RF-41 — DADO una actividad CUANDO intento marcarla Bloqueada sin indicar un motivo ENTONCES no se permite.
- **CA-50** · positivo · RF-41 — DADO una actividad CUANDO la marco Bloqueada indicando un motivo ENTONCES se permite.
- **CA-51** · positivo · RF-41 — DADO una actividad que marqué Bloqueada con motivo CUANDO consulto el avance correspondiente ENTONCES consta el motivo.
- **CA-52** · límite · RF-41 — DADO una actividad que estuvo Bloqueada CUANDO pasa a otro estado ENTONCES el motivo anterior sigue constando en el historial.
