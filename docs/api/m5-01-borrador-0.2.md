# SMARTWORK — Contrato M5-01 «Generar un informe individual»: borrador de la versión 0.2

| Campo | Valor |
|---|---|
| **Estado** | **Borrador `[PROPUESTO]`.** Incorpora las decisiones de la persona responsable del 2026-11-18 sobre M5-T1 y M5-T2 (sección 6). No sustituye al contrato 0.1 de `m5-informes.md`, que no se ha modificado. Cada campo y cada regla indica si procede de una **decisión confirmada**, de una **decisión aprobada de M5-T0** o si sigue **`[PROPUESTO]`** o **`[ABIERTO]`**. Nada marcado así es requisito |
| **Versión** | 0.2 (borrador) |
| **Fecha** | 2026-11-18 |
| **Base** | `m5-informes.md` 0.1; `docs/backlog/tickets/m5-plan-implementacion.md` (M5-T0 y M5-T1); PRD; historias HU-5.1 a HU-5.5; ADR-003; `convenciones.md`; política de visibilidad de M1 y M4 |
| **Qué cambia respecto a 0.1** | (1) se añade `OPERACION_NO_PERMITIDA` y se precisa cuándo se emite (D-M5-02, **aprobada**); (2) se detalla campo por campo la respuesta (H-M5-1), separando lo que ya implementa M5-T1 (núcleo determinista) de lo que llegará con la narrativa (M5-T3) y la ruta (M5-T4); (3) se registran las decisiones del 2026-11-18 y las preguntas que siguen abiertas (sección 6). **No cambia ningún requisito, historia ni criterio de aceptación** |

## 1. Alcance de este contrato

Un servicio de **lectura** que no modifica datos: genera el informe de una persona para un período. No tiene identificador ni recurso de consulta posterior y no se guarda (RN-56, RF-75). **Contrato público independiente del proveedor de IA** (0.1): no aparece ningún proveedor, modelo, región ni parámetro de inferencia. Bedrock y Lambda son dependencias futuras de M5-T5 y M5-T7 y no figuran aquí.

## 2. Petición

`POST /api/v1/informes/individuales` `[PROPUESTO: la ruta la implementa M5-T4; M5-T1 es un servicio interno sin ruta]`

| Campo | Tipo | Obligatorio | Regla | Estado |
|---|---|---|---|---|
| `desde` | fecha laboral ISO | Sí | No posterior a `hasta`; incumplirlo es `SOLICITUD_INVALIDA` | Contrato 0.1 |
| `hasta` | fecha laboral ISO | Sí | Ídem | Contrato 0.1 |
| `persona_id` | identificador opaco | No | Por defecto, la persona que llama | Contrato 0.1 |

Cualquier otro campo es `SOLICITUD_INVALIDA` (convenciones, sección 2). **La amplitud máxima del período y los demás límites** son parámetros configurables (`INFORME_EXCEDE_LIMITES`) cuyos valores **siguen pendientes (D-M5-06)**.

## 3. Autorización y orden de evaluación

Orden (convenciones 3.2; implementado en M5-T1 como servicio interno):

1. Persona identificada: `NO_IDENTIFICADA` (401). La resuelve la dependencia de sesión en M5-T4.
2. Puede operar: `ACCESO_DESACTIVADO` o `SIN_PERTENENCIA_VIGENTE` (403), que solo informan de su propia situación.
3. Formato (`desde` no posterior a `hasta`): `SOLICITUD_INVALIDA`. Se evalúa antes que la persona y sin consultar nada, así que no revela existencia.
4. La persona solicitada:
   - **La propia persona**: siempre puede (RN-53, CA-152).
   - **Otra persona visible para quien llama EN EL PERÍODO pedido** (sección siguiente): solo si quien llama es **supervisor vigente con acceso efectivo** (RN-53, RA-12; CA-153). Si no lo es, **`OPERACION_NO_PERMITIDA` (403)** (D-M5-02 **aprobada**; CA-154).
   - **Persona inexistente, o sin visibilidad demostrable en el período**: **`RECURSO_NO_DISPONIBLE` (404) indistinguible** en código, mensaje, detalles y estructura (T-01, RNF-13). La respuesta no revela relaciones históricas ajenas al período.
