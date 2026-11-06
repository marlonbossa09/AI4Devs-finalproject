# SMARTWORK — Contratos de la API: M2 Bitácoras laborales híbridas

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]`, pendiente de revisión |
| **Versión** | 0.5 |
| **Fecha** | 2026-11-06 |
| **Convenciones** | `docs/api/convenciones.md` (formato, errores, autorización y esquemas) |

Todas las operaciones de este módulo actúan sobre registros propios (RN-23). Para consultar los de otras personas, ver M4.

## M2-01a — Consultar mi bitácora de una fecha laboral

| Campo | Contenido |
|---|---|
| **Propósito** | Obtener mi bitácora de una fecha laboral con sus planificaciones, avances y actividades. **No crea nada.** |
| **Relacionados** | HU-2.1, HU-2.7 · RF-04, RF-05, RF-10, RF-12, RF-117 · RN-16, RN-18, RN-23, RN-107 |
| **Método y ruta** | `GET /api/v1/mi/bitacoras/{fecha_laboral}` |
| **Entrada** | Ruta: `fecha_laboral`. Sin cuerpo |
| **Respuesta** | 200: `bitacora` (esquema Bitácora, con las tres fechas por separado), `planificaciones[]`, `avances[]` y `actividades[]` referenciadas (vista de la propietaria) |
| **Validaciones** | Formato de la fecha. La consulta nunca crea una bitácora (D-01) |
| **Autorización** | Propietaria. Las bitácoras de otras personas se consultan con M4-01 |
| **Errores** | `RECURSO_NO_DISPONIBLE` si no existe bitácora mía de esa fecha · `SOLICITUD_INVALIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | Lectura: no audita ni modifica |
| **Criterios vinculados** | CA-32, CA-33, CA-34, CA-35, CA-61, CA-62, CA-282 |
| **Decisiones pendientes** | Ninguna (D-01 aprobada) |

## M2-01b — Abrir mi bitácora de una fecha laboral

