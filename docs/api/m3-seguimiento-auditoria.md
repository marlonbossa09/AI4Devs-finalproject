# SMARTWORK — Contratos de la API: M3 Seguimiento de actividades y auditoría

| Campo | Contenido |
|---|---|
| **Estado** | `[PROPUESTO]`, pendiente de revisión |
| **Versión** | 0.5 |
| **Fecha** | 2026-11-06 |
| **Convenciones** | `docs/api/convenciones.md` |

Todas las operaciones de escritura actúan sobre registros propios (RN-23). Ni el supervisor puede reabrir ni corregir bitácoras ajenas (CA-101, CA-107). La continuidad de una actividad se registra con M2-05 (selección explícita de la actividad). HU-3.5 (auditar las modificaciones de jornadas pasadas) no tiene operación propia: es un comportamiento transversal de las operaciones que modifican, descrito en cada contrato.

## M3-01 — Cerrar mi jornada

| Campo | Contenido |
|---|---|
| **Propósito** | Cerrar manualmente mi bitácora de una fecha laboral |
| **Relacionados** | HU-3.3, HU-2.3, HU-3.4 · RF-17, RF-18, RF-19, RF-44, RF-68, RF-119 · RN-10, RN-21, RN-22, RN-46, RN-23, RN-109 |
| **Método y ruta** | `POST /api/v1/mi/bitacoras/{fecha_laboral}/cierre` |
| **Entrada** | Ruta: `fecha_laboral`. Sin cuerpo. Cabecera `Idempotency-Key` obligatoria (T-04, decisión técnica aceptada) |
| **Respuesta** | 200 con la Bitácora en estado `cerrada` y `cerrada_en`. Las actividades conservan su estado (CA-95) |
| **Validaciones** | El cierre es solo manual: ninguna condición lo dispara por el paso del tiempo (CA-89). Se exige al menos una actividad **creada en esa jornada** o **continuada en ella** (con al menos un avance de esa fecha laboral) y un resumen con texto, no vacío ni formado solo por espacios (CA-90 a CA-94). Una continuación planificada no cuenta como actividad continuada (CA-184). Se admiten actividades en cualquiera de los cuatro estados, sin modificarlas (CA-95). No se cierra una jornada de fecha futura (CA-97). Las actividades no completadas siguen disponibles para recibir avances en una jornada posterior sin copiarse (CA-96). No crea la bitácora: si no existe, `RECURSO_NO_DISPONIBLE` (D-01). Las actividades marcadas como registradas por error no cuentan para las condiciones de cierre (RN-109, D-04b aprobada). La comprobación considera todas las actividades válidas creadas o continuadas en esa fecha laboral, incluidas las iniciadas en jornadas anteriores |
| **Autorización** | Propietaria. La jornada de otra persona no se puede cerrar (CA-98) |
| **Errores** | `CONDICIONES_DE_CIERRE_NO_CUMPLIDAS` (con `detalles` de qué falta) · `FECHA_FUTURA_NO_PERMITIDA` · `BITACORA_CERRADA` si ya está cerrada · `RECURSO_NO_DISPONIBLE` · `OPERACION_NO_PERMITIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE`. Además: los errores de idempotencia (convenciones 5.3) y, en campos de texto, `CAMPO_OBLIGATORIO` y `TEXTO_DEMASIADO_LARGO` (convenciones 6.2) |
| **Auditoría y transacción** | Una entrada de auditoría por cierre, para reconstruir los ciclos de cierre y reapertura (RN-103, CA-266). Transacción atómica. El cierre se serializa con las marcas de error de las actividades de esa jornada (M3-05), para que no se cierre y se invalide a la vez |
| **Criterios vinculados** | CA-89, CA-90, CA-91, CA-92, CA-93, CA-94, CA-95, CA-96, CA-97, CA-98, CA-184, CA-266, CA-283 |
| **Decisiones pendientes** | Ninguna (D-04b aprobada). T-04 (confirmada) |

## M3-02 — Reabrir mi bitácora cerrada

