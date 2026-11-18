# SMARTWORK — Contratos de la API: M4 Consulta histórica y supervisión

| Campo | Contenido |
|---|---|
| **Estado** | `[PROPUESTO]`, pendiente de revisión. **Implementación:** M4-01 (M4-T1) y M4-02 (M4-T2) implementados el 2026-11-17; M4-03 y M4-04 sin implementar |
| **Versión** | 0.7 |
| **Fecha** | 2026-11-17 |
| **Convenciones** | `docs/api/convenciones.md` |

Todas las operaciones de este módulo son de **solo lectura**. Aplican la política de autorización centralizada (RA-01 a RA-12): el equipo de un registro se deduce de la pertenencia de su propietaria en la fecha laboral, y ninguna respuesta incluye información de otro equipo que la política no permita. Las operaciones de escritura sobre un registro de un compañero no existen en la API: todas cuelgan de `/mi/...` y, si se apunta a un registro ajeno, responden según la convención T-01.

**Protección entre equipos (aplicable a los cuatro contratos).**

- La actividad se presenta en forma `completa` solo a quienes están autorizados sobre su jornada de origen; a los demás, en forma `neutral`, sin título ni marca de error (RA-04, DM-03).
- Un avance, una planificación o una bitácora autorizados se muestran con su detalle propio (descripción y motivo de bloqueo del propio registro), que no incluye el título de la actividad (RA-05). Los motivos de bloqueo de registros de otro equipo nunca se exponen.
- La planificación conservada tras una finalización de pertenencia no se muestra como trabajo vigente ni pendiente de ningún equipo (RA-11).
- El estado actual solo se informa si la propietaria pertenece al equipo (RN-48, RN-85).
- **`forma` (confirmado el 2026-11-17):** cada `ActividadVisible` lleva un campo `forma` (`completa` o `neutral`) que es el **discriminador explícito** de sus dos formas en el JSON. La forma `neutral` tiene una lista cerrada de campos: `forma`, `id`, `propietaria_id` y `referencia_neutral`. En la forma `completa`, el campo `estado_actual` se **omite** (no se envía nulo) cuando la propietaria no pertenece hoy al equipo de quien consulta.

## M4-01 — Consultar la bitácora de un compañero