| Campo | Contenido |
|---|---|
| **Propósito** | Crear mi bitácora de una fecha laboral si aún no existe. Es idempotente: si ya existe, devuelve la existente. Separa explícitamente crear de consultar |
| **Relacionados** | HU-2.1, HU-2.7, HU-3.5 · RF-04, RF-10, RF-11, RF-12, RF-58, RF-104, RF-117, RF-121 · RN-16, RN-14, RN-44, RN-94, RN-107, RN-111 |
| **Método y ruta** | `POST /api/v1/mi/bitacoras` |
| **Entrada** | Cuerpo: `fecha_laboral` (obligatoria) |
| **Respuesta** | 201 con `creada: true` y la Bitácora creada; 200 con `creada: false` y la Bitácora existente, sin cambio alguno |
| **Validaciones** | La fecha laboral debe estar cubierta por una pertenencia mía (`FECHA_NO_CUBIERTA`: ni antes de mi primera pertenencia ni fuera de mi período de actividad). Una fecha pasada se acepta sin límite de antigüedad (CA-59, CA-60). Una fecha futura se acepta para planificar (RN-27). No hay restricción por días festivos (CA-64). **Semántica de idempotencia (D-01):** si ya existe, devuelve la misma bitácora (mismo `id`, `creada_en`, `modificada_en`, `estado` y `resumen`), no la modifica, no deja entrada de auditoría y no la reabre si estaba cerrada. Es la única vía de apertura explícita; las operaciones de escritura también abren de forma implícita (convenciones 5.1) |
| **Autorización** | Solo para mí: el cuerpo no admite otra persona |
| **Errores** | `FECHA_NO_CUBIERTA` · `SOLICITUD_INVALIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | Abrir una bitácora vacía de una jornada pasada no es una escritura efectiva y no genera entrada (D-02, confirmada). Dos aperturas simultáneas de la misma fecha dejan una sola bitácora (IR-01): una recibe 201 y la otra 200 con el mismo `id`. Abrir una bitácora que ya existe no modifica nada ni genera entrada |
| **Criterios vinculados** | CA-32, CA-33, CA-35, CA-59, CA-60, CA-63, CA-64, CA-264, CA-280, CA-281, CA-294 |
| **Decisiones pendientes** | D-02 (confirmada) |

## M2-02 — Guardar el resumen libre de mi bitácora

| Campo | Contenido |
|---|---|
| **Propósito** | Guardar (reemplazar) el resumen libre de mi bitácora. Es también la vía de corrección del resumen, una vez reabierta la bitácora (no se crea un contrato aparte) |
| **Relacionados** | HU-2.1, HU-2.7, HU-3.4, HU-3.5 · RF-05, RF-12, RF-21, RF-25, RF-10, RF-117, RF-118 · RN-16, RN-19, RN-23, RN-45, RN-107, RN-108 |
| **Método y ruta** | `PUT /api/v1/mi/bitacoras/{fecha_laboral}/resumen` |
| **Entrada** | Ruta: `fecha_laboral`. Cuerpo: `resumen` (texto libre) |
| **Respuesta** | 200 con la Bitácora actualizada (`modificada_en` renovada) |
| **Validaciones** | El texto se trata como datos (RN-31). Modificar el contenido de una jornada cerrada exige reabrirla antes con M3-02 (D-04). Si la bitácora de esa fecha no existe, se crea en la misma transacción con las mismas condiciones que M2-01b (D-01, aprobada); la respuesta indica `bitacora_creada`. Un resumen vacío se acepta al guardar; solo impide cerrar (RN-21, M3-01). No se fija longitud máxima (D-03). Textos (D-03, confirmada): `resumen` opcional al guardar, con máximo configurable |
| **Autorización** | Propietaria (CA-36). Sobre la bitácora de otra persona: `OPERACION_NO_PERMITIDA` si me es visible, `RECURSO_NO_DISPONIBLE` si no (T-01) |
| **Errores** | `BITACORA_CERRADA` · `RECURSO_NO_DISPONIBLE` · `OPERACION_NO_PERMITIDA` · `FECHA_NO_CUBIERTA` (si la bitácora debe crearse y la fecha no está cubierta) · `SOLICITUD_INVALIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` |
| **Auditoría y transacción** | **Trazabilidad del guardado:** si la fecha es pasada, o la bitácora fue reabierta, se genera una única entrada con el resumen anterior y el nuevo y el autor (RN-45, RN-49, IR-35), en la misma transacción. En la jornada actual o futura, guardar el resumen no genera entrada. Siempre se renueva `modificada_en` (RN-18). La primera escritura efectiva sobre una jornada pasada también se audita, y la creación implícita de la bitácora va en la misma entrada (D-02, confirmada); guardar un resumen vacío no es una escritura efectiva |
| **Criterios vinculados** | CA-34, CA-36, CA-62, CA-65, CA-105, CA-107, CA-281, CA-284, CA-293 |
| **Decisiones pendientes** | D-02 y D-03 (confirmadas o aceptadas) |

## M2-03 — Planificar una actividad nueva

| Campo | Contenido |
|---|---|
| **Propósito** | Registrar lo previsto: crea una actividad en estado Pendiente con su planificación original en la jornada indicada |
| **Relacionados** | HU-2.2, HU-2.3 · RF-06, RF-07, RF-38, RF-42, RF-43, RF-63, RF-81, RF-114, RF-122 · RN-07, RN-08, RN-20, RN-27, RN-43, RN-46, RN-71, RN-104, RN-112 |
| **Método y ruta** | `POST /api/v1/mi/bitacoras/{fecha_laboral}/planificaciones` |
| **Entrada** | Ruta: `fecha_laboral`. Cuerpo: `titulo` y `descripcion` (de lo previsto). No admite `estado`, `propietaria_id` ni avances. Cabecera `Idempotency-Key` obligatoria (T-04, decisión técnica aceptada) |
| **Respuesta** | 201: Actividad (con `estado_actual` Pendiente, `origen` planificada) y la Planificación original (`tipo` original) |
| **Validaciones** | Fecha cubierta por mi pertenencia. La actividad empieza en Pendiente y no se admite otro estado (el campo no existe; CA-43). La planificación no es un avance y no altera ningún estado (CA-40). El propietario es la persona que llama y no puede asignarse otro (CA-41). La planificación original no se edita después (RN-104). Si la bitácora de esa fecha no existe, se crea en la misma transacción con las mismas condiciones que M2-01b (D-01, aprobada); la respuesta indica `bitacora_creada`. Si la bitácora está cerrada se exige reabrirla (D-04). Textos (D-03, confirmada): `titulo` obligatorio; `descripcion` opcional; máximos configurables |
| **Autorización** | Propietaria |
| **Errores** | `FECHA_NO_CUBIERTA` · `BITACORA_CERRADA` · `SOLICITUD_INVALIDA` (incluye `estado` u otros campos desconocidos) · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE`. Además: los errores de idempotencia (convenciones 5.3) y, en campos de texto, `CAMPO_OBLIGATORIO` y `TEXTO_DEMASIADO_LARGO` (convenciones 6.2) |
| **Auditoría y transacción** | Una sola transacción crea la actividad y su planificación. En una jornada pasada es una modificación auditable, incluida la primera escritura efectiva (RN-45; D-02, confirmada). En jornada actual o futura, sin entrada |
| **Criterios vinculados** | CA-37, CA-38, CA-39, CA-40, CA-41, CA-42, CA-43, CA-263, CA-295 |
| **Decisiones pendientes** | D-02, D-03 y T-04 (confirmadas o aceptadas) |