| Campo | Contenido |
|---|---|
| **Propósito** | Reabrir mi bitácora cerrada, indicando un motivo, para poder corregirla |
| **Relacionados** | HU-3.4, HU-3.6 · RF-20, RF-21, RF-71, RF-113, RNF-02 · RN-01, RN-19, RN-23, RN-50, RN-103 |
| **Método y ruta** | `POST /api/v1/mi/bitacoras/{fecha_laboral}/reapertura` |
| **Entrada** | Ruta: `fecha_laboral`. Cuerpo: `motivo` (obligatorio). Cabecera `Idempotency-Key` obligatoria (T-04, decisión técnica aceptada) |
| **Respuesta** | 200 con la Bitácora en estado `abierta` |
| **Validaciones** | Sin motivo no se permite (CA-100). La bitácora debe estar cerrada. Mientras no se reabra, no se corrige (`BITACORA_CERRADA` en M2-02 y M3-03). Solo opera sobre una bitácora existente; no la crea (D-01). Reabrir una jornada no obliga a reabrir otras (D-04) |
| **Autorización** | Propietaria. La bitácora cerrada de otra persona no se reabre, tampoco por un supervisor (CA-101) |
| **Errores** | `MOTIVO_OBLIGATORIO` · `BITACORA_NO_CERRADA` · `RECURSO_NO_DISPONIBLE` · `OPERACION_NO_PERMITIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE`. Además: los errores de idempotencia (convenciones 5.3) y, en campos de texto, `CAMPO_OBLIGATORIO` y `TEXTO_DEMASIADO_LARGO` (convenciones 6.2) |
| **Auditoría y transacción** | Una entrada con el motivo (CA-109), autor, momento, valor anterior y nuevo, en la misma transacción que el cambio de estado. Cada reapertura y cada cierre quedan reconstruibles (CA-266) |
| **Criterios vinculados** | CA-99, CA-100, CA-101, CA-102, CA-109, CA-266 |
| **Decisiones pendientes** | D-03 y T-04 (confirmadas o aceptadas) |

## M3-03 — Corregir un avance ya registrado

División técnica del catálogo: el resumen se corrige con M2-02 (con la bitácora abierta), y el avance con este contrato.

| Campo | Contenido |
|---|---|
| **Propósito** | Corregir el estado, la descripción o el motivo de bloqueo de un avance mío ya registrado, sin crear un avance nuevo y sin reescribir silenciosamente el historial |
| **Relacionados** | HU-3.4, HU-3.5, HU-2.9, HU-3.8, HU-3.7 · RF-21, RF-25, RF-82, RF-90, RF-101, RF-102, RF-103, RF-118, RF-123 · RN-19, RN-45, RN-67, RN-80, RN-91, RN-92, RN-93, RN-108, RN-113 |
| **Método y ruta** | `PATCH /api/v1/mi/avances/{avance_id}` |
| **Entrada** | Ruta: `avance_id`. Cuerpo: al menos uno de `estado`, `descripcion`, `motivo_bloqueo`. **No se acepta** `fecha_laboral` (la reubicación de avances no está aprobada, PP-44), ni el cambio de la planificación ni del título (RN-104). Cabecera `Idempotency-Key` obligatoria (T-04, decisión técnica aceptada) |
| **Respuesta** | 200: el Avance corregido, la Actividad con su `estado_actual` recalculado y un indicador de si el estado actual cambió |
| **Validaciones** | **Se valida la secuencia completa de la actividad** con el cambio aplicado (RN-91, IR-11): no puede quedar un avance de ejecución tras una finalización sin reactivación válida (RN-92, CA-236); cambiar el estado de una finalización es válido solo si la secuencia resultante lo sigue siendo (CA-238). Estado entre los cuatro; Bloqueada exige motivo; la descripción no queda vacía. Nunca se crea una reactivación automática (CA-239). La corrección es distinta de registrar un avance nuevo (CA-211). Solo se exige que esté abierta la bitácora del propio avance: no se reabren otras jornadas (D-04). La corrección es una modificación histórica, distinta de registrar una ejecución nueva (convenciones 5.2). **D-05 (confirmada):** si la actividad está marcada por error no se corrigen sus avances; primero debe revertirse la marca con M3-06, que no exige reabrir la jornada, y después corregir con la bitácora del avance abierta. Una corrección con los valores ya vigentes no hace nada: 200 sin cambios ni entrada (T-04). Textos (D-03): `descripcion` no vacía y con máximo configurable |
| **Autorización** | Propietaria, y la bitácora del avance debe estar abierta. Otra persona, incluido un supervisor, no corrige (CA-101, CA-107) |
| **Errores** | `SECUENCIA_INVALIDA` (no modifica nada: CA-237) · `ESTADO_INVALIDO` · `MOTIVO_BLOQUEO_OBLIGATORIO` · `DESCRIPCION_OBLIGATORIA` · `BITACORA_CERRADA` · `SOLICITUD_INVALIDA` (campo no modificable) · `RECURSO_NO_DISPONIBLE` · `OPERACION_NO_PERMITIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE`. Además: los errores de idempotencia (convenciones 5.3) y, en campos de texto, `CAMPO_OBLIGATORIO` y `TEXTO_DEMASIADO_LARGO` (convenciones 6.2) |
| **Auditoría y transacción** | Transacción atómica, serializada por actividad (DM-01): cambio, entrada de auditoría y recálculo del estado actual. Una única entrada con el valor anterior y el nuevo, incluido el estado actual anterior y nuevo si varía (IR-35). Toda corrección de un avance queda auditada (CA-103, CA-79). Si el avance no es el último, el estado actual no cambia pero la corrección se audita igual (CA-80) |
| **Criterios vinculados** | CA-79, CA-80, CA-102, CA-103, CA-104, CA-105, CA-107, CA-211, CA-236, CA-237, CA-238, CA-239, CA-101, CA-284, CA-297, CA-298 |
| **Decisiones pendientes** | D-03, D-05 y T-04 (confirmadas o aceptadas) |