| Campo | Contenido |
|---|---|
| **Propósito** | Leer, sin poder modificarla, la bitácora de un integrante de mi equipo (incluido su supervisor) de una fecha en que pertenecía a mi equipo |
| **Relacionados** | HU-4.1, HU-1.4 · RF-23, RF-24, RF-25, RF-67, RF-66, RF-97 · RN-02, RN-12, RN-23, RN-36, RN-37, RN-63 |
| **Método y ruta** | `GET /api/v1/personas/{persona_id}/bitacoras/{fecha_laboral}` |
| **Entrada** | Ruta: `persona_id` y `fecha_laboral` |
| **Respuesta** | 200: la Bitácora en solo lectura, con sus planificaciones vigentes, avances y actividades (en forma `completa` o `neutral` según RA-04) |
| **Validaciones** | La persona consultada pertenecía a mi equipo en esa fecha laboral (RA-01). Un colaborador que se incorporó después puede abrir los registros de una fecha en que el compañero pertenecía al equipo (CA-193). La bitácora del supervisor de mi equipo es visible en solo lectura (CA-133). Si `persona_id` soy yo, equivale a M2-01a |
| **Autorización** | Colaboradores y supervisor del equipo histórico del registro. Un registro de una fecha en que la persona pertenecía a otro equipo no se puede abrir (CA-132). El filtrado de autorización se aplica antes de construir la respuesta (convenciones 3.3) |
| **Errores** | `RECURSO_NO_DISPONIBLE` (inexistente o de otro equipo, indistinguibles) · `SOLICITUD_INVALIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | Lectura |
| **Criterios vinculados** | CA-130, CA-131, CA-132, CA-133, CA-193, CA-194, CA-291, CA-15, CA-16, CA-17, CA-18, CA-21, CA-176, CA-177, CA-178, CA-216, CA-217, **CA-30, CA-256** (vinculados el 2026-11-17: la lectura, por un compañero o el supervisor, de los registros de una persona finalizada o con el acceso desactivado) |
| **Aplicación (M4-T1, 2026-11-17)** | Implementado en `app/modulos/consulta`. Orden de evaluación de convenciones 3.2: sesión, puede operar, formato de `persona_id` y `fecha_laboral` (`SOLICITUD_INVALIDA`) y visibilidad (`RECURSO_NO_DISPONIBLE`) **antes** de leer nada. La decisión de visibilidad es la de M1 (`decidir_lectura`, `forma_de_actividad` y `puede_ver_estado_actual`); no hay política paralela. Un registro inexistente, de otro equipo en esa fecha, de otra organización, de una persona inexistente o de una fecha sin bitácora devuelven exactamente la misma respuesta 404. Las actividades se proyectan según la autorización sobre su **jornada de origen** (completa, neutral u oculta); una actividad oculta (marcada por error con origen no autorizado) no aparece ni sus planificaciones ni sus avances. La planificación y el avance se muestran con su detalle propio, sin el título de la actividad. Si `persona_id` es quien consulta, el contenido equivale a M2-01a (más `forma`). La ruta de M4 solo admite `GET`: cualquier otro método responde 405 con `Allow: GET`. M2 y M3 no cambian (siguen respondiendo 404 sobre lo ajeno hasta M4-T6). **Pendiente de verificación completa en M4-T6:** CA-178 y las prohibiciones de escritura ajena (CA-131, CA-194): M4-T1 solo demuestra que **M4 no tiene ninguna ruta de escritura**; que las escrituras existentes de M2 y M3 sobre un registro visible ajeno respondan 403 `OPERACION_NO_PERMITIDA` es de M4-T6 |
| **Decisiones pendientes** | D-07 (confirmada: referencia neutral «Actividad en continuidad», con identificador opaco) |

## M4-02 — Consultar el histórico por colaborador y fechas

| Campo | Contenido |
|---|---|
| **Propósito** | Recuperar lo que se hizo en un período, filtrando por colaborador y rango de fechas laborales |
| **Relacionados** | HU-4.2, HU-1.4 · RF-26, RF-83 · RN-25, RN-05, RN-36 |
| **Método y ruta** | `GET /api/v1/historico` |
| **Entrada** | Consulta: `desde` y `hasta` (obligatorios), `persona_id` (opcional), `limite`, `continuar_desde`. No hay búsqueda por texto ni otros filtros: un parámetro desconocido se rechaza |
| **Respuesta** | 200: lista paginada de bitácoras de ese colaborador y rango (`persona_id`, `fecha_laboral`, `estado`, `resumen` y actividades en forma `completa` o `neutral`) |
| **Validaciones** | Solo se devuelven los registros que estoy autorizado a consultar (RA-01, CA-135). Un filtro sin registros autorizados da una lista vacía, no un error (T-01). El rango usa fechas laborales (RN-05). **D-08 (confirmada):** el rango de fechas es obligatorio y su amplitud máxima es configurable (PA-13). `persona_id` es opcional: si se indica, solo se devuelven los registros autorizados de esa persona; si se omite, los registros autorizados de las personas que la política de autorización permite a quien consulta, siempre incluidos los propios. Orden estable: fecha laboral, persona e identificador. Paginación según convenciones 6.1 |
| **Autorización** | Según el equipo histórico de cada registro; la propietaria ve todos los suyos. El filtrado de autorización se aplica antes de construir la respuesta (convenciones 3.3) |
| **Errores** | `SOLICITUD_INVALIDA` (incluidas la búsqueda por texto, CA-136, y la falta o el exceso del rango) · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | Lectura |
| **Criterios vinculados** | CA-134, CA-135, CA-136, CA-19, CA-20, CA-299, CA-300, **CA-30, CA-256** (vinculados el 2026-11-17: el histórico de un rango incluye los registros de personas finalizadas o con el acceso desactivado) |
| **Aplicación (M4-T2, 2026-11-17)** | Implementado en `app/modulos/consulta` con utilidad de paginación propia de M4 (`app/compartido/paginacion.py`; M2 y M3 no se tocan, D-M4-08). **Parámetros admitidos:** `desde`, `hasta`, `persona_id`, `limite` y `continuar_desde`; cualquier otro, o uno repetido, es `SOLICITUD_INVALIDA` (`parametro_no_soportado` o `parametro_repetido`). **Rango (D-M4-03 y D-M4-04, confirmadas):** `desde` y `hasta` obligatorios (`obligatorio`), `desde` ≤ `hasta` (`posterior_a_hasta`), `hasta` puede ser una fecha futura y la amplitud —`hasta − desde + 1` días, extremos incluidos— no puede superar `QUERY_MAX_RANGE_DAYS` (por defecto **92**; `rango_excede_el_maximo` con `maximo_dias` en `detalles`). **Elementos:** `persona_id`, `fecha_laboral`, `estado`, `resumen` y `actividades` (`ActividadVisible`: `forma` `completa` o `neutral`; las ocultas no aparecen), sin ningún campo más. **Orden:** `fecha_laboral`, `persona_id` e identificador de la bitácora (único por persona y fecha). **Paginación:** `limite` (por defecto 20, máximo 100) y `continuar_desde`, un cursor opaco con la posición del último elemento entregado; es solo una posición: la autorización se aplica siempre al seleccionar, así que un cursor fabricado no entrega nada que la consulta no entregaría, y uno inválido se rechaza (`cursor_invalido`). `siguiente` es nulo cuando no hay más. **Autorización:** el predicado `condicion_lectura` de la política de M1 se aplica **en la propia consulta, antes de ordenar y de paginar**: lo no autorizado no cambia los elementos, su orden, el tamaño de las páginas, el cursor ni `siguiente`. **Persona:** si se indica `persona_id`, solo los registros autorizados de esa persona; una persona no autorizada, de otra organización o inexistente da la misma lista vacía (200), sin revelar su existencia. Sin `persona_id`, los de las personas que la política permite, siempre incluidos los propios. Una persona trasladada se ve por el equipo de cada fecha; los registros de personas finalizadas o con el acceso desactivado siguen siendo visibles para su equipo de esa fecha. La ruta solo admite `GET` (405 con `Allow: GET`). Sin búsqueda por texto. **Índice (migración 0018, aprobada y aplicada el 2026-11-18):** `bitacora_historico_idx` sobre `bitacora (fecha_laboral, persona_id, id)`, con el mismo orden que la paginación; es un detalle de rendimiento y no cambia ningún resultado, ni el contrato |
| **Decisiones pendientes** | D-08 y D-10 (confirmadas o aceptadas) |

## M4-03 — Obtener la vista de supervisión del equipo en un período

| Campo | Contenido |
|---|---|
| **Propósito** | Dar al supervisor una vista consolidada de las actividades de su equipo en un período, clasificadas por estado, con el estado al corte y, cuando procede, el estado actual |
| **Relacionados** | HU-4.3, HU-3.7 · RF-25, RF-27, RF-45, RF-69, RF-70, RF-78, RF-83, RF-94, RF-95, RF-98, RF-99, RF-111, RF-115 · RN-13, RN-47, RN-48, RN-60, RN-84, RN-85, RN-88, RN-89, RN-101, RN-105 |
| **Método y ruta** | `GET /api/v1/equipo/supervision` |
| **Entrada** | Consulta: `desde` y `hasta` (el período, obligatorios). No existe un parámetro `corte` independiente (D-06, aprobada): el corte es el último día del período, es decir `hasta`; un parámetro `corte` se rechaza con `SOLICITUD_INVALIDA`, `limite` y `continuar_desde` (D-10) |
| **Respuesta** | 200: `periodo`, `corte` (informativo, igual a `hasta`), `totales_por_estado` (recuento de las actividades autorizadas por estado al corte en todo el período, no solo en la página) y `elementos` (lista paginada). Cada elemento tiene `tipo`: si es `actividad`, incluye la ActividadVisible, `propietaria_id`, `motivo_inclusion`, `estado_al_corte` y `estado_actual_si_difiere` (presente solo si difiere del estado al corte y la propietaria pertenece al equipo); si es `referencia_minima`, la ReferenciaMínima. La clasificación por estado (CA-137) la dan `estado_al_corte` y `totales_por_estado` |
| **Validaciones** | **Inclusión (RN-47):** actividades del equipo planificadas en el período (CA-138), con avances en el período (CA-139) y no completadas que siguen pendientes de atención (CA-140); no las completadas antes del período sin avances en él (CA-141); incluye las propias del supervisor (CA-142). **Estado al corte (RA-07):** calculado con la secuencia válida completa; si coincide con el actual, se muestra uno solo (CA-144); si difiere, se indica aparte (CA-143); una continuación planificada posterior al corte no influye (CA-198). No se muestra el estado al corte cuando lo determina un avance de otro equipo (CA-230); sí cuando lo determina un avance autorizado, sin revelar información protegida (CA-231). **Referencia mínima:** las actividades heredadas pendientes sin registros del equipo se devuelven como elementos de `tipo` `referencia_minima`, claramente distinguidos del acceso completo (CA-218, CA-232) y sin título, descripciones, motivos de bloqueo, contenido de bitácoras, equipo anterior ni número de avances (CA-219); sin fecha del último avance si pertenece al equipo anterior (CA-220). Con avances del equipo nuevo, la actividad se identifica con la referencia neutral y se muestra el detalle propio de esos avances (CA-223, CA-272, CA-273). Personas trasladadas: el supervisor del equipo nuevo no ve registros anteriores al traslado (CA-196) y el del equipo anterior no ve los posteriores (CA-197); este último conserva los autorizados y su estado al corte, sin estado actual (CA-221, CA-222). Se excluyen las marcadas por error (CA-147) y la planificación conservada (CA-274). Sin clasificaciones, rankings ni puntuaciones de personas (CA-145). Los criterios que hablan de «el corte» se leen como el último día del período consultado (D-06). Orden estable: estado al corte (Pendiente, En progreso, Bloqueada, Completada), propietaria e identificador (convenciones 6.1) |
| **Autorización** | Solo el supervisor de un equipo, con acceso efectivo (RA-12). Solo incluye actividades de su equipo (CA-146). Un colaborador recibe `OPERACION_NO_PERMITIDA` (RN-13). La vista es de solo lectura: no ofrece modificación (CA-195). El filtrado de autorización se aplica antes de construir la respuesta (convenciones 3.3), también los recuentos y el estado al corte |
| **Errores** | `OPERACION_NO_PERMITIDA` · `SOLICITUD_INVALIDA` (período inválido o parámetro `corte`) · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | Lectura. Consulta histórica sin entradas de auditoría |
| **Criterios vinculados** | CA-137, CA-138, CA-139, CA-140, CA-141, CA-142, CA-143, CA-144, CA-145, CA-146, CA-147, CA-195, CA-196, CA-197, CA-198, CA-218, CA-219, CA-220, CA-221, CA-222, CA-223, CA-230, CA-231, CA-232, CA-268, CA-272, CA-273, CA-274, CA-301 |
| **Decisiones pendientes** | D-07 y D-10 (confirmadas o aceptadas). D-06 aprobada |

## M4-04 — Consultar el historial de una actividad de mi equipo

| Campo | Contenido |
|---|---|
| **Propósito** | Seguir la evolución de una actividad de mi equipo: avances con su fecha laboral y estado histórico, sin poder modificarla |
| **Relacionados** | HU-4.4, HU-4.3, HU-1.4 · RF-25, RF-28, RF-45, RF-99, RF-111, RF-92 · RN-13, RN-17, RN-23, RN-48, RN-89, RN-101 |
| **Método y ruta** | `GET /api/v1/equipo/actividades/{actividad_id}` |
| **Entrada** | Ruta: `actividad_id` |
| **Respuesta** | 200: ActividadVisible, los avances **autorizados** en orden de secuencia (fecha laboral, estado histórico, descripción y motivo de bloqueo del propio avance), las planificaciones vigentes autorizadas y `estado_actual` (solo si la propietaria pertenece al equipo). **D-09 (aprobada):** si la actividad es heredada y no hay avances ni planificaciones autorizados para el equipo, la respuesta es 200 con **solo la ReferenciaMínima** (`tipo: referencia_minima`): propietaria, indicación de que se inició en otro equipo, estado actual y referencia neutral. No incluye título, descripciones, motivos, avances ni estado al corte de otro equipo |
| **Validaciones** | Solo los registros de períodos autorizados; ningún avance ni motivo de otro equipo (CA-273). Título original protegido: referencia neutral cuando el origen no está autorizado (CA-275). Una actividad heredada sin avances autorizados solo se muestra mediante la referencia mínima (CA-233; D-09); el estado actual solo se informa si la propietaria pertenece al equipo. Si la actividad no admite ni siquiera referencia mínima (por ejemplo, está Completada, o su propietaria no es supervisada por la persona), responde como cualquier recurso no disponible. Sin clasificaciones, rankings ni puntuaciones (CA-151). Si la actividad heredada no tiene avances autorizados, el historial se limita a la referencia mínima (CA-292) |
| **Autorización** | Supervisor con acceso efectivo, sobre actividades de su equipo. En solo lectura (CA-149, CA-150). El filtrado de autorización se aplica antes de construir la respuesta (convenciones 3.3) |
| **Errores** | `RECURSO_NO_DISPONIBLE` · `OPERACION_NO_PERMITIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | Lectura |
| **Criterios vinculados** | CA-148, CA-149, CA-150, CA-151, CA-233, CA-275, CA-273, CA-292, CA-215 |
| **Decisiones pendientes** | D-07 (confirmada). D-09 aprobada |