5. Solo entonces se leen datos, **y solo los autorizados**, con la política única de M1 (D-M5-09 **aprobada**):
   - la propietaria obtiene todos sus registros del período, de ambos equipos (RF-93, CA-227);
   - un supervisor obtiene únicamente los registros de las fechas en que la persona pertenecía a su equipo (RF-96; CA-157, CA-224, CA-225), nunca los de otro equipo ni los posteriores a un traslado;
   - el supervisor del equipo nuevo no recibe título, descripciones ni motivos de bloqueo del equipo anterior; ve la actividad como «Actividad en continuidad» (RN-101; CA-226, CA-276).

**Definición de «persona visible» (corrección de P-9, 2026-11-18):** la propia persona, o una persona que perteneció al **equipo vigente de quien llama en algún día del período solicitado**; es decir, la regla de equipo de la lectura de registros (`decidir_lectura`) elevada de «una fecha» a «alguna fecha del período». **No** se usa la regla «perteneció alguna vez al equipo vigente»: revelaría relaciones históricas fuera del período pedido. Solo sirve para elegir entre 403 y 404 y no concede la lectura de ningún registro. Cuando la visibilidad no puede demostrarse, el 404 es uniforme. Ver la nota sobre CA-202 en la pregunta P-10.

## 4. Respuesta: 200 con `informe`

Los campos se agrupan por cuánto está decidido. **La respuesta pública no incluye identificadores internos de referencia de los hechos ni enlaces a los registros de origen** (PP-11 sigue sin aprobar).

### 4.1 Campos que implementa M5-T1 (núcleo determinista)

| Campo | Tipo | Definición | Origen / estado |
|---|---|---|---|
| `tipo` | texto | Siempre `individual` | Contrato 0.1 |
| `periodo` | objeto `desde`, `hasta` | El período solicitado | Contrato 0.1, RF-48 |
| `persona` | objeto `id`, `nombre` | La persona del informe. No incluye ningún otro dato de la persona | Contrato 0.1 |
| `sin_datos` | booleano | Verdadero si no hay ningún **avance** autorizado en el período. Entonces `hechos`, `bloqueos` y `actividades` están vacíos y `agregaciones` es nulo: solo se indica que no hay datos disponibles, sin inventar nada | RN-57, RF-33; CA-172, CA-173, CA-202. **Decidido el 2026-11-18:** una planificación sin avances no cuenta como registro para las métricas basadas en avances |
| `actividades` | lista | Las actividades que algún hecho referencia, cada una una sola vez: `id` (opaco), `forma` (`completa` o `neutral`), `texto` (el título si `completa`; «Actividad en continuidad» si `neutral`) y `planificada` (`true`, `false` o ausente si el origen es de otro equipo y no se revela) | ActividadVisible (convenciones 7); RN-101, RA-04. Forma de la lista `[PROPUESTO: P-5]` |
| `hechos` | lista ordenada por la secuencia de avances (fecha laboral, momento, identificador) | Cada hecho es un **avance autorizado**: `fecha_laboral`, referencia a su actividad, `estado` (el estado histórico del avance), `descripcion` y `motivo_bloqueo` (solo si el estado es Bloqueada) | Contrato 0.1; RA-05. Forma exacta `[PROPUESTO: P-5]` |
| `bloqueos` | lista | Cada avance en estado Bloqueada con su motivo: `fecha_laboral`, actividad y `motivo`. **Una entrada por avance bloqueado** | RF-74, RN-55; CA-165. Unidad `[ABIERTA: P-3]` |
| `agregaciones` | objeto | Ver 4.2. **Nulo si `sin_datos`** | RF-46, RF-51. **Catálogo `[PROPUESTO]`, pendiente de aprobar (D-M5-04)** |

Quedan **fuera** de `hechos`, `actividades` y `agregaciones`: las actividades marcadas por error (RN-60, RA-08, CA-167); las planificaciones, conservadas o no (RA-11); el resumen libre de la bitácora (ADR-003, B6); correos, identificadores de acceso, credenciales, nombres de equipos y la auditoría.

### 4.2 Agregaciones (D-M5-04 **confirmado** el 2026-11-18: catálogo de seis métricas y sus reglas)

Todas son recuentos deterministas, sin porcentajes (RN-57), calculados solo sobre los hechos autorizados, sin rankings ni puntuaciones.

| Campo | Definición |
|---|---|
| `avances` | Cantidad de avances autorizados en el período |
| `jornadas_con_registros` | Fechas laborales distintas con avances autorizados |
| `actividades_con_registros` | Actividades distintas con avances autorizados |
| `actividades_por_origen` | `planificadas`, `no_planificadas` y `origen_no_disponible`. Un origen protegido (forma neutral) **nunca se infiere**: va a `origen_no_disponible` |
| `actividades_con_bloqueo` | Actividades con algún avance autorizado en estado Bloqueada durante el período |
| `actividades_por_estado_al_corte` | **Solo** las actividades con avances autorizados en el período. El corte es `hasta` (RF-70). El estado de cada una es el del **último avance hasta el corte** según la secuencia válida completa, y solo se informa si ese avance está autorizado (RA-07, RN-88). Grupos: `pendiente`, `en_progreso`, `bloqueada`, `completada` y **`estado_no_disponible`** |