## M2-04 — Planificar la continuación de una actividad propia

| Campo | Contenido |
|---|---|
| **Propósito** | Registrar la continuación planificada de una actividad existente para una jornada futura, sin crear otra actividad ni generar ningún avance de ejecución |
| **Relacionados** | HU-2.3, HU-2.9 · RF-42, RF-43, RF-84, RF-85, RF-89, RF-18 · RN-75, RN-76, RN-78, RN-23 |
| **Método y ruta** | `POST /api/v1/mi/actividades/{actividad_id}/continuaciones-planificadas` |
| **Entrada** | Ruta: `actividad_id`. Cuerpo: `fecha_laboral` y `descripcion`. Cabecera `Idempotency-Key` obligatoria (T-04, decisión técnica aceptada) |
| **Respuesta** | 201: Planificación (`tipo` continuacion) y la Actividad, con su `estado_actual` **sin cambios** |
| **Validaciones** | La fecha laboral es posterior a la actual (`FECHA_NO_FUTURA`, RN-76). La actividad es mía, no está marcada por error y no está Completada: una Completada se rechaza con `ACTIVIDAD_COMPLETADA` mientras no se reactive (CA-209; con reactivación vigente se permite, CA-210). **Planificación futura sin avances:** el contrato no crea avances, no entra en la secuencia y no modifica el estado actual (CA-180, CA-181, CA-185, CA-186); el cuerpo no admite `estado`. Si la bitácora de la jornada futura no existe, se crea en la misma transacción (D-01); nunca está cerrada, porque no se cierran jornadas futuras (RN-46). Textos (D-03, confirmada): `descripcion` opcional, con máximo configurable |
| **Autorización** | Propietaria. Actividad de otra persona: 403 si me es visible, 404 si no (CA-183, T-01) |
| **Errores** | `FECHA_NO_FUTURA` · `FECHA_NO_CUBIERTA` · `ACTIVIDAD_COMPLETADA` · `ACTIVIDAD_MARCADA_POR_ERROR` · `OPERACION_NO_PERMITIDA` · `RECURSO_NO_DISPONIBLE` · `SOLICITUD_INVALIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE`. Además: los errores de idempotencia (convenciones 5.3) y, en campos de texto, `CAMPO_OBLIGATORIO` y `TEXTO_DEMASIADO_LARGO` (convenciones 6.2) |
| **Auditoría y transacción** | Sin entrada: no modifica una jornada pasada. Una jornada que solo contiene continuaciones planificadas no puede cerrarse (M3-01) |
| **Criterios vinculados** | CA-43, CA-179, CA-180, CA-181, CA-182, CA-183, CA-185, CA-186, CA-209, CA-210 |
| **Decisiones pendientes** | D-03 y T-04 (confirmadas o aceptadas) |

