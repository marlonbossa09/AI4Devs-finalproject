# HU-2.1 — Tener mi bitácora por fecha laboral

| | |
|---|---|
| **Módulo** | M2 — Bitácoras laborales híbridas |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-11, RN-16, RN-23, RN-107 |
| **Requisitos** | RF-04, RF-05, RF-12, RF-25, RF-117 |
| **Dependencias** | HU-1.1 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador o supervisor, quiero disponer de mi propia bitácora por cada fecha laboral, para registrar mi jornada.

## Criterios de aceptación

- **CA-32** · positivo · RF-04 — DADO una persona identificada, sea colaborador o supervisor CUANDO registra su jornada de una fecha laboral ENTONCES lo hace en su propia bitácora de esa fecha.
- **CA-33** · límite · RF-12 — DADO una persona con bitácora para una fecha laboral CUANDO vuelve a registrar esa misma fecha ENTONCES no existe una segunda bitácora suya para esa fecha.
- **CA-34** · positivo · RF-05 — DADO una bitácora CUANDO la persona la completa ENTONCES puede incluir actividades estructuradas y un resumen libre de texto.
- **CA-35** · positivo · RF-04 — DADO un supervisor y un colaborador CUANDO cada uno registra su jornada del mismo día ENTONCES cada uno dispone de su propia bitácora.
- **CA-36** · permisos · RF-25 — DADO la bitácora de otra persona CUANDO intento registrar en ella ENTONCES no es posible.
- **CA-280** · positivo · RF-117 — DADO una bitácora existente mía de una fecha laboral CUANDO la abro de nuevo ENTONCES se devuelve la misma bitácora, sin cambios y sin una segunda bitácora.
- **CA-281** · positivo · RF-117 — DADO una fecha laboral sin bitácora mía CUANDO registro por primera vez contenido en ella ENTONCES se crea mi única bitácora de esa fecha.
- **CA-282** · negativo · RF-117 — DADO una fecha laboral sin bitácora mía CUANDO la consulto ENTONCES no se crea ninguna bitácora.
- La bitácora se abre de forma explícita o implícita, y siempre hay una sola por persona y fecha (RN-107).