**`estado_no_disponible`.** Agrupa las actividades cuyo último avance hasta el corte no está autorizado para quien genera el informe (por ejemplo, lo registró el otro equipo tras un traslado). No se sustituye por el estado de un avance anterior autorizado, y el estado protegido **nunca sale de la base de datos** (la consulta lo anula antes de devolverlo). El grupo solo contiene un **recuento**: no identifica la actividad, no dice qué estado tiene ni cuántos avances protegidos hay. No se incluye la población de actividades pendientes de la vista de supervisión (M4-03). Los cinco grupos suman `actividades_con_registros`.

### 4.3 Campos que se añadirán después `[PROPUESTO]`

| Campo | Tipo | Quién lo aporta |
|---|---|---|
| `generado_en` | momento real UTC | M5-T4 (RF-48, RN-29): se fija al generar |
| `base` | texto fijo | M5-T4 (RF-87). **El texto exacto no está decidido `[ABIERTO: P-6]`** |
| `narrativa` | texto o nulo | M5-T3 (interfaz interna y validación, **implementadas con un generador simulado**) y M5-T5 (integración). Es **la única parte generada por IA**; nula si `sin_datos`. No contiene valoraciones ni rankings (RF-47) y no afirma nada que no conste en los hechos (RF-32); la validación determinista no garantiza esto último ni lo primero (riesgo residual y evaluación por muestras en `m5-integracion-ia.md`). Forma pública: `[ABIERTA]` P-11 |

## 5. Errores

| Código | HTTP | Cuándo |
|---|---|---|
| `NO_IDENTIFICADA` | 401 | No hay persona identificada (CA-02) |
| `ACCESO_DESACTIVADO` | 403 | El acceso de quien llama está desactivado |
| `SIN_PERTENENCIA_VIGENTE` | 403 | Quien llama no tiene pertenencia vigente |
| `SOLICITUD_INVALIDA` | 400 | Formato incorrecto, `desde` posterior a `hasta` o campo desconocido |
| `RECURSO_NO_DISPONIBLE` | 404 | Persona inexistente o no visible, de forma indistinguible |
| **`OPERACION_NO_PERMITIDA`** | 403 | **Nueva respecto a 0.1 (D-M5-02, aprobada).** La persona es visible, pero quien llama ni es la propietaria ni supervisa |
| `INFORME_EXCEDE_LIMITES` | 422 | Se rebasa un límite configurado, antes de generar. **Valores pendientes (D-M5-06)** |
| `INFORME_NO_GENERADO` | 503 | El servicio de IA falla, agota su tiempo o su salida no supera la validación. Sin contenido parcial (RN-58; CA-174, CA-175) |

Ningún mensaje ni detalle incluye títulos, descripciones, motivos, nombres de equipo ni contenido de registros.

## 6. Decisiones del 2026-11-18 y preguntas

### 6.1 Resueltas por la persona responsable (se aplican a M5-T1)

| Id | Resolución |
|---|---|
| P-1 | Una planificación sin avances **no** cuenta como registro para las métricas basadas en avances (se mantiene la lectura «registro = avance») |
| P-2 | `actividades_por_estado_al_corte` queda definida (sección 4.2): solo actividades con avances autorizados en el período, estado del último avance hasta el corte si está autorizado y grupo `estado_no_disponible` si no |
| P-4 | `actividades_con_bloqueo` = actividades con algún avance autorizado en estado Bloqueada durante el período |
| P-7 | `actividades_por_origen` incluye `origen_no_disponible`; no se infiere un origen protegido |
| P-9 | Corregida: visibilidad efectiva sobre la persona **y el período** (sección 3); 404 uniforme si no puede demostrarse |
| **P-10** | **Confirmada (2026-11-18, tercera comunicación):** persona autorizada y visible durante el período, sin avances: respuesta vacía autorizada (`sin_datos`); persona sin visibilidad autorizada en ningún día del período: 404 uniforme; persona inexistente o de otra organización sin autorización: 404 uniforme; propietaria autorizada sin avances: `sin_datos`. No se amplían ni alteran las políticas históricas de M1 a M4 |
| D-M5-04 | **Confirmado** el catálogo de seis métricas y sus reglas de cálculo (T1 y T2). **No** se declara cerrado todo el contrato de respuesta: P-3, P-5, P-6 y P-8 siguen abiertas |