### Corrección según el estado de la bitácora y la fecha laboral

| Bitácora del avance | Fecha laboral | Resultado | Auditoría |
|---|---|---|---|
| Abierta | Actual | Se permite | Sí: toda corrección de un avance se audita (CA-103) |
| Abierta | Pasada | Se permite | Sí: corrección y modificación de jornada pasada, en una sola entrada (RN-45, IR-35) |
| Cerrada | Cualquiera | `BITACORA_CERRADA`: se reabre antes con M3-02 | La reapertura y la corrección constan (CA-102) |
| Cualquiera | Futura | No hay avances de ejecución futuros (RN-27); no aplica | — |

## M3-04 — Reactivar una actividad Completada

| Campo | Contenido |
|---|---|
| **Propósito** | Reactivar de forma explícita una actividad Completada para que reciba nuevos avances, sin duplicarla |
| **Relacionados** | HU-3.8 · RF-41, RF-59, RF-65, RF-86, RF-110 · RN-24, RN-40, RN-68, RN-70, RN-73, RN-74, RN-100 |
| **Método y ruta** | `POST /api/v1/mi/actividades/{actividad_id}/reactivacion` |
| **Entrada** | Ruta: `actividad_id`. Cuerpo: `fecha_laboral`, `estado` (Pendiente, En progreso o Bloqueada), `descripcion`, `motivo_bloqueo` (si Bloqueada). Cabecera `Idempotency-Key` obligatoria (T-04, decisión técnica aceptada) |
| **Respuesta** | 201: el Avance de reactivación (`es_reactivacion` verdadero) y la misma Actividad con su `estado_actual` |
| **Validaciones** | La actividad es mía, está Completada y no está marcada por error. La fecha no es anterior a la fecha laboral F del avance de finalización (CA-188), puede ser la misma F con un momento de registro posterior (CA-187), y no es futura (CA-189). El estado es uno de los tres permitidos; Completada se rechaza. Bloqueada exige motivo (CA-128, CA-270, CA-271). Descripción no vacía (CA-129). La reactivación es un avance de la secuencia, posterior al que la completó, y puede registrarse en una jornada pasada posterior a F (CA-126, CA-192). La actividad conserva identidad, planificación original y avances (CA-191). La bitácora de la `fecha_laboral` de la reactivación debe estar abierta (D-04) y se crea si no existe (D-01); no se exige reabrir la jornada de la finalización ni otras anteriores, porque reactivar es una ejecución nueva. Textos (D-03): `descripcion` obligatoria; `motivo_bloqueo` obligatorio si Bloqueada; máximos configurables |
| **Autorización** | Propietaria (CA-127) |
| **Errores** | `ACTIVIDAD_NO_COMPLETADA` · `ESTADO_INVALIDO` · `MOTIVO_BLOQUEO_OBLIGATORIO` · `DESCRIPCION_OBLIGATORIA` · `FECHA_FUTURA_NO_PERMITIDA` · `SECUENCIA_INVALIDA` (fecha anterior a F) · `BITACORA_CERRADA` · `ACTIVIDAD_MARCADA_POR_ERROR` · `RECURSO_NO_DISPONIBLE` · `OPERACION_NO_PERMITIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE`. Además: los errores de idempotencia (convenciones 5.3) y, en campos de texto, `CAMPO_OBLIGATORIO` y `TEXTO_DEMASIADO_LARGO` (convenciones 6.2) |
| **Auditoría y transacción** | Transacción atómica y serializada por actividad: avance, entrada de auditoría y recálculo del estado actual (CA-125) |
| **Criterios vinculados** | CA-124, CA-125, CA-126, CA-127, CA-128, CA-129, CA-187, CA-188, CA-189, CA-190, CA-191, CA-192, CA-269, CA-270, CA-271 |
| **Decisiones pendientes** | D-02, D-03 y T-04 (confirmadas o aceptadas) |

