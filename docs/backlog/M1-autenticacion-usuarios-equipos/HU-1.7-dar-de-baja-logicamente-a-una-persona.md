# HU-1.7 — Dar de baja lógicamente a una persona

| | |
|---|---|
| **Módulo** | M1 — Autenticación, usuarios y equipos |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-34, RN-38, RN-52, RN-96, RN-97, RN-98, RN-105 |
| **Requisitos** | RF-54, RF-106, RF-107, RF-108, RF-115 |
| **Dependencias** | HU-1.5 |
| **Decisiones pendientes** | PA-04 (cómo corregir la bitácora de una persona dada de baja; no afecta a los criterios de esta historia); PA-12 (reactivación administrativa del acceso); PA-24 (reincorporación) |

## Historia

Como organización, quiero dar de baja lógicamente a una persona, para que deje de acceder al producto sin perder su histórico.

## Criterios de aceptación

- **CA-29** · positivo · RF-54 — DADO una persona con el acceso desactivado o sin pertenencia vigente CUANDO intenta operar ENTONCES no accede al producto.
- **CA-30** · positivo · RF-54 — DADO una persona dada de baja CUANDO una persona autorizada consulta sus bitácoras y actividades ENTONCES siguen siendo consultables conforme a la pertenencia histórica de cada registro.
- **CA-31** · límite · RF-54 — DADO una persona dada de baja CUANDO se completa la baja ENTONCES ninguno de sus registros se elimina.
- **CA-255** · positivo · RF-106 — DADO una persona con el acceso desactivado CUANDO intenta cualquier operación autenticada ENTONCES no se permite desde el momento de la desactivación.
- **CA-256** · límite · RF-106 — DADO una persona con el acceso desactivado CUANDO una persona autorizada consulta sus registros anteriores ENTONCES su contenido, su equipo histórico y su visibilidad no han cambiado.
- **CA-257** · negativo · RF-106 — DADO una finalización de pertenencia con fecha efectiva F CUANDO la persona intenta registrar una bitácora con fecha igual o posterior a F ENTONCES no se permite.
- **CA-258** · negativo · RF-106 — DADO una finalización de pertenencia CUANDO se intenta registrar con una fecha efectiva igual o anterior a la fecha actual ENTONCES se rechaza.
- **CA-259** · negativo · RF-107 — DADO una persona sin pertenencia vigente y con el acceso sin desactivar CUANDO intenta operar ENTONCES no se permite.
- **CA-260** · positivo · RF-108 — DADO el único supervisor de un equipo con colaboradores CUANDO se desactiva su acceso ENTONCES la desactivación se aplica, su pertenencia histórica se conserva y el equipo queda identificado como pendiente de supervisión efectiva.
- **CA-261** · negativo · RF-108 — DADO un equipo pendiente de supervisión efectiva CUANDO se consultan los permisos de sus colaboradores ENTONCES ninguno ha recibido permisos de supervisión.
- **CA-262** · positivo · RF-115 — DADO una persona con planificación futura posterior a la fecha efectiva de su finalización de pertenencia CUANDO la finalización surte efecto ENTONCES esa planificación se conserva con su actividad y su propietaria.

## Notas

- Mientras PA-04 siga abierto, nadie puede corregir las bitácoras de una persona dada de baja (RN-19, RN-23).
- La baja lógica se compone de la desactivación del acceso, que puede ser inmediata, y de la finalización de la pertenencia, con fecha efectiva posterior a la actual (RN-96). Pueden ejecutarse juntas o por separado.
- Desactivar el acceso del único supervisor no se bloquea: el equipo queda pendiente de supervisión efectiva (RN-98).
- La reactivación administrativa del acceso (PA-12) y la reincorporación (PA-24) no están definidas; no hay criterios sobre ellas.
