# HU-4.3 — Supervisar mi equipo en un período

| | |
|---|---|
| **Módulo** | M4 — Consulta histórica y supervisión |
| **Estado de preparación** | Lista para diseño técnico |
| **Reglas (RN)** | RN-13, RN-47, RN-48, RN-60, RN-36, RN-23, RN-75, RN-84, RN-85, RN-88, RN-89, RN-101, RN-105 |
| **Requisitos** | RF-27, RF-69, RF-70, RF-45, RF-78, RF-25, RF-83, RF-94, RF-95, RF-98, RF-99, RF-111, RF-115 |
| **Dependencias** | HU-2.9, HU-3.1 |
| **Decisiones pendientes** | Ninguna |

## Historia

Como supervisor, quiero una vista consolidada de mi equipo para un período, para saber qué está pendiente, en progreso, bloqueado y completado.

## Criterios de aceptación

En los criterios, P es una persona que perteneció al equipo T y después pasó al equipo U.

- **CA-137** · positivo · RF-27 — DADO un supervisor CUANDO selecciona un período ENTONCES ve las actividades de su equipo clasificadas en Pendiente, En progreso, Bloqueada y Completada.
- **CA-138** · positivo · RF-69 — DADO una actividad del equipo planificada durante el período CUANDO el supervisor consulta la vista de ese período ENTONCES aparece en la vista.
- **CA-139** · positivo · RF-69 — DADO una actividad del equipo con avances durante el período CUANDO el supervisor consulta la vista de ese período ENTONCES aparece en la vista.
- **CA-140** · positivo · RF-69 — DADO una actividad del equipo sin avances en el período que sigue sin completarse al final del período CUANDO el supervisor consulta la vista de ese período ENTONCES aparece en la vista.
- **CA-141** · negativo · RF-69 — DADO una actividad del equipo completada antes del período y sin avances en él CUANDO el supervisor consulta la vista de ese período ENTONCES no aparece en la vista.
- **CA-142** · positivo · RF-69 — DADO las actividades del propio supervisor CUANDO consulta la vista de un período en el que las tuvo ENTONCES aparecen en la vista junto con las del equipo.
- **CA-143** · positivo · RF-70 — DADO una actividad de una persona que pertenece al equipo, Bloqueada al corte del período y Completada hoy CUANDO el supervisor consulta la vista ENTONCES la vista la muestra como Bloqueada al corte e indica aparte que su estado actual es Completada.
- **CA-144** · límite · RF-70 — DADO una actividad cuyo estado al corte coincide con su estado actual CUANDO el supervisor consulta la vista ENTONCES la vista muestra un único estado, sin indicar diferencia.
- **CA-145** · negativo · RF-45 — DADO la vista del supervisor CUANDO se revisa su contenido ENTONCES no contiene clasificaciones, rankings ni puntuaciones de personas.
- **CA-146** · permisos · RF-27 — DADO un supervisor CUANDO consulta la vista ENTONCES solo incluye actividades de su equipo y no de otros equipos.
- **CA-147** · negativo · RF-78 — DADO una actividad marcada como registrada por error CUANDO el supervisor consulta la vista ENTONCES no aparece en ella.
- **CA-195** · permisos · RF-25 — DADO la vista de supervisión CUANDO el supervisor intenta modificar desde ella un registro de su equipo ENTONCES no es posible.
- **CA-196** · permisos · RF-83 — DADO P trasladada de T a U CUANDO el supervisor de U consulta la vista para un período que incluye fechas anteriores al traslado ENTONCES la vista no incluye los registros de P de esas fechas.
- **CA-197** · permisos · RF-83 — DADO P trasladada de T a U CUANDO el supervisor de T consulta la vista para un período que incluye fechas posteriores al traslado ENTONCES la vista no incluye los registros de P de esas fechas.
- **CA-198** · límite · RF-70 — DADO una actividad del equipo con una continuación planificada para una fecha posterior al corte CUANDO el supervisor consulta la vista al corte ENTONCES el estado mostrado es el del último avance de ejecución hasta el corte, sin que la continuación planificada intervenga.
- **CA-218** · positivo · RF-94 — DADO el supervisor de U y una actividad pendiente de P, iniciada en T y sin registros en U CUANDO consulta la vista ENTONCES ve una referencia mínima con el propietario, la indicación de que se inició en otro equipo y su estado actual.
- **CA-219** · negativo · RF-94 — DADO esa referencia mínima CUANDO se revisa su contenido ENTONCES no incluye el título, las descripciones, los motivos de bloqueo, el contenido de bitácoras, el nombre del equipo anterior ni el número de avances.
- **CA-220** · límite · RF-94 — DADO esa referencia mínima CUANDO el último avance de la actividad pertenece al equipo anterior ENTONCES no muestra su fecha laboral.
- **CA-221** · negativo · RF-95 — DADO el supervisor de T y una persona P trasladada a U CUANDO consulta la vista de un período posterior al traslado ENTONCES no presenta como pendiente actual ninguna actividad de P.
- **CA-222** · positivo · RF-95 — DADO el supervisor de T CUANDO consulta la vista de un período anterior al traslado de P ENTONCES conserva los registros autorizados de P de ese período y su estado al corte, sin mostrar su estado actual.
- **CA-223** · positivo · RF-94 — DADO esa actividad CUANDO P registra en U un avance sobre ella ENTONCES el supervisor de U ve ese avance con su descripción y, en su caso, su motivo de bloqueo, porque pertenece a U, y la actividad se identifica con una referencia neutral.
- **CA-230** · positivo · RF-98 — DADO el supervisor de U y una actividad heredada de P cuyo último avance hasta el corte pertenece a T, sin avances de U hasta el corte CUANDO consulta la vista de un período cuyo último día es ese corte ENTONCES no se muestra su estado al corte y se muestra la referencia mínima con el estado actual.
- **CA-231** · positivo · RF-98 — DADO esa misma actividad con un avance autorizado de U anterior o igual al corte CUANDO el supervisor de U consulta la vista de un período cuyo último día es ese corte ENTONCES se muestra el estado al corte que resulta de ese avance, sin revelar información de T.
- **CA-232** · límite · RF-99 — DADO una referencia mínima en la vista CUANDO se revisa ENTONCES se distingue claramente como referencia mínima y no como acceso completo al historial de la actividad.
- **CA-233** · negativo · RF-99 — DADO una referencia mínima CUANDO el supervisor de U intenta abrir el historial completo de la actividad ENTONCES no obtiene los registros protegidos del equipo anterior.
- **CA-272** · permisos · RF-111 — DADO una actividad iniciada en el equipo T con avances posteriores del equipo U CUANDO el supervisor de U consulta la vista de supervisión ENTONCES la actividad se identifica con una referencia neutral y no se muestra su título original.
- **CA-273** · permisos · RF-111 — DADO un avance del equipo T con un motivo de bloqueo CUANDO el supervisor de U consulta la actividad ENTONCES no se muestra ese motivo de bloqueo.
- **CA-274** · permisos · RF-115 — DADO una planificación conservada de una persona sin pertenencia vigente CUANDO el supervisor de un equipo consulta su vista de supervisión ENTONCES no la ve como trabajo vigente ni pendiente de ningún equipo.
- **CA-301** · permisos · RF-111 — DADO una actividad heredada identificada con una referencia neutral CUANDO el supervisor del equipo nuevo la revisa ENTONCES se muestra «Actividad en continuidad» con un identificador que no contiene información del equipo anterior.

## Notas

- La referencia mínima y su clasificación de seguridad están documentadas en el alcance (sección 6.2.1).
- El estado al corte no se muestra cuando deriva exclusivamente de registros protegidos de otro equipo (RN-88).
- La actividad heredada se identifica con la referencia neutral «Actividad en continuidad» (RN-101). La planificación conservada no se muestra como trabajo vigente (RN-105).
- El corte de la vista es el último día del período consultado (RN-48).