## M3-05 — Marcar una actividad como registrada por error

| Campo | Contenido |
|---|---|
| **Propósito** | Marcar de forma lógica una actividad mía creada por equivocación, sin borrarla |
| **Relacionados** | HU-3.7 · RF-77, RF-78, RF-119 · RN-59, RN-60, RN-23, RN-109 |
| **Método y ruta** | `POST /api/v1/mi/actividades/{actividad_id}/marca-error` |
| **Entrada** | Ruta: `actividad_id`. Cuerpo: `motivo` (obligatorio). Cabecera `Idempotency-Key` obligatoria (T-04, decisión técnica aceptada) |
| **Respuesta** | 200: la Actividad con `marca_error`. No es un quinto estado: su estado sigue siendo uno de los cuatro (CA-121) |
| **Validaciones** | Exige motivo (CA-116). Solo procede si la actividad no tiene avances en jornadas posteriores a su creación (CA-115, CA-117). Si ya está marcada, se rechaza. Desde la marca, la actividad no aparece en las vistas operativas ni en los recuentos (CA-119) y no admite avances ni reactivación (IR-18), pero sigue consultable en el historial y la auditoría (CA-120). **Cambio lógico de validez, no corrección de contenido (RN-109, D-04b aprobada):** marcar no obliga a reabrir la bitácora de origen. Se audita y se valida antes la integridad de los registros relacionados: (1) por RN-59, la actividad no tiene avances posteriores a su creación; (2) sus continuaciones planificadas se conservan vinculadas a la actividad y quedan fuera de las vistas operativas mientras la marca esté vigente (IR-18); (3) **si la bitácora de origen está cerrada, se comprueban sus condiciones de cierre sin contar esta actividad, considerando todas las actividades válidas creadas o continuadas en esa fecha laboral, incluidas las iniciadas en jornadas anteriores. Si la jornada perdería alguna condición, la operación se rechaza con `MARCA_INVALIDARIA_CIERRE` y no se modifica ningún registro**; si otras actividades válidas la conservan, la marca se aplica sin reapertura. Si la jornada de origen está abierta no hay comprobación de cierre. Para marcar una actividad que la comprobación rechaza, la propietaria reabre la jornada (M3-02), marca y vuelve a cerrar si cumple las condiciones |
| **Autorización** | Propietaria (CA-118) |
| **Errores** | `MOTIVO_OBLIGATORIO` · `MARCA_NO_PROCEDE` · `MARCA_INVALIDARIA_CIERRE` · `ACTIVIDAD_MARCADA_POR_ERROR` · `RECURSO_NO_DISPONIBLE` · `OPERACION_NO_PERMITIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE`. Además: los errores de idempotencia (convenciones 5.3) y, en campos de texto, `CAMPO_OBLIGATORIO` y `TEXTO_DEMASIADO_LARGO` (convenciones 6.2) |
| **Auditoría y transacción** | Una entrada con el motivo, atómica con el cambio. La entrada pertenece a la jornada de origen de la actividad (IR-36). No corrige el contenido de la bitácora: no renueva su `modificada_en`; la trazabilidad es la entrada. La comprobación de integridad y la marca se hacen en la misma transacción, serializada con el cierre de la bitácora de origen (M3-01) |
| **Criterios vinculados** | CA-115, CA-116, CA-117, CA-118, CA-119, CA-120, CA-121, CA-287, CA-288, CA-289 |
| **Decisiones pendientes** | Ninguna (D-04b aprobada). D-03 y T-04 (confirmadas o aceptadas) |

## M3-06 — Revertir la marca de error

