# HU-3.8 — Reactivar una actividad Completada

| | |
|---|---|
| **Módulo** | M3 — Seguimiento de actividades y auditoría |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-40, RN-66, RN-68, RN-73, RN-74, RN-77, RN-79, RN-80, RN-91, RN-92, RN-93, RN-24, RN-70, RN-23, RN-45, RN-100 |
| **Requisitos** | RF-65, RF-86, RF-88, RF-90, RF-101, RF-102, RF-103, RF-41, RF-59, RF-110 |
| **Dependencias** | HU-2.8, HU-2.9 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como colaborador, quiero reactivar una actividad Completada sin duplicarla y completar su historia anterior a la finalización, para retomarla cuando el trabajo se reabre y no perder avances olvidados.

## Criterios de aceptación

- **CA-124** · positivo · RF-65 — DADO una actividad Completada mía CUANDO la reactivo mediante la acción explícita de reactivación, con una descripción, en una jornada posterior a la del avance que la completó ENTONCES la misma actividad pasa a un estado distinto de Completada y no se crea otra.
- **CA-125** · positivo · RF-65 — DADO una reactivación CUANDO se completa ENTONCES consta una entrada de auditoría.
- **CA-126** · positivo · RF-65 — DADO una actividad Completada CUANDO la reactivo en una jornada posterior a la del avance que la completó ENTONCES la reactivación se registra como un avance de la secuencia de la actividad, posterior al que la completó.
- **CA-127** · permisos · RF-65 — DADO una actividad Completada de otra persona CUANDO intento reactivarla ENTONCES no es posible.
- **CA-128** · límite · RF-41 — DADO una reactivación que deja la actividad Bloqueada CUANDO no indico un motivo ENTONCES no se permite.
- **CA-129** · negativo · RF-59 — DADO una reactivación CUANDO no incluye una descripción no vacía ENTONCES no se permite.
- **CA-187** · límite · RF-65 — DADO una actividad Completada cuyo avance de finalización tiene la fecha laboral F CUANDO la reactivo en la jornada de la misma fecha laboral F, con un momento de registro posterior ENTONCES se acepta y la reactivación queda posterior al avance que la completó.
- **CA-188** · negativo · RF-65 — DADO una actividad Completada cuyo avance de finalización tiene la fecha laboral F CUANDO intento reactivarla con una fecha laboral anterior a F ENTONCES no se permite.
- **CA-189** · negativo · RF-65 — DADO una actividad Completada CUANDO intento reactivarla en una jornada con fecha laboral futura ENTONCES no se permite.
- **CA-190** · negativo · RF-86 — DADO una actividad Completada CUANDO intento registrarle un avance de ejecución posterior al que la completó sin reactivarla antes ENTONCES no se permite.
- **CA-191** · límite · RF-65 — DADO una actividad reactivada CUANDO se consulta ENTONCES sigue siendo la misma actividad: conserva su identidad, su planificación original y sus avances anteriores.
- **CA-192** · límite · RF-65 — DADO una actividad Completada cuyo avance de finalización tiene la fecha laboral F CUANDO registro, en una jornada pasada con fecha laboral posterior a F, su reactivación ENTONCES se acepta, queda posterior en la secuencia y la modificación de esa jornada pasada queda auditada.
- **CA-203** · positivo · RF-88 — DADO una actividad Completada cuyo avance de finalización tiene la fecha laboral F CUANDO registro un avance retroactivo con fecha laboral anterior a F ENTONCES se acepta sin reactivar la actividad.
- **CA-204** · positivo · RF-88 — DADO ese avance retroactivo CUANDO se registra ENTONCES se inserta en la secuencia histórica según su fecha laboral y consta una entrada de auditoría de la modificación de la jornada pasada.
- **CA-205** · límite · RF-88 — DADO ese avance retroactivo CUANDO existe un avance posterior que mantiene la actividad Completada ENTONCES el estado actual sigue siendo Completada.
- **CA-206** · negativo · RF-86 — DADO una actividad Completada cuyo avance de finalización tiene la fecha laboral F CUANDO intento registrar, sin reactivarla, un avance de ejecución con fecha laboral F y un momento de registro posterior al de la finalización ENTONCES no se permite.
- **CA-207** · límite · RF-88 — DADO una actividad con dos finalizaciones separadas por una reactivación CUANDO intento registrar, sin reactivarla, un avance que según la secuencia quedaría justo después de la primera finalización y antes de la reactivación ENTONCES no se permite, para que la historia siga siendo coherente.
- **CA-208** · permisos · RF-88 — DADO una actividad Completada de otra persona CUANDO intento registrarle un avance retroactivo ENTONCES no es posible.
- **CA-211** · positivo · RF-90 — DADO una actividad Completada CUANDO corrijo con auditoría la descripción de un avance existente anterior a su finalización ENTONCES se acepta sin reactivar la actividad y la corrección no se registra como un nuevo avance de ejecución.
- **CA-236** · negativo · RF-102 — DADO una actividad con avances En progreso el lunes y el martes, Completada el miércoles y una reactivación el jueves CUANDO intento corregir el avance del lunes a Completada ENTONCES la corrección se rechaza.
- **CA-237** · negativo · RF-101 — DADO una corrección rechazada CUANDO se consulta la actividad ENTONCES sus avances, su estado actual y su auditoría no han cambiado.
- **CA-238** · positivo · RF-102 — DADO una actividad Completada CUANDO corrijo el estado de su avance de finalización a otro estado y la secuencia resultante sigue siendo válida ENTONCES se acepta, queda auditada y el estado actual se recalcula.
- **CA-239** · negativo · RF-103 — DADO una corrección válida o rechazada CUANDO se resuelve ENTONCES no se crea ninguna reactivación automática.
- **CA-269** · positivo · RF-110 — DADO una actividad Completada CUANDO la reactivo hacia Pendiente o En progreso ENTONCES se acepta y la finalización anterior se conserva.
- **CA-270** · negativo · RF-110 — DADO una actividad Completada CUANDO intento reactivarla hacia Bloqueada sin indicar un motivo ENTONCES se rechaza.
- **CA-271** · positivo · RF-110 — DADO una actividad Completada CUANDO la reactivo hacia Bloqueada indicando un motivo ENTONCES se acepta y el motivo se conserva en el historial.

## Notas

- CA-207 recoge la regla confirmada RN-79: no se admite insertar un avance de ejecución en un intervalo posterior a una finalización y anterior a una reactivación válida.
- Los avances retroactivos anteriores a una finalización se registran con auditoría (CA-203 a CA-205). Las correcciones de registros existentes no son nuevos avances de ejecución (CA-211).
- Toda corrección se valida contra la secuencia completa (RN-91 a RN-93, CA-236 a CA-239). "Eliminar una finalización" se interpreta como una corrección que la deja sin efecto; no existe borrado de avances.
- Las actividades marcadas como registradas por error no se reactivan ni reciben avances (HU-3.7).
- La reactivación admite Pendiente, En progreso o Bloqueada con motivo, y la finalización anterior se conserva (RN-100).
