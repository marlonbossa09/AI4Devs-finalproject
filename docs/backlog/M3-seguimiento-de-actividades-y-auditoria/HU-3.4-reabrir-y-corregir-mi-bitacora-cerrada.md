# HU-3.4 — Reabrir y corregir mi bitácora cerrada

| | |
|---|---|
| **Módulo** | M3 — Seguimiento de actividades y auditoría |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-01, RN-19, RN-23, RN-50, RN-67, RN-103, RN-108 |
| **Requisitos** | RF-20, RF-71, RF-21, RNF-02, RF-113, RF-118 |
| **Dependencias** | HU-3.3 |
| **Decisiones pendientes** | PA-04 (cómo corregir la bitácora de una persona que no puede acceder; no afecta a los criterios de esta historia) |

## Historia

Como colaborador o supervisor, quiero reabrir y corregir mis bitácoras cerradas, para corregir errores sin perder trazabilidad.

## Criterios de aceptación

- **CA-99** · positivo · RF-20 — DADO una bitácora cerrada mía CUANDO la reabro indicando un motivo ENTONCES puedo corregirla.
- **CA-100** · negativo · RF-71 — DADO una bitácora cerrada mía CUANDO intento reabrirla sin indicar un motivo ENTONCES no se permite.
- **CA-101** · permisos · RF-20 — DADO la bitácora cerrada de otra persona CUANDO intento reabrirla o corregirla ENTONCES no es posible, tampoco para un supervisor.
- **CA-102** · positivo · RF-21 — DADO que reabrí mi bitácora cerrada CUANDO la corrijo ENTONCES existe constancia de auditoría de la reapertura y de la corrección.
- **CA-103** · límite · RF-21 — DADO la corrección del estado de un avance ya registrado CUANDO la aplico ENTONCES no se reescribe silenciosamente: queda auditada.
- **CA-104** · límite · RNF-02 — DADO varias correcciones sucesivas sobre una misma bitácora cerrada CUANDO se consulta la auditoría ENTONCES permite reconstruir cada una de ellas.
- **CA-266** · límite · RF-113 — DADO una bitácora cerrada, reabierta y cerrada de nuevo CUANDO se consulta la auditoría ENTONCES se reconstruye cada ciclo de cierre y reapertura.
- **CA-284** · negativo · RF-118 — DADO una bitácora cerrada mía CUANDO intento registrar o corregir contenido en esa jornada sin reabrirla antes ENTONCES no se permite.

## Notas

- Los criterios sobre el recálculo del estado actual tras una corrección están en HU-2.9.
- Los ciclos de cierre y reapertura se reconstruyen desde la auditoría (RN-103).
- Continuar una actividad en una jornada abierta posterior no obliga a reabrir las jornadas cerradas anteriores (RN-108; CA-96).