## M2-05 — Registrar un avance sobre una actividad propia

| Campo | Contenido |
|---|---|
| **Propósito** | Registrar un avance de ejecución: cambia el estado y describe el trabajo. Sirve para continuar la actividad en una jornada posterior y para un avance retroactivo anterior a una finalización |
| **Relacionados** | HU-2.3, HU-2.4, HU-2.5, HU-2.8, HU-2.9, HU-3.1, HU-3.2, HU-3.3, HU-3.5, HU-3.8, HU-3.4, HU-1.4 · RF-08, RF-09, RF-15, RF-40, RF-41, RF-59, RF-60, RF-64, RF-86, RF-88, RF-118, RF-91 · RN-08, RN-17, RN-24, RN-39, RN-41, RN-70, RN-79, RN-108 |
| **Método y ruta** | `POST /api/v1/mi/actividades/{actividad_id}/avances` |
| **Entrada** | Ruta: `actividad_id`, **obligatoria**: es la selección explícita de la actividad que se continúa. Cuerpo: `fecha_laboral`, `estado`, `descripcion`, `motivo_bloqueo` (solo si el estado es Bloqueada). Cabecera `Idempotency-Key` obligatoria (T-04, decisión técnica aceptada) |
| **Respuesta** | 201: el Avance creado (con su fecha laboral, el estado histórico y la descripción) y la Actividad con su `estado_actual` recalculado |
| **Validaciones** | La actividad es mía y no está marcada por error. Estado ∈ {Pendiente, En progreso, Bloqueada, Completada} (CA-48). Bloqueada exige motivo (CA-49), que consta en el avance (CA-51, CA-52). La descripción no puede estar vacía ni ser solo espacios (CA-68, CA-69). La fecha no es futura (CA-182). La fecha está cubierta. **Secuencia (IR-11):** si la actividad está Completada y el avance quedaría tras la finalización, se rechaza con `ACTIVIDAD_COMPLETADA`; hay que reactivar (M3-04) (CA-190, CA-206, CA-207). Un avance con fecha anterior a la finalización se acepta sin reactivar, se inserta en su posición y no altera el estado de uno posterior (CA-78, CA-203, CA-204, CA-205). Varios avances en la misma fecha son válidos (CA-71) y se ordenan por fecha laboral, momento de registro e identificador (CA-74 a CA-76). El avance conserva el estado histórico (CA-45, CA-46). Sin `actividad_id` no hay asociación automática por título (CA-87). **Nueva ejecución frente a corrección histórica (D-04):** solo debe estar abierta la bitácora de la `fecha_laboral` del avance; no se reabren las jornadas anteriores en las que la actividad ya tiene avances (CA-96). Si la bitácora de esa fecha no existe, se crea en la misma transacción con las mismas condiciones que M2-01b (D-01, aprobada); la respuesta indica `bitacora_creada`. Si está cerrada, `BITACORA_CERRADA`. Textos (D-03, confirmada): `descripcion` obligatoria; `motivo_bloqueo` obligatorio si Bloqueada; máximos configurables |
| **Autorización** | Propietaria. Actividad de otra persona: `OPERACION_NO_PERMITIDA` si me es visible, `RECURSO_NO_DISPONIBLE` si no (CA-72, CA-88, CA-208) |
| **Errores** | `ESTADO_INVALIDO` · `MOTIVO_BLOQUEO_OBLIGATORIO` · `DESCRIPCION_OBLIGATORIA` · `FECHA_FUTURA_NO_PERMITIDA` · `FECHA_NO_CUBIERTA` · `ACTIVIDAD_COMPLETADA` · `ACTIVIDAD_MARCADA_POR_ERROR` · `BITACORA_CERRADA` · `OPERACION_NO_PERMITIDA` · `RECURSO_NO_DISPONIBLE` · `SOLICITUD_INVALIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE`. Además: los errores de idempotencia (convenciones 5.3) y, en campos de texto, `CAMPO_OBLIGATORIO` y `TEXTO_DEMASIADO_LARGO` (convenciones 6.2) |
| **Auditoría y transacción** | Una transacción serializada por actividad (DM-01) crea el avance y recalcula `estado_actual` (IR-12, CA-77). Un avance retroactivo sobre una jornada pasada deja una entrada de auditoría de la modificación de esa jornada (RN-45, CA-204). La primera escritura efectiva en una jornada pasada también se audita (D-02, confirmada) |
| **Criterios vinculados** | CA-45, CA-46, CA-47, CA-48, CA-49, CA-50, CA-51, CA-52, CA-66, CA-67, CA-68, CA-69, CA-71, CA-72, CA-74, CA-75, CA-76, CA-77, CA-78, CA-81, CA-86, CA-87, CA-88, CA-96, CA-182, CA-190, CA-203, CA-204, CA-205, CA-206, CA-207, CA-208, CA-284, CA-213, CA-293 |
| **Decisiones pendientes** | D-02, D-03 y T-04 (confirmadas o aceptadas) |

