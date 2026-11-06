# HU-4.1 — Consultar las bitácoras de mi equipo

| | |
|---|---|
| **Módulo** | M4 — Consulta histórica y supervisión |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-02, RN-12, RN-23, RN-36, RN-37, RN-63 |
| **Requisitos** | RF-23, RF-24, RF-25, RF-67, RNF-13 |
| **Dependencias** | HU-1.2, HU-1.4 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero consultar en solo lectura los registros que pertenecen históricamente a mi equipo, para saber en qué trabaja cada compañero sin preguntarle.

## Criterios de aceptación

- **CA-130** · positivo · RF-23 — DADO un colaborador con compañeros en su equipo CUANDO abre la bitácora de un compañero de una fecha en que ese compañero pertenecía a su equipo ENTONCES ve su contenido en modo lectura.
- **CA-131** · negativo · RF-25 — DADO la bitácora de un compañero CUANDO intento modificar actividades, avances o resumen ENTONCES no es posible.
- **CA-132** · negativo · RF-24 — DADO un colaborador CUANDO intenta abrir un registro de una persona correspondiente a una fecha en que esa persona pertenecía a otro equipo ENTONCES no puede.
- **CA-133** · positivo · RF-67 — DADO un colaborador CUANDO consulta la bitácora del supervisor de su equipo ENTONCES la ve en modo lectura.
- **CA-193** · positivo · RF-23 — DADO un colaborador activo que se incorporó a su equipo después de la fecha de un registro CUANDO abre ese registro de un integrante del equipo de una fecha en que ese integrante pertenecía al equipo ENTONCES puede consultarlo.
- **CA-194** · permisos · RF-25 — DADO el registro de un compañero CUANDO intento ejecutar sobre él cualquier operación de escritura (modificar, cerrar, reabrir, reactivar, marcar como registrado por error o planificar una continuación) ENTONCES no es posible.
- **CA-291** · permisos · RNF-13 — DADO un registro de una fecha que no existe y otro de una fecha en que la persona pertenecía a otro equipo CUANDO un colaborador intenta abrir ambos ENTONCES recibe respuestas indistinguibles que no revelan si existen.

## Notas

- Un integrante activo consulta los registros históricos que corresponden a su equipo aunque se haya incorporado después (RN-36, resuelto en la versión 0.7).
- Un registro inexistente y uno no autorizado producen respuestas indistinguibles (RNF-13).
