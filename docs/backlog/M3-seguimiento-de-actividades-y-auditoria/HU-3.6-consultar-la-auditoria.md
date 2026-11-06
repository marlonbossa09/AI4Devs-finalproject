# HU-3.6 — Consultar la auditoría

| | |
|---|---|
| **Módulo** | M3 — Seguimiento de actividades y auditoría |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-49, RN-50, RN-51, RN-52, RN-36, RN-110 |
| **Requisitos** | RF-22, RF-71, RF-72, RF-73, RF-120, RNF-13 |
| **Dependencias** | HU-3.4, HU-3.5 |
| **Decisiones pendientes** | PA-06 (política de retención; no afecta a los criterios de esta historia) |

## Historia

Como propietario de una bitácora o supervisor autorizado de su equipo, quiero consultar qué se cambió en un registro, para verificar las correcciones.

## Criterios de aceptación

- **CA-108** · positivo · RF-22 — DADO una corrección auditada CUANDO consulto su entrada ENTONCES veo autor, fecha real, operación, valor anterior y valor nuevo, con contexto suficiente para reconstruir el cambio.
- **CA-109** · positivo · RF-71 — DADO una reapertura auditada CUANDO consulto su entrada ENTONCES consta el motivo de la reapertura.
- **CA-110** · positivo · RF-72 — DADO un registro auditado CUANDO su propietario consulta la auditoría ENTONCES ve las entradas.
- **CA-111** · permisos · RF-72 — DADO un registro que pertenece históricamente al equipo T CUANDO el supervisor autorizado de T consulta su auditoría ENTONCES ve las entradas.
- **CA-112** · permisos · RF-72 — DADO un registro auditado CUANDO un compañero que no es su propietario ni el supervisor autorizado intenta consultar su auditoría ENTONCES no puede.
- **CA-113** · permisos · RF-72 — DADO un registro que pertenece históricamente al equipo T CUANDO el supervisor de otro equipo intenta consultar su auditoría ENTONCES no puede.
- **CA-114** · límite · RF-73 — DADO cualquier corrección o reapertura de un registro CUANDO se realiza ENTONCES el registro no se borra silenciosamente y la operación queda en la auditoría.
- **CA-285** · permisos · RF-120 — DADO una operación de provisión administrativa auditada CUANDO el propietario o el supervisor autorizado consulta la auditoría de una bitácora ENTONCES las entradas de la provisión no aparecen en esa consulta.
- **CA-286** · permisos · RNF-13 — DADO la auditoría de un registro inexistente y la de un registro de otro equipo CUANDO una persona no autorizada intenta consultarlas ENTONCES las respuestas son indistinguibles y no revelan si el registro existe.
- La auditoría de la provisión administrativa permanece separada de esta consulta hasta definir su autoría y permisos (RN-110; PA-12, PA-06).