## M2-06 — Registrar una actividad no planificada

| Campo | Contenido |
|---|---|
| **Propósito** | Registrar trabajo no previsto: crea la actividad y su primer avance en una sola operación |
| **Relacionados** | HU-2.6, HU-2.3 · RF-39, RF-42, RF-43, RF-59, RF-80, RF-122 · RN-20, RN-24, RN-69, RN-70, RN-112 |
| **Método y ruta** | `POST /api/v1/mi/actividades-no-planificadas` |
| **Entrada** | Cuerpo: `fecha_laboral`, `titulo`, `estado`, `descripcion`, `motivo_bloqueo` (si Bloqueada). Cabecera `Idempotency-Key` obligatoria (T-04, decisión técnica aceptada) |
| **Respuesta** | 201: la Actividad (`origen` no_planificada, distinta de las planificadas y sin ser un estado adicional) y su primer Avance; `estado_actual` es el del primer avance |
| **Validaciones** | Estado ∈ cuatro estados (CA-54). Bloqueada exige motivo (CA-55, CA-56). Descripción no vacía (CA-58). La fecha no es futura, porque no se registra ejecución futura (CA-43; RN-27). La fecha está cubierta. En la jornada de la fecha actual se acepta cualquiera de los cuatro estados (CA-44). Si la bitácora de esa fecha no existe, se crea en la misma transacción con las mismas condiciones que M2-01b (D-01, aprobada); la respuesta indica `bitacora_creada`. Si está cerrada, `BITACORA_CERRADA` (D-04). Textos (D-03, confirmada): `titulo` y `descripcion` obligatorios; `motivo_bloqueo` obligatorio si Bloqueada; máximos configurables |
| **Autorización** | Propietaria |
| **Errores** | `ESTADO_INVALIDO` · `MOTIVO_BLOQUEO_OBLIGATORIO` · `DESCRIPCION_OBLIGATORIA` · `FECHA_FUTURA_NO_PERMITIDA` · `FECHA_NO_CUBIERTA` · `BITACORA_CERRADA` · `SOLICITUD_INVALIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE`. Además: los errores de idempotencia (convenciones 5.3) y, en campos de texto, `CAMPO_OBLIGATORIO` y `TEXTO_DEMASIADO_LARGO` (convenciones 6.2) |
| **Auditoría y transacción** | Actividad y primer avance en una única transacción atómica (IR-13). En una jornada pasada es una modificación auditable, incluida la primera escritura efectiva (RN-45; D-02, confirmada) |
| **Criterios vinculados** | CA-43, CA-44, CA-53, CA-54, CA-55, CA-56, CA-57, CA-58, CA-296 |
| **Decisiones pendientes** | D-02, D-03 y T-04 (confirmadas o aceptadas) |