### 6.2 Siguen abiertas: P-3, P-5, P-6 y P-8, con sus definiciones exactas en las fuentes

No se inventa ninguna respuesta. Lo que M5-T1 implementó para P-3 y P-5 es **provisional** y está así señalado.

| Id | Qué dicen exactamente las fuentes | Qué falta decidir | Lo implementado (provisional) |
|---|---|---|---|
| **P-3** Unidad de `bloqueos` | Contrato 0.1: `bloqueos` = «Actividades bloqueadas con su motivo (RN-55)». RF-74: «Los informes incluyen los bloqueos con sus motivos.» CA-165: «DADO un informe de un período con una actividad bloqueada CUANDO se genera ENTONCES muestra la actividad y su motivo de bloqueo.» | Si la unidad es el avance bloqueado o la actividad, y qué motivo se muestra si una actividad se bloquea varias veces en el período | Una entrada por avance Bloqueada, con su motivo: no pierde ningún motivo |
| **P-5** Campos públicos de `hechos` | Contrato 0.1: `hechos` = «Registros del período: fecha laboral, ActividadVisible, estado histórico, descripción y, si procede, motivo de bloqueo». Convenciones 7: `ActividadVisible` tiene las formas `completa` y `neutral` | Qué campos de `ActividadVisible` lleva cada hecho (por ejemplo, si se informa `estado_actual`, sujeto a D-M4-05) y si el hecho repite la actividad o la referencia en una lista | Una lista de actividades con referencia y, en cada hecho, la referencia; la actividad lleva solo `forma`, `texto` y `planificada`. No hay `estado_actual` |
| **P-6** Texto de `base` | Contrato 0.1: `base` = «Declaración fija de que el informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada (RF-87)». RF-87 y CA-200 exigen esa indicación en todo informe | El **texto exacto** de la declaración | Nada: es de M5-T4 |
| **P-8** Valores de los límites | `convenciones.md` sección 9: la amplitud máxima de un rango de fechas (M4-02, M4-03, M5-01, M5-02) incumplida da `SOLICITUD_INVALIDA` y, en M5, `INFORME_EXCEDE_LIMITES` (PA-13); los límites de registros, tokens, tiempo, reintentos y presupuesto de un informe dan `INFORME_EXCEDE_LIMITES` o `INFORME_NO_GENERADO` (ADR-003). «Ningún contrato fija un valor numérico de estos parámetros». El 92 de M4 (D-M4-03) es solo de M4. ADR-003, sección 9: «como máximo un reintento» (propuesto) | Los valores (D-M5-06) | Ningún límite: no se implementó ningún valor numérico |

### 6.2 bis Nueva pregunta abierta (M5-T3)

| Id | Qué dicen las fuentes | Qué falta decidir |
|---|---|---|
| **P-11** | Contrato 0.1: `narrativa` = «Texto generado a partir de los hechos y las agregaciones recibidos» | Si la narrativa pública es un único texto (lo propuesto: las secciones validadas unidas con una línea en blanco) o una lista de secciones. Las referencias de cada sección son internas y no se muestran (PP-11 no aprobada) |

### 6.3 Pregunta que se planteó y quedó resuelta

| Id | Pregunta | Tratamiento |
|---|---|---|
| **P-10** | Con la corrección de P-9, quien pide el informe de una persona **sin visibilidad en ningún día del período** recibe el 404 uniforme. El criterio CA-202 («tiene registros, pero ninguno autorizado para quien genera el informe → no hay datos disponibles») se cumple cuando hay visibilidad en el período pero ningún registro autorizado (por ejemplo, la persona estuvo en el equipo al inicio del período, sin registros, y los del resto son de otro equipo). **No se cumple literalmente en el caso sin ninguna visibilidad**, que da 404. Se aplicó la instrucción de no revelar relaciones históricas | **Confirmada** (sección 6.1): es la lectura deseada |

## 7. Criterios de aceptación vinculados

Sin cambios respecto a 0.1: CA-152 a CA-167, CA-172 a CA-175, CA-199 a CA-202, CA-224 a CA-227, CA-234 y CA-276. **Ningún criterio se modifica en este borrador y ninguno se declara cumplido**: la evidencia de M5-T1 (núcleo determinista) está en el plan, sección 14.
