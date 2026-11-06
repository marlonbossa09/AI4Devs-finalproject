# SMARTWORK — Contratos de la API: convenciones comunes

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]`, pendiente de revisión por la persona responsable del producto |
| **Versión** | 0.5 |
| **Fecha** | 2026-11-06 |
| **Base** | `docs/producto/alcance-mvp.md` (0.12), `docs/producto/prd.md` (0.10), `docs/backlog/indice.md` (0.7), `docs/modelo-datos/modelo-datos.md` (0.5) y ADR-001 |
| **Alcance** | Convenciones comunes a los contratos de M2, M3 y M4 |
| **Decisiones aprobadas incorporadas** | T-01, T-03, D-01, D-04, D-04b, D-06, D-09 y D-11 (sección 8 y `indice.md`) |
| **Confirmadas posteriormente** | D-02, D-03, D-05, D-07 y D-08 (sincronizadas con el alcance). D-10, T-02 y T-04 son decisiones técnicas aceptadas |

Estas convenciones no son requisitos del producto. Son propuestas técnicas para expresar los requisitos confirmados. Ninguna crea una regla de negocio: cuando un contrato necesita una regla que no está especificada, la registra como decisión pendiente en lugar de resolverla.

## 1. Lo que estos contratos no deciden

- **Mecanismo de identificación (PA-12).** Los contratos suponen que existe una persona identificada (RN-61). No definen cómo se identifica ni cómo se transporta esa identidad. No mencionan cabeceras, credenciales ni sesiones.
- **Proveedor de IA (PA-09).** Fuera de M2, M3 y M4. AWS Bedrock sigue siendo solo un candidato.
- **Retención de la auditoría (PA-06), límites de rendimiento y volumen (PA-13).** Cada contrato indica donde dependen de ellos.

## 2. Estilo

| Aspecto | Propuesta |
|---|---|
| Estilo | REST sobre HTTP, con representaciones en JSON (UTF-8) |
| Prefijo y versión | `/api/v1` (T-03, aprobada) |
| Recursos | Nombres en español, en minúsculas y con guiones |
| Persona que actúa | Se deduce de la identidad. Las operaciones de escritura cuelgan de `/mi/...` y solo actúan sobre registros propios. Ninguna acepta un identificador de persona para actuar en nombre de otra |
| Fecha laboral | `AAAA-MM-DD`, interpretada en la zona horaria de la organización (RN-44) |
| Momentos reales | ISO 8601 en UTC |
| Identificadores | Cadenas opacas, aleatorias y sin información incrustada (ni secuencia, ni fecha, ni equipo, ni persona) |
| Fecha actual | La calcula siempre el servidor en la zona de la organización al ejecutar la operación (DM-06). Ningún contrato acepta una «fecha de hoy» del cliente |
| Campos desconocidos | Se rechazan con `SOLICITUD_INVALIDA`. Así se hace verificable que no existen búsquedas, ediciones ni campos que el producto no contempla |

## 3. Autorización

- Toda decisión de acceso la toma la política de autorización centralizada del servidor (ADR-001), a partir de la función «equipo en una fecha» (DM-04). Los controles no se duplican en la interfaz.
- Cada contrato cita las reglas de autorización del modelo (RA-01 a RA-12) que aplica.
- Una persona con el acceso desactivado (IR-37) o sin pertenencia vigente (IR-38) no puede ejecutar ninguna operación.
- Un supervisor con acceso desactivado no ejerce funciones de supervisión (RA-12).

### 3.1 Respuesta ante registros inexistentes o no autorizados (T-01, aprobada)

| Situación | Respuesta |
|---|---|
| El recurso no existe, o existe pero la persona no está autorizada a conocerlo | Respuesta pública **indistinguible**: mismo estado HTTP (404), mismo `codigo` (`RECURSO_NO_DISPONIBLE`), mismo `mensaje` fijo («El recurso solicitado no está disponible»), `detalles` vacío y misma estructura. Nada en el mensaje, en los detalles ni en la forma de la respuesta revela existencia, tipo, equipo ni propietaria |
| El recurso es visible para la persona, pero la operación no le está permitida (por ejemplo, intentar modificar la bitácora de un compañero de su equipo, que puede leer) | `OPERACION_NO_PERMITIDA` (403). Se reserva a recursos cuya existencia ya es visible para quien consulta |
| La persona no puede operar (acceso desactivado o sin pertenencia vigente) | `ACCESO_DESACTIVADO` o `SIN_PERTENENCIA_VIGENTE` (403), que solo informan de su propia situación |
| Un listado filtrado por persona o fechas | Devuelve solo lo autorizado. Un filtro sin resultados autorizados da una lista vacía y no un error |

Los mensajes de error nunca incluyen títulos, descripciones, motivos, nombres de equipo ni contenido de otros registros. No se garantiza la igualdad de tiempos de respuesta: un canal de temporización entre «inexistente» y «no autorizado» queda como riesgo residual para el diseño de seguridad.

### 3.2 Orden de evaluación

Para que ninguna validación revele existencia, toda operación evalúa en este orden y se detiene en el primer fallo:

1. Persona identificada (`NO_IDENTIFICADA`).
2. La persona puede operar (`ACCESO_DESACTIVADO`, `SIN_PERTENENCIA_VIGENTE`).
3. Formato de los parámetros de ruta y de consulta (`SOLICITUD_INVALIDA`), sin consultar el recurso.
4. Visibilidad del recurso (`RECURSO_NO_DISPONIBLE`).
5. Permiso sobre un recurso visible (`OPERACION_NO_PERMITIDA`).
6. Validación del cuerpo y reglas de negocio o de estado (409 y 422).

Así, una petición con cuerpo inválido sobre un recurso no disponible produce `RECURSO_NO_DISPONIBLE`, no un error de validación.

### 3.3 Filtrado antes de construir la respuesta

El predicado de autorización (la función «equipo en una fecha», DM-04) se aplica al seleccionar los datos, no al presentarlos. Un registro no autorizado no llega a la construcción de la respuesta. Esto incluye los recuentos, las agrupaciones y el cálculo del estado al corte, que se hacen solo sobre registros autorizados, y los datos que se preparen para los informes (RA-09).

## 4. Errores (T-02, decisión técnica aceptada)

Estructura: `codigo` (cadena estable), `mensaje` (texto para personas) y `detalles` (lista opcional de pares campo y motivo). Los errores del servidor (5xx) no incluyen detalles internos y llevan un identificador de correlación.

**Criterio de coherencia entre clases HTTP:**

| Clase | Significado | Se usa para |
|---|---|---|
| 400 | Petición mal formada | Sintaxis, campo desconocido o no modificable, parámetro no soportado, paginación fuera de rango, falta de la clave de idempotencia |
| 401 | Sin persona identificada | RN-61; el mecanismo está en PA-12 |
| 403 | Prohibido | La persona no puede operar, u operación prohibida sobre un recurso visible |
| 404 | No disponible | Recurso inexistente o no autorizado, de forma indistinguible (T-01) |
| 409 | Conflicto con el **estado actual** del recurso o con otra operación en curso | Bitácora cerrada, actividad Completada o marcada, secuencia inválida, condiciones de cierre |
| 422 | Petición bien formada que incumple una regla sobre **sus propios datos** | Fechas, estados, textos obligatorios o demasiado largos, motivos |
| 429, 500, 503 | Limitación de solicitudes (reservado), fallo interno, servicio no disponible | — |

| Código | HTTP | Cuándo | Origen |
|---|---|---|---|
| `SOLICITUD_INVALIDA` | 400 | Formato incorrecto, campo desconocido o no modificable, parámetro no soportado, paginación fuera de rango | Técnica |
| `CLAVE_IDEMPOTENCIA_OBLIGATORIA` | 400 | Falta `Idempotency-Key` en una operación que la exige | T-04 |
| `NO_IDENTIFICADA` | 401 | No hay persona identificada | RN-61; PA-12 |
| `ACCESO_DESACTIVADO` | 403 | El acceso de la persona está desactivado | RN-96, IR-37 |
| `SIN_PERTENENCIA_VIGENTE` | 403 | La persona no tiene pertenencia vigente | RN-97, IR-38 |
| `OPERACION_NO_PERMITIDA` | 403 | El registro es visible pero la operación no está permitida | RN-23, RN-13 |
| `RECURSO_NO_DISPONIBLE` | 404 | Inexistente o no autorizado: respuesta idéntica | T-01 |
| `BITACORA_CERRADA` | 409 | Se intenta modificar el contenido de una jornada cerrada sin reabrirla | RN-19; D-04 |
| `BITACORA_NO_CERRADA` | 409 | Se intenta reabrir una bitácora que no está cerrada | RN-19 |
| `ACTIVIDAD_COMPLETADA` | 409 | La operación exige reactivar antes la actividad Completada | RN-73, RN-78, RN-79 |
| `ACTIVIDAD_NO_COMPLETADA` | 409 | Se intenta reactivar una actividad que no está Completada | RN-40 |
| `ACTIVIDAD_MARCADA_POR_ERROR` | 409 | La actividad tiene una marca de error vigente | RN-59, IR-18; D-05 |
| `MARCA_NO_VIGENTE` | 409 | Se intenta revertir una marca que no existe | RN-60 |
| `MARCA_NO_PROCEDE` | 409 | La actividad tiene avances en jornadas posteriores a su creación | RN-59 |
| `MARCA_INVALIDARIA_CIERRE` | 409 | Marcar haría perder a una jornada cerrada sus condiciones de cierre | RN-109 (D-04b, aprobada) |
| `CONDICIONES_DE_CIERRE_NO_CUMPLIDAS` | 409 | No se cumplen las condiciones de cierre; `detalles` indica cuáles | RN-21 |
| `SECUENCIA_INVALIDA` | 409 | El resultado violaría la secuencia de avances; no se modifica nada | RN-91, RN-92, IR-11 |
| `OPERACION_EN_CURSO` | 409 | Otra petición con la misma clave de idempotencia sigue en curso | T-04 |
| `FECHA_NO_CUBIERTA` | 422 | La fecha laboral no está cubierta por una pertenencia de la persona | RN-94, IR-29 |
| `FECHA_FUTURA_NO_PERMITIDA` | 422 | Se intenta registrar ejecución con fecha futura o cerrar una jornada futura | RN-27, RN-46, RN-74 |
| `FECHA_NO_FUTURA` | 422 | Una continuación planificada exige una fecha posterior a la actual | RN-76 |
| `ESTADO_INVALIDO` | 422 | El estado no es uno de los cuatro o no está permitido en esa operación | RN-08, RN-46, RN-100 |
| `DESCRIPCION_OBLIGATORIA` | 422 | Descripción vacía o formada solo por espacios | RN-70 |
| `MOTIVO_BLOQUEO_OBLIGATORIO` | 422 | Estado Bloqueada sin motivo | RN-24 |
| `MOTIVO_OBLIGATORIO` | 422 | Falta el motivo de una reapertura o de una marca de error | RN-50, RN-59 |
| `CAMPO_OBLIGATORIO` | 422 | Falta un campo de texto obligatorio; `detalles` indica cuál | D-03 |
| `TEXTO_DEMASIADO_LARGO` | 422 | El texto supera el máximo configurado; `detalles` indica campo y máximo | D-03 |
| `CLAVE_IDEMPOTENCIA_REUTILIZADA` | 422 | La misma clave se usó con otra petición distinta | T-04 |
| `CREDENCIALES_INVALIDAS` | 401 | Identificador o contraseña incorrectos; la respuesta es la misma en ambos casos | RN-61; ADR-002 |
| `CODIGO_NO_VALIDO` | 422 | El código de un solo uso es desconocido, está usado, caducado, invalidado o pertenece a un acceso desactivado; la respuesta es la misma en todos los casos | RN-35; DD-05; ADR-002 |
| `CONTRASENA_NO_VALIDA` | 422 | La contraseña nueva incumple la política; `detalles` indica la regla sin revelar listas | RNF-08; ADR-002 |
| `FECHA_EFECTIVA_INVALIDA` | 422 | La fecha efectiva de una operación de pertenencia no es posterior a la fecha actual, o el inicio de la primera pertenencia es anterior a ella | RN-95, RN-106 |
| `PERTENENCIA_INVALIDA` | 409 | La línea temporal resultante incumple una regla; `detalles.motivo` indica cuál (solape, hueco, equipo sin supervisor, supervisor duplicado o en otro equipo) | RN-94, RN-98, RN-99 |
| `IDENTIFICADOR_DUPLICADO` | 409 | El identificador de acceso ya existe (solo para la provisión) | ADR-002 |
| `ACCESO_YA_DESACTIVADO` | 409 | El acceso ya estaba desactivado | RN-96 |
| `ACCESO_DESACTIVADO_ADMINISTRATIVAMENTE` | 409 | La orden no procede porque el acceso está desactivado (por ejemplo, emitir un código de recuperación) | DD-05 |
| `OPERADOR_NO_AUTORIZADO` | — | La persona operadora no está autorizada para la orden (solo órdenes de provisión) | RN-33; ADR-002 |
| `INFORME_EXCEDE_LIMITES` | 422 | El informe superaría un límite configurado (período, registros o tamaño); se rechaza antes de generar | ADR-003 |
| `INFORME_NO_GENERADO` | 503 | El informe no pudo generarse; no se devuelve contenido parcial. Indica si se puede reintentar | RN-58 |
| `DEMASIADAS_SOLICITUDES` | 429 | Limitación de solicitudes (reservado; la política se define con PA-12 y PA-13) | Técnica |
| `ERROR_INTERNO`, `SERVICIO_NO_DISPONIBLE` | 500, 503 | Fallos del servidor | Técnica |

Una operación rechazada no modifica datos ni deja entrada de auditoría (IR-24, RN-93).

## 5. Auditoría y transacciones

- Toda operación que modifica es atómica con su entrada de auditoría y, cuando procede, con el recálculo del estado actual (IR-24).
- El registro y la corrección de avances de una misma actividad se serializan (DM-01). `registrado_en` e `id` los asigna el servidor.
- Cada operación genera una única entrada de auditoría con los valores anterior y nuevo (IR-35).
- La modificación de una jornada pasada se audita, esté abierta o cerrada (RN-45). Si el primer registro del contenido de una jornada pasada genera entrada de auditoría está pendiente (PA-06, decisión D-02).
- No existe ninguna operación de borrado de bitácoras, actividades, planificaciones ni avances (RN-52, IR-26).

### 5.1 Apertura de bitácoras: explícita e implícita (D-01, aprobada)

- La unicidad por persona y fecha laboral (IR-01) es absoluta: ninguna vía crea una segunda bitácora.
- **Explícita:** M2-01b.
- **Implícita:** las operaciones que registran contenido en una fecha crean la bitácora de esa fecha en la misma transacción, con las mismas condiciones que M2-01b (fecha cubierta por una pertenencia): M2-02, M2-03, M2-04, M2-05, M2-06 y M3-04. La respuesta incluye `bitacora_creada`.
- Las consultas (M2-01a, M2-07, M2-08), el cierre (M3-01) y la reapertura (M3-02) **nunca crean** una bitácora; si no existe, responden `RECURSO_NO_DISPONIBLE`.
- **Idempotencia verificable de M2-01b:** (1) si la bitácora no existe, responde 201 con `creada: true`; (2) si existe, responde 200 con `creada: false` y la misma bitácora (mismo `id`, `creada_en`, `modificada_en`, `estado` y `resumen`), sin modificarla, sin entrada de auditoría y sin reabrirla si estaba cerrada; (3) N aperturas de la misma fecha, también simultáneas, dejan exactamente una bitácora, y solo una recibe 201.

### 5.2 Nueva ejecución frente a corrección histórica (D-04, aprobada)

Modificar el contenido de una jornada cerrada exige reabrirla antes (M3-02). Solo cuenta la jornada cuyo contenido se modifica; ninguna operación obliga a reabrir otras jornadas.

| Tipo | Operación | Jornada que debe estar abierta | ¿Reabrir jornadas anteriores? | Auditoría |
|---|---|---|---|---|
| Nueva ejecución | M2-05 avance | La de su `fecha_laboral` | No: una actividad con avances en jornadas cerradas se continúa en una jornada abierta (CA-96) | Si la jornada es pasada (RN-45) |
| Nueva ejecución | M3-04 reactivación | La de su `fecha_laboral` | No, tampoco la de la finalización | Sí (CA-125) |
| Nueva ejecución | M2-03, M2-06 | La de su `fecha_laboral` | No | Si la jornada es pasada |
| Nueva ejecución | M2-04 continuación planificada | La futura, que nunca está cerrada (RN-46) | No | No |
| Corrección histórica | M3-03 corregir un avance | La del avance | No | Siempre (CA-103) |
| Corrección histórica | M2-02 resumen en jornada pasada o reabierta | La de la bitácora | No | Sí (RN-45) |
| Cambio lógico de validez (no es corrección de contenido) | M3-05 y M3-06 | Ninguna: no exigen reabrir. M3-05 valida antes que la jornada de origen cerrada no quede sin una actividad válida (D-04b) | No | Sí |

Marcar o revertir una marca de error es un **cambio lógico de validez de la actividad**, no una corrección del contenido de la bitácora: se audita y valida la integridad de los registros relacionados, pero no obliga a reabrir la jornada de origen. Si marcar puede invalidar las condiciones de cierre de una jornada cerrada, M3-05 lo evita rechazando la operación (`MARCA_INVALIDARIA_CIERRE`), y el cierre se serializa con las marcas de la misma jornada.

### 5.3 Reintentos y solicitudes concurrentes (T-04, decisión técnica aceptada)

- **Operaciones no repetibles:** M2-03, M2-04, M2-05, M2-06, M3-01, M3-02, M3-03, M3-04, M3-05 y M3-06. Registrar dos avances iguales el mismo día es válido (RN-41), así que un reintento no se distingue de una intención nueva por su contenido: hace falta una clave.
- **Clave:** cabecera `Idempotency-Key`, valor opaco generado por el cliente, único por intención de operación. Si falta, `CLAVE_IDEMPOTENCIA_OBLIGATORIA`.
- **Ámbito y conservación:** persona, operación y clave, con la huella de la petición y la respuesta, durante una ventana configurable (PA-13). Solo se guardan los resultados con éxito (2xx), para que una petición rechazada pueda reintentarse corregida.
- **Misma clave y misma petición:** devuelve la respuesta original (mismo estado y cuerpo) sin repetir efectos ni auditoría, e indica la reproducción con una cabecera.
- **Misma clave y otra petición:** `CLAVE_IDEMPOTENCIA_REUTILIZADA`. **Misma clave mientras la primera sigue en curso:** `OPERACION_EN_CURSO`.
- **Controles previos:** la identidad, el acceso y la pertenencia se evalúan antes de devolver una respuesta guardada (3.2); una persona desactivada no recibe el resultado almacenado.
- **Concurrencia con claves distintas:** las peticiones sobre una misma actividad se serializan (DM-01) y cada una se valida sobre el resultado de la anterior. El cierre de una bitácora se serializa con las marcas de error de sus actividades.
- **Idempotentes por naturaleza, sin clave:** M2-01b (unicidad, IR-01) y M2-02 (el `PUT` reemplaza). Una corrección con los valores ya vigentes (M3-03) no hace nada: 200 sin cambios ni entrada de auditoría.
- **Persistencia:** el registro de claves es una estructura técnica fuera de las nueve entidades de dominio. Su impacto se presenta aparte para aprobación.

## 6. Listados y textos

### 6.1 Listados y paginación (D-10, decisión técnica aceptada)

- Parámetros `limite` y `continuar_desde` (cursor opaco emitido por el servidor).
- `limite` tiene un valor por defecto y un máximo configurables (PA-13). Un valor inválido o superior al máximo se rechaza con `SOLICITUD_INVALIDA`, con el máximo en `detalles`. Un cursor inválido se rechaza igual.
- El orden es estable y determinista, definido por cada contrato, con el identificador como desempate, para que la paginación no repita ni omita elementos.
- El filtro de autorización se aplica antes de paginar (3.3). `siguiente` es nulo cuando no hay más elementos.
- La amplitud máxima de un rango de fechas es configurable (PA-13).

### 6.2 Textos (D-03, confirmada)

Requisitos mínimos de obligatoriedad, sin valores arbitrarios:

| Campo | Obligatoriedad | Fuente |
|---|---|---|
| `titulo` de una actividad | Obligatorio, no vacío tras recortar espacios. Hace falta para identificar la actividad; ninguna regla confirmada lo exige expresamente (precisión funcional pendiente) | D-03 |
| `descripcion` de un avance o una reactivación | Obligatoria, ni vacía ni solo espacios | RN-70 |
| `motivo_bloqueo` | Obligatorio si el estado es Bloqueada | RN-24 |
| `descripcion` de una planificación (original o continuación) | Opcional: ninguna regla la exige | D-03 |
| `resumen` | Opcional al guardar; obligatorio, ni vacío ni solo espacios, para cerrar | RN-21 |
| `motivo` de una reapertura o de una marca de error | Obligatorio | RN-50, RN-59 |

**Longitud:** todo campo de texto tiene un máximo configurable, definido con PA-13; los contratos no fijan ningún valor. Se mide en caracteres Unicode, tras recortar los espacios del inicio y del final. Superarlo se rechaza con `TEXTO_DEMASIADO_LARGO` (el cuerpo indica campo y máximo); nunca se trunca en silencio. Los textos se conservan tal como se reciben y se tratan como datos (RN-31).

## 7. Esquemas compartidos

Descripción conceptual de los campos. No fija tipos físicos.

**Bitácora**

| Campo | Descripción |
|---|---|
| `id`, `persona_id`, `fecha_laboral` | Identificador, propietaria y fecha laboral |
| `clase_jornada` | `pasada`, `actual` o `futura` (RN-72) |
| `estado` | `abierta` o `cerrada` |
| `resumen` | Texto libre |
| `cerrada_en`, `creada_en`, `modificada_en` | Momentos reales. Junto con la fecha laboral, permiten ver las tres fechas por separado (RN-18) |

**Actividad (vista de la propietaria)**: `id`, `propietaria_id`, `titulo`, `origen` (`planificada` o `no_planificada`), `estado_actual`, `marca_error` (nula o con `motivo` y `marcada_en`), `fecha_laboral_origen` y `creada_en`.

**ActividadVisible (vista de otras personas autorizadas)**: tiene dos formas, `completa` y `neutral`. La `completa` se entrega a la propietaria y a quienes están autorizados sobre la jornada de origen. La `neutral` contiene `id` (opaco), `propietaria_id` y `referencia_neutral`, con el texto fijo propuesto «Actividad en continuidad» (D-07, confirmada), sin título ni marca de error (RA-04, DM-03). El `id` no revela información del equipo anterior porque los identificadores son aleatorios y sin información incrustada. PA-26 está resuelto (RN-101).

**Planificación**: `id`, `actividad_id`, `fecha_laboral`, `tipo` (`original` o `continuacion`), `descripcion`, `registrada_en`, `clase` (`vigente` o `conservada`, DM-08).

**Avance**: `id`, `actividad_id`, `fecha_laboral`, `estado` (el estado histórico), `descripcion`, `motivo_bloqueo`, `es_reactivacion`, `registrado_en` y `modificado_en`.

**EntradaAuditoría**: `id`, `momento`, `tipo_autor`, `autor_persona_id`, `operacion`, `tipo_objeto`, `objeto_id`, `propietaria_registro_id`, `fecha_laboral_registro`, `motivo`, `valor_anterior` y `valor_nuevo`.

**ReferenciaMínima** (RA-06): `actividad` (en forma neutral), `propietaria_id`, `iniciada_en_otro_equipo` (siempre verdadero), `estado_actual` y `fecha_ultimo_avance` (solo si ese avance está autorizado).

## 8. Decisiones técnicas pendientes

| Id | Decisión | Estado |
|---|---|---|
| T-01 | Política de respuesta ante registros inexistentes o no autorizados (secciones 3.1 a 3.3) | **Aprobada** |
| T-02 | Catálogo coherente de errores y su correspondencia con códigos HTTP (sección 4) | Decisión técnica aceptada |
| T-03 | Prefijo y versionado `/api/v1` | **Aprobada** |
| T-04 | Clave de idempotencia y serialización ante reintentos y concurrencia (sección 5.3) | Decisión técnica aceptada |

## 9. Parámetros configurables

Un parámetro puede quedar configurable sin impedir que el contrato esté completo cuando el contrato fija su **nombre**, su **unidad**, la **regla de error** al incumplirlo y el **comportamiento** al rebasarlo. Solo falta el valor.

| Parámetro | Lo usan | Al incumplirlo | Lo decide |
|---|---|---|---|
| Valor por defecto y máximo de `limite` | M2-08, M3-07, M4-02, M4-03 | `SOLICITUD_INVALIDA`, con el máximo en `detalles` | PA-13 |
| Amplitud máxima de un rango de fechas | M4-02, M4-03, M5-01, M5-02 | `SOLICITUD_INVALIDA`; en M5, `INFORME_EXCEDE_LIMITES` | PA-13 |
| Longitud máxima de cada campo de texto | Todas las operaciones con texto | `TEXTO_DEMASIADO_LARGO` | PA-13 |
| Ventana de conservación de las claves de idempotencia | Operaciones con `Idempotency-Key` | Pasada la ventana, la clave se trata como nueva | PA-13 |
| Caducidad e intentos de los códigos; retardos y límite de intentos de inicio de sesión; inactividad y duración absoluta de la sesión | M1-01a, M1-03b, M1-09b | `CODIGO_NO_VALIDO`, `DEMASIADAS_SOLICITUDES`, `NO_IDENTIFICADA` | ADR-002 |
| Límites de registros, tokens, tiempo, reintentos y presupuesto de un informe | M5-01, M5-02 | `INFORME_EXCEDE_LIMITES`, `INFORME_NO_GENERADO` | ADR-003 |

Ningún contrato fija un valor numérico de estos parámetros.
