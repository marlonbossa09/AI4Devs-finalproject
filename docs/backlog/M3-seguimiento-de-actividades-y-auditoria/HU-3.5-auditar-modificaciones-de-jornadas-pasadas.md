# HU-3.5 — Auditar las modificaciones de jornadas pasadas

| | |
|---|---|
| **Módulo** | M3 — Seguimiento de actividades y auditoría |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-45, RN-72, RN-19, RN-49, RN-23, RN-103, RN-111 |
| **Requisitos** | RF-21, RF-22, RF-25, RF-113, RF-121 |
| **Dependencias** | HU-2.7, HU-3.4 |
| **Decisiones pendientes** | PA-06 (retención de la auditoría; no afecta a los criterios de esta historia) |

## Historia

Como supervisor, quiero que las modificaciones de jornadas pasadas queden auditadas aunque la bitácora no se hubiera cerrado, para confiar en el histórico.

## Criterios de aceptación

Una jornada pasada es aquella cuya fecha laboral es anterior a la fecha actual en la zona horaria de la organización (RN-72).

- **CA-105** · positivo · RF-21 — DADO una jornada pasada que no se había cerrado CUANDO su propietario modifica su contenido ENTONCES queda una entrada de auditoría de la modificación.
- **CA-106** · positivo · RF-22 — DADO una entrada de auditoría de una modificación de una jornada pasada CUANDO la consulto ENTONCES registra autor, fecha real, operación, valor anterior y valor nuevo.
- **CA-107** · permisos · RF-25 — DADO la jornada pasada de otra persona CUANDO intento modificarla ENTONCES no es posible, tampoco para un supervisor.
- **CA-267** · positivo · RF-113 — DADO una operación que modifica varios campos CUANDO se audita ENTONCES existe una única entrada con los valores anterior y nuevo de cada campo afectado.
- **CA-293** · positivo · RF-121 — DADO una jornada pasada sin contenido CUANDO su propietaria registra por primera vez contenido en ella ENTONCES queda una entrada de auditoría de ese registro.
- **CA-294** · límite · RF-121 — DADO una fecha laboral pasada sin bitácora CUANDO la propietaria abre una bitácora vacía de esa fecha ENTONCES no se genera ninguna entrada de auditoría.
- Cada operación genera una única entrada de auditoría (RN-103).