| Campo | Contenido |
|---|---|
| **Propósito** | Retirar la marca de error de una actividad mía; vuelve a las vistas operativas y a los recuentos |
| **Relacionados** | HU-3.7 · RF-79, RF-119 · RN-60, RN-23, RN-109 |
| **Método y ruta** | `POST /api/v1/mi/actividades/{actividad_id}/marca-error/reversion` |
| **Entrada** | Ruta: `actividad_id`. Sin cuerpo (ninguna regla exige un motivo para revertir). Cabecera `Idempotency-Key` obligatoria (T-04, decisión técnica aceptada) |
| **Respuesta** | 200: la Actividad sin marca vigente |
| **Validaciones** | Debe haber una marca vigente. Revertir la marca es un cambio lógico de validez: no obliga a reabrir la bitácora de origen. No puede invalidar las condiciones de cierre, porque devuelve una actividad a la jornada y no la quita. La entrada de auditoría pertenece a la jornada de origen. **Integridad de los registros relacionados (RN-109):** comprueba que hay una marca vigente, que la actividad no tiene avances posteriores a su creación (IR-18) y que su bitácora de origen existe. Tras la reversión la actividad vuelve a contar para las condiciones de cierre; revertir no puede invalidar un cierre |
| **Autorización** | Propietaria (CA-123) |
| **Errores** | `MARCA_NO_VIGENTE` · `RECURSO_NO_DISPONIBLE` · `OPERACION_NO_PERMITIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE`. Además: los errores de idempotencia (convenciones 5.3) y, en campos de texto, `CAMPO_OBLIGATORIO` y `TEXTO_DEMASIADO_LARGO` (convenciones 6.2) |
| **Auditoría y transacción** | Una entrada de auditoría con la marca anterior (CA-122); atómica con el cambio |
| **Criterios vinculados** | CA-122, CA-123, CA-290 |
| **Decisiones pendientes** | T-04 (confirmada) |

## M3-07 — Consultar la auditoría de un registro

| Campo | Contenido |
|---|---|
| **Propósito** | Ver qué se cambió en un registro: autor, momento, operación, motivo, valor anterior y nuevo |
| **Relacionados** | HU-3.6, HU-3.4, HU-3.5, HU-3.7, HU-2.7 · RF-22, RF-71, RF-72, RF-73, RF-113, RF-120 · RN-49, RN-50, RN-51, RN-52, RN-36, RN-103, RN-110 |
| **Método y ruta** | `GET /api/v1/auditoria` |
| **Entrada** | Consulta: `tipo_objeto` (bitácora, actividad, avance o planificación) y `objeto_id`, obligatorios; `operacion` opcional; `limite` y `continuar_desde`. No existe consulta sin objeto: no hay listado global de la auditoría |
| **Respuesta** | 200: lista paginada de EntradasAuditoría en orden cronológico |
| **Validaciones** | Cada entrada contiene lo necesario para reconstruir el cambio (CA-108). Permite reconstruir cada corrección (CA-104) y cada ciclo de cierre y reapertura (CA-266). La reapertura consta con su motivo (CA-109). Una operación que modifica varios campos aparece como una sola entrada (CA-267). Registros corregidos o con reapertura no se borran: la operación consta siempre (CA-114). Una actividad marcada por error sigue siendo consultable (CA-120). Solo se devuelven entradas de operaciones de dominio hechas por personas. Las entradas de provisión administrativa permanecen separadas y no aparecen en esta consulta, ni para la propietaria ni para un supervisor (D-11, aprobada). El filtro de autorización se aplica antes de construir la respuesta (convenciones 3.3) |
| **Autorización** | La propietaria del registro y el supervisor autorizado del equipo al que pertenece el registro por su fecha laboral (RA-10, CA-110, CA-111). Un compañero que no es ninguno de los dos, o el supervisor de otro equipo, recibe `RECURSO_NO_DISPONIBLE` (CA-112, CA-113) |
| **Errores** | `RECURSO_NO_DISPONIBLE` · `SOLICITUD_INVALIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | Lectura. La consulta de la auditoría no genera entradas |
| **Criterios vinculados** | CA-65, CA-104, CA-106, CA-108, CA-109, CA-110, CA-111, CA-112, CA-113, CA-114, CA-120, CA-266, CA-267, CA-285, CA-286 |
| **Decisiones pendientes** | Ninguna en el contrato. D-11 aprobada: la auditoría de provisión se define aparte con PA-12 y PA-06. La retención (PA-06) no se asume |
