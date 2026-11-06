# HU-5.4 — Informe cuando faltan registros

| | |
|---|---|
| **Módulo** | M5 — Informes individuales y consolidados con IA |
| **Estado de preparación** | Lista con dependencia técnica pendiente |
| **Reglas (RN)** | RN-57, RN-36, RN-06 |
| **Requisitos** | RF-33, RF-87 |
| **Dependencias** | HU-5.1 |
| **Decisiones pendientes** | PA-09 (proveedor de IA, conservación y tratamiento de datos) |

## Historia

Como persona que genera un informe, quiero saber cuándo no hay datos o cuándo el informe se basa en registros parciales, para no confundir un informe vacío o incompleto con un informe de todo el trabajo realizado.

## Criterios de aceptación

- **CA-172** · positivo · RF-33 — DADO un período sin ningún registro autorizado CUANDO se genera un informe ENTONCES el informe indica explícitamente que no hay datos disponibles.
- **CA-173** · negativo · RF-33 — DADO un período sin ningún registro autorizado CUANDO se genera un informe ENTONCES el informe no contiene actividades, personas, fechas, avances ni bloqueos inventados.
- **CA-199** · positivo · RF-33 — DADO un período con registros autorizados, completos o parciales CUANDO se genera un informe ENTONCES se genera únicamente con esos registros.
- **CA-200** · negativo · RF-87 — DADO un informe generado, también con registros parciales CUANDO se lee ENTONCES deja claro que se basa únicamente en los registros disponibles y autorizados del período y que no representa información que nunca fue registrada.
- **CA-201** · límite · RF-33 — DADO un período con un único registro autorizado CUANDO se genera un informe ENTONCES se genera con esa información, porque no existe un número mínimo de registros.
- **CA-202** · permisos · RF-33 — DADO un período en el que la persona tiene registros, pero ninguno autorizado para quien genera el informe CUANDO se genera un informe ENTONCES el informe indica que no hay datos disponibles.