## M2-07 — Consultar una actividad propia con sus avances

| Campo | Contenido |
|---|---|
| **Propósito** | Ver una actividad mía completa: planificación original, continuaciones planificadas, avances ordenados y estado actual. Distingue la planificación, el avance de ejecución y el estado actual |
| **Relacionados** | HU-2.2, HU-2.4, HU-2.5, HU-2.7, HU-2.8, HU-2.9, HU-3.1, HU-3.7, HU-3.8, HU-1.4 · RF-14, RF-16, RF-38, RF-61, RF-62, RF-78, RF-81, RF-85, RF-91, RF-93 · RN-42, RN-65, RN-66, RN-71, RN-75, RN-83 |
| **Método y ruta** | `GET /api/v1/mi/actividades/{actividad_id}` |
| **Entrada** | Ruta: `actividad_id` |
| **Respuesta** | 200: Actividad (vista de la propietaria, con `marca_error` si existe), `planificacion_original`, `continuaciones_planificadas[]` (no forman parte de la secuencia), `avances[]` en el orden de la secuencia y `estado_actual` |
| **Validaciones** | Orden: fecha laboral, momento de registro e identificador estable (CA-74 a CA-76). Estado actual: el del último avance de ejecución; Pendiente si no tiene avances (CA-73, CA-77, CA-185, CA-186). Un avance retroactivo no sustituye el estado de uno posterior (CA-78). Cada avance muestra su fecha laboral y el estado que tenía (CA-70, CA-84); el motivo anterior de un bloqueo consta (CA-51, CA-52). Se muestran la fecha laboral, la real y la de modificación (CA-61, CA-62). Una actividad marcada por error sigue siendo consultable (CA-120, CA-121). Tras reactivarla sigue siendo la misma, con su planificación original (CA-191). El título es el mismo en todas las jornadas (CA-265) |
| **Autorización** | Propietaria, con historial completo aunque se haya trasladado (RA-03, RN-83). Las demás personas: M4-04 |
| **Errores** | `RECURSO_NO_DISPONIBLE` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | Lectura. El historial de cambios se consulta con M3-07 |
| **Criterios vinculados** | CA-39, CA-40, CA-47, CA-51, CA-52, CA-61, CA-62, CA-70, CA-73, CA-74, CA-75, CA-76, CA-77, CA-78, CA-82, CA-83, CA-84, CA-120, CA-121, CA-185, CA-186, CA-191, CA-265, CA-212, CA-214 |
| **Decisiones pendientes** | Ninguna |

## M2-08 — Listar mis actividades

| Campo | Contenido |
|---|---|
| **Propósito** | Listar mis actividades para elegir de forma explícita la que se continúa |
| **Relacionados** | HU-3.1, HU-3.2, HU-3.7 · RF-13, RF-64, RF-78 · RN-39, RN-43, RN-32 |
| **Método y ruta** | `GET /api/v1/mi/actividades` |
| **Entrada** | Consulta opcional: `estado` (uno o varios de los cuatro estados, sobre el estado actual), `limite`, `continuar_desde`. No hay búsqueda por texto |
| **Respuesta** | 200: lista paginada de Actividades mías (`id`, `titulo`, `origen`, `estado_actual`) |
| **Validaciones** | Excluye por defecto las actividades marcadas por error (CA-119). Dos actividades con el mismo título o parecidos siguen siendo distintas (CA-85) y cada actividad cuenta una sola vez aunque tenga avances en varias jornadas (CA-82). Paginación según convenciones 6.1 (D-10, decisión técnica aceptada); orden estable: más reciente primero, con el `id` como desempate |
| **Autorización** | Solo mis actividades. Las de otras personas no aparecen (CA-88) |
| **Errores** | `SOLICITUD_INVALIDA` (filtro o parámetro no soportado) · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | Lectura |
| **Criterios vinculados** | CA-82, CA-85, CA-88, CA-119 |
| **Decisiones pendientes** | D-10 (confirmada) |
