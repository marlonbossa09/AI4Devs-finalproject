# HU-1.3 — Asignar pertenencias y conservar las anteriores

| | |
|---|---|
| **Módulo** | M1 — Autenticación, usuarios y equipos |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-28, RN-34, RN-33, RN-94, RN-95, RN-99 |
| **Requisitos** | RF-53, RF-37, RF-104, RF-105, RF-109 |
| **Dependencias** | HU-1.2, HU-1.5 (provisión) |
| **Decisiones pendientes** | PA-25 (ajustes históricos excepcionales de pertenencia; no afecta a los criterios de esta historia) |

## Historia

Como organización, quiero asignar a cada persona a su equipo y conservar sus pertenencias anteriores cuando cambia de equipo, para mantener la trazabilidad del equipo.

## Criterios de aceptación

- **CA-11** · positivo · RF-53 — DADO una persona sin equipo asignado CUANDO se ejecuta el procedimiento de asignación de pertenencia ENTONCES la persona figura en el equipo asignado.
- **CA-12** · positivo · RF-53 — DADO una persona de un equipo CUANDO se ejecuta el procedimiento de cambio de equipo ENTONCES la persona figura en el nuevo equipo y deja de figurar en el anterior.
- **CA-13** · positivo · RF-37 — DADO una persona que cambió de equipo CUANDO se consulta su historial de pertenencias ENTONCES constan los equipos anteriores y las fechas en que estuvo en cada uno.
- **CA-14** · límite · RF-53 — DADO una persona que cambia de equipo CUANDO se completa el cambio ENTONCES pertenece a un único equipo.
- **CA-243** · negativo · RF-105 — DADO un traslado ordinario CUANDO se intenta registrar con una fecha efectiva igual o anterior a la fecha actual de la organización ENTONCES se rechaza.
- **CA-244** · positivo · RF-109 — DADO un traslado programado cuya fecha efectiva es posterior a la fecha actual CUANDO la provisión controlada lo cancela ENTONCES la persona permanece en su equipo y la auditoría conserva la operación original, la cancelación, su autor y los valores retirados.
- **CA-245** · negativo · RF-109 — DADO un traslado cuya fecha efectiva es igual o anterior a la fecha actual CUANDO se intenta cancelarlo o sustituirlo ENTONCES se rechaza.
- **CA-246** · negativo · RF-109 — DADO una cancelación que dejaría a un equipo con colaboradores sin supervisor CUANDO se intenta aplicar ENTONCES se rechaza sin modificar ninguna pertenencia.
- **CA-247** · positivo · RF-109 — DADO un traslado programado CUANDO se sustituye por otro con una fecha efectiva posterior a la fecha actual ENTONCES queda vigente solo el nuevo y la auditoría conserva ambas operaciones.
- **CA-248** · límite · RF-104 — DADO las pertenencias de una persona CUANDO se revisa su período de actividad ENTONCES cada fecha laboral tiene un único equipo, sin solapes ni huecos.
- **CA-278** · positivo · RF-109 — DADO un alta con inicio futuro CUANDO la provisión controlada la cancela ENTONCES la persona queda sin pertenencia, no puede operar y la auditoría conserva la operación original, la cancelación y su autor.
- **CA-279** · positivo · RF-109 — DADO un cambio de rol programado con fecha efectiva posterior a la fecha actual CUANDO la provisión controlada lo cancela ENTONCES la persona conserva su rol y la auditoría conserva la operación original, la cancelación, su autor y los valores retirados.

## Notas

- Los efectos del cambio de equipo sobre la visibilidad de los registros están en HU-1.4.
- Las pertenencias programadas pueden cancelarse o sustituirse antes de su fecha efectiva (RN-99). Los ajustes históricos excepcionales de pertenencia no existen en el MVP (PA-25).
