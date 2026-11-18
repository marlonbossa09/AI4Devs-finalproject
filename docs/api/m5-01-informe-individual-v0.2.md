# SMARTWORK — Contrato M5-01 «Generar un informe individual»: versión 0.2 (aprobada)

| Campo | Valor |
|---|---|
| **Estado** | **APROBADO** el 2026-11-18 por la persona responsable del producto (versión 0.2). **Sustituye al contrato 0.1** de `m5-informes.md`, que se conserva como historial de la versión 0.1. Sigue abierta solo la parte parcial de P-8 (tokens, plazo total y concurrencia: sección 6.2), que no cambia la forma de la respuesta |
| **Versión** | 0.2 (aprobada) |
| **Fecha** | 2026-11-18 |
| **Base** | `m5-informes.md` 0.1; `docs/backlog/tickets/m5-plan-implementacion.md` (M5-T0 y M5-T1); PRD; historias HU-5.1 a HU-5.5; ADR-003; `convenciones.md`; política de visibilidad de M1 y M4 |
| **Qué cambia respecto a 0.1** | (1) se añade `OPERACION_NO_PERMITIDA` (D-M5-02); (2) esquema público completo campo por campo; (3) límites confirmados (D-M5-06), reintento (P-12), declaración `base` (P-6), `persona` (P-13) y nombres de campo. **No cambia ningún requisito, historia ni criterio de aceptación.** Trazabilidad: sección 4.9 y sección 8 |

## 1. Alcance de este contrato

Un servicio de **lectura** que no modifica datos: genera el informe de una persona para un período. No tiene identificador ni recurso de consulta posterior y no se guarda (RN-56, RF-75). **Contrato público independiente del proveedor de IA** (0.1): no aparece ningún proveedor, modelo, región ni parámetro de inferencia. Bedrock y Lambda son dependencias futuras de M5-T5 y M5-T7 y no figuran aquí.

## 2. Petición

`POST /api/v1/informes/individuales` `[PROPUESTO: la ruta la implementa M5-T4; M5-T1 es un servicio interno sin ruta]`

| Campo | Tipo | Obligatorio | Regla | Estado |
|---|---|---|---|---|
| `desde` | fecha laboral ISO | Sí | No posterior a `hasta`; incumplirlo es `SOLICITUD_INVALIDA` | Contrato 0.1 |
| `hasta` | fecha laboral ISO | Sí | Ídem | Contrato 0.1 |
| `persona_id` | identificador opaco | No | Por defecto, la persona que llama | Contrato 0.1 |

Cualquier otro campo es `SOLICITUD_INVALIDA` (convenciones, sección 2). **Límites (D-M5-06, 2026-11-18):** período máximo de **31 días con ambos extremos incluidos** (`INFORME_MAX_RANGE_DAYS`, **confirmado**) y máximo de **400 hechos por solicitud** (`INFORME_MAX_HECHOS`, **confirmado**); los excedidos se rechazan con `INFORME_EXCEDE_LIMITES`, sin truncar nada. Siguen **abiertos** los límites de tokens de entrada y de salida, el plazo y la concurrencia. **Implementación de M5-T4:** la ruta, la autorización, los límites, el interruptor y los errores están implementados, pero la ruta **no está registrada** en la aplicación porque la respuesta de éxito depende de las preguntas abiertas.

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

## 4. Respuesta: 200 con `informe` (esquema público, campo por campo)

`[PROPUESTO]` hasta la revisión contractual. Todas las claves son **obligatorias** (nunca se omiten a nivel de informe); lo que no aplica se envía vacío o `null` como se indica. Los campos de los elementos que no se pueden mostrar se **omiten**. No hay ningún campo de ranking, puntuación, porcentaje ni valoración. Ningún identificador de la base de datos salvo los de las personas del informe.

### 4.1 Campos del informe

| Campo | Tipo | Contenido y visibilidad | Origen |
|---|---|---|---|
| `tipo` | texto | Siempre `individual` | 0.1 |
| `periodo` | objeto | `desde` y `hasta` (fechas laborales ISO): el período solicitado | 0.1, RF-48 |
| `generado_en` | texto, momento ISO 8601 en UTC con `Z` | Momento real de generación; cada generación es nueva | 0.1, RF-48, RN-29, CA-160; convenciones 2 |
| `base` | texto | La **declaración fija de producto** (P-6, confirmada): «Este informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada.». Redacción de producto aprobada, **no una cita literal de RF-87** (RF-87 fija la obligación, no el texto). **Siempre presente, también con `sin_datos`** | RF-87, CA-200 |
| `sin_datos` | booleano | Verdadero si no hay ningún avance autorizado en el período (una planificación sin avances no cuenta). Entonces `agregaciones` y `narrativa` son `null` y las listas, vacías | RN-57, RF-33; CA-172, CA-173, CA-202 |
| `persona` | objeto `id`, `nombre` | La persona del informe (P-13, confirmada). **Solo en respuestas autorizadas.** Ningún otro dato de la persona. No se envía al generador de IA (4.10) | 0.1 |
| `agregaciones` | objeto o `null` | Las seis métricas (4.5). `null` si `sin_datos` | D-M5-04 |
| `actividades` | lista | Proyección autorizada y cerrada de las actividades que algún hecho referencia, una vez cada una (4.2) | P-5 |
| `hechos` | lista, en la secuencia de avances | Un elemento por avance autorizado (4.3) | P-5 |
| `bloqueos` | lista | Agrupados por actividad (4.4) | P-3 |
| `narrativa` | lista o `null` | Lista de secciones de texto (4.6). **`null` cuando `sin_datos` es verdadero: está permitido y es obligatorio** | P-11 |

### 4.2 `actividades[]` (P-5)

Referencias **opacas y locales al informe** (`a1`, `a2`…): nunca el identificador de la base de datos. Dos formas.

| Forma | Campos | Regla |
|---|---|---|
| `completa` | `ref`, `forma` (`completa`), `titulo`, `origen` (`planificada` o `no_planificada`) | Solo si quien genera el informe está autorizado sobre la jornada de origen de la actividad (RA-04) |
| `neutral` | `ref`, `forma` (`neutral`), `referencia_neutral` («Actividad en continuidad») | Actividad iniciada en otro equipo: **sin título ni origen** (RN-101, CA-276). El título original no sale de la base de datos |

No hay `estado_actual`, `propietaria_id`, marca de error ni fechas de origen. Una actividad marcada por error no aparece.

### 4.3 `hechos[]` (P-5)

| Campo | Tipo | Regla |
|---|---|---|
| `fecha_laboral` | fecha ISO | La del avance |
| `actividad_ref` | texto | Referencia a un elemento de `actividades` del mismo informe (siempre existe) |
| `estado` | texto | El estado **histórico** de ese avance: `Pendiente`, `En progreso`, `Bloqueada` o `Completada` (nunca el estado actual) |
| `descripcion` | texto | Texto libre de la persona, tal cual; es dato y no instrucción (RN-31) |
| `motivo_bloqueo` | texto | **Solo** si `estado` es `Bloqueada`; en otro caso se omite |

Sin referencia propia del hecho: las referencias internas de respaldo de la narrativa no se exponen (PP-11 sin aprobar). No hay hechos de avances no autorizados.

### 4.4 `bloqueos[]` (P-3)

Agrupados por actividad, en el orden de primera aparición.

| Campo | Tipo | Regla |
|---|---|---|
| `actividad_ref` | texto | Referencia a un elemento de `actividades` |
| `ocurrencias` | lista | Una entrada por cada avance **autorizado** en estado Bloqueada de esa actividad, en la secuencia: `fecha_laboral` y `motivo` |

Es un registro **histórico**: no significa que la actividad esté bloqueada ahora (el estado actual no se informa). No incluye motivos de avances protegidos. Coincide siempre con los hechos en estado `Bloqueada`.

### 4.5 `agregaciones`

| Campo | Definición (D-M5-04 **confirmada**) |
|---|---|
| `avances` | Cantidad de avances autorizados en el período |
| `jornadas_con_registros` | Fechas laborales distintas con avances autorizados |
| `actividades_con_registros` | Actividades distintas con avances autorizados |
| `actividades_por_origen` | Objeto `planificadas`, `no_planificadas` y `origen_no_disponible` (las de forma neutral: no se infiere un origen protegido) |
| `actividades_con_bloqueo` | Actividades con algún avance autorizado en estado Bloqueada durante el período (no «bloqueada al corte») |
| `actividades_por_estado_al_corte` | Objeto `pendiente`, `en_progreso`, `bloqueada`, `completada` y `estado_no_disponible`. **Solo** actividades con avances autorizados en el período; el estado es el del último avance hasta `hasta` (RF-70) y solo si está autorizado (RA-07, RN-88); si lo determina un avance protegido, la actividad va a `estado_no_disponible` y **no** se sustituye por un estado anterior. Los cinco grupos suman `actividades_con_registros` |

Todos son enteros no negativos, calculados con código determinista sobre los hechos autorizados, **sin porcentajes**, rankings ni puntuaciones. Se copian tal cual a la respuesta: no se recalculan ni se duplican.

### 4.6 `narrativa` (P-11)

Una lista de **secciones**; cada una es un objeto con **solo** `texto` (texto plano). Sin identificadores ni referencias internas. Es la **única parte generada por IA** y nunca sustituye ni modifica un hecho o una cifra. `null` si `sin_datos`. La validación determinista no garantiza la ausencia de valoraciones subjetivas ni de afirmaciones plausibles pero inventadas (riesgo residual y evaluación por muestras en `m5-integracion-ia.md`).

### 4.7 Consistencia entre colecciones

Todo `actividad_ref` de `hechos` y de `bloqueos` existe en `actividades`; los `bloqueos` son exactamente los hechos `Bloqueada` agrupados por actividad; las `agregaciones` son las deterministas y no se derivan de la narrativa; un campo no autorizado nunca aparece, ni en un elemento ni en un recuento.

### 4.8 Ejemplo ficticio (abreviado)

```json
{"tipo": "individual", "periodo": {"desde": "2026-11-01", "hasta": "2026-11-30"}, "generado_en": "2026-12-01T14:03:22Z",
 "base": "Este informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada.",
 "sin_datos": false, "persona": {"id": "<identificador opaco>", "nombre": "Ana de prueba"},
 "agregaciones": {"avances": 3, "jornadas_con_registros": 2, "actividades_con_registros": 2,
                  "actividades_por_origen": {"planificadas": 1, "no_planificadas": 0, "origen_no_disponible": 1}, "actividades_con_bloqueo": 1,
                  "actividades_por_estado_al_corte": {"pendiente": 0, "en_progreso": 1, "bloqueada": 1, "completada": 0, "estado_no_disponible": 0}},
 "actividades": [{"ref": "a1", "forma": "completa", "titulo": "Preparar informe", "origen": "planificada"},
                 {"ref": "a2", "forma": "neutral", "referencia_neutral": "Actividad en continuidad"}],
 "hechos": [{"fecha_laboral": "2026-11-03", "actividad_ref": "a1", "estado": "En progreso", "descripcion": "Primer avance"},
            {"fecha_laboral": "2026-11-04", "actividad_ref": "a1", "estado": "Bloqueada", "descripcion": "Espera datos", "motivo_bloqueo": "falta acceso"}],
 "bloqueos": [{"actividad_ref": "a1", "ocurrencias": [{"fecha_laboral": "2026-11-04", "motivo": "falta acceso"}]}],
 "narrativa": [{"texto": "Resumen redactado a partir de los hechos."}]}
```

### 4.9 Diferencias frente a la versión 0.1

| Campo | Versión 0.1 | Este borrador |
|---|---|---|
| `hechos` | «Registros del período: fecha laboral, ActividadVisible, estado histórico, descripción y, si procede, motivo de bloqueo» | Sin `ActividadVisible` dentro del hecho: una lista `actividades` con una proyección cerrada y, en cada hecho, `actividad_ref` (P-5) |
| `bloqueos` | «Actividades bloqueadas con su motivo (RN-55)» | Agrupados por actividad con la lista de ocurrencias, fecha y motivo (P-3) |
| `narrativa` | «Texto generado…» (un único texto) | Lista de secciones solo con `texto` (P-11) |
| `agregaciones` | Catálogo propuesto sin esquema | Las seis métricas confirmadas, campo por campo (D-M5-04) |
| `base`, `generado_en`, `sin_datos` | Descritos en prosa | Tipo, obligatoriedad y reglas definidos; el texto de `base` queda pendiente (P-6) |
| Errores | Sin `OPERACION_NO_PERMITIDA` y sin indicación de reintento | Se añaden (D-M5-02, P-12) |

### 4.10 Privacidad frente al generador de IA

El generador **no recibe** el nombre ni el identificador de la persona: recibe un alias («Persona 1») y referencias internas de hechos y actividades (contrato interno, `m5-integracion-ia.md`). `persona.id` y `persona.nombre` existen solo en la respuesta autorizada. La seudonimización por alias **no es anonimización**: los textos libres pueden contener datos personales (riesgo residual documentado).

## 5. Errores

| Código | HTTP | Cuándo | `detalles` |
|---|---|---|---|
| `NO_IDENTIFICADA` | 401 | No hay persona identificada (CA-02) | Los de las convenciones |
| `ACCESO_DESACTIVADO` | 403 | Acceso desactivado | Los de las convenciones |
| `SIN_PERTENENCIA_VIGENTE` | 403 | Sin pertenencia vigente | Los de las convenciones |
| `SOLICITUD_INVALIDA` | 400 | Formato, `desde` posterior a `hasta`, campo desconocido, CSRF u origen | Los de las convenciones |
| `OPERACION_NO_PERMITIDA` | 403 | La persona es visible, pero quien llama ni es la propietaria ni supervisa (D-M5-02) | Vacío |
| `RECURSO_NO_DISPONIBLE` | 404 | Persona inexistente o sin visibilidad demostrable en el período, **indistinguible** (RNF-13) | Vacío |
| `INFORME_EXCEDE_LIMITES` | 422 | Más de 31 días (extremos incluidos) o más de 400 hechos por solicitud; antes de generar y sin truncar | `{campo: hasta, motivo: rango_excede_el_maximo, maximo_dias: 31}` o `{campo: hechos, motivo: hechos_exceden_el_maximo, maximo_hechos: 400}`, más el detalle de reintento. Nunca el recuento real ni datos |
| `INFORME_NO_GENERADO` | 503 | La generación está desactivada (por defecto), el generador falla, agota su plazo o su salida no supera la validación. Sin contenido parcial (RN-58; CA-174, CA-175) | El detalle de reintento |

**Reintento (P-12, confirmada).** El detalle de reintento es `{campo: reintento, reintento: <booleano>, motivo: posible | no_aplicable}`, siempre coherente: `reintento` verdadero ⇔ `motivo` `posible`. Solo `INFORME_NO_GENERADO` y `INFORME_EXCEDE_LIMITES` lo llevan. **Los errores de autorización, de validación de la entrada y de límites no son reintentables** (`no_aplicable`). Solo los fallos técnicos **transitorios** del generador (no disponible, plazo agotado, error inesperado) admiten el reintento (`posible`); una integración desactivada o sin generador configurado, una salida malformada y una salida rechazada por la validación **no**. Se conservan los formatos de error de las convenciones. Ningún mensaje ni detalle incluye títulos, descripciones, motivos, nombres de equipo, el contenido rechazado ni prompts.

## 6. Decisiones del 2026-11-18 y preguntas

### 6.1 Resueltas por la persona responsable

| Id | Resolución |
|---|---|
| P-1 | Una planificación sin avances **no** cuenta como registro |
| P-2 | `actividades_por_estado_al_corte` definida (4.5) |
| P-3 | **Confirmada:** bloqueos agrupados por actividad con la lista de ocurrencias autorizadas (fecha y motivo); no es estado actual; sin motivos de avances protegidos |
| P-4 | `actividades_con_bloqueo`: con algún avance Bloqueada autorizado en el período |
| P-5 | **Confirmada:** `actividades` (proyección autorizada y cerrada), `hechos` (avances autorizados vinculados a una referencia de actividad) y `bloqueos`, con referencias opacas y locales al informe |
| P-7 | `origen_no_disponible`; no se infiere un origen protegido |
| P-9 | Visibilidad efectiva sobre la persona y el período; 404 uniforme si no puede demostrarse |
| P-10 | **Confirmada:** autorizada y visible sin avances → `sin_datos`; sin visibilidad en ningún día del período → 404 uniforme; inexistente o de otra organización → 404 uniforme; propietaria sin avances → `sin_datos` |
| P-11 | **Confirmada:** narrativa pública = lista de secciones por persona, cada una solo con `texto` |
| P-12 | **Confirmada:** `reintento` (booleano) y `motivo` (`posible` o `no_aplicable`), coherentes |
| P-6 | **Confirmada:** la declaración fija de producto es «Este informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada.». Es **redacción aprobada de producto**, no una cita literal de RF-87 (RF-87 fija la obligación, no el texto). Se usa en los dos tipos de informe, también con `sin_datos` |
| P-13 | **Confirmada:** se conserva el objeto público `persona` (`id`, `nombre`), solo en respuestas autorizadas; en el consolidado, solo las personas de la población aprobada. Ni el nombre ni el identificador van al generador de IA (alias y referencias internas) |
| Nombres de campo | **Confirmados:** `actividad_ref` (referencia opaca local al informe), `ocurrencias` (bloqueos autorizados agrupados por actividad), `titulo` y `origen` (solo si la política permite exponer el origen) y `referencia_neutral` (actividad heredada) |
| D-M5-04 | **Confirmado** el catálogo de seis métricas |
| D-M5-06 | **Confirmados** 31 días, 400 hechos por solicitud, 0 reintentos e `INFORME_HABILITADO` falso |

### 6.2 Sigue abierta

| Id | Estado | Qué falta |
|---|---|---|
| **P-8** | **Parcial** | Siguen abiertos y **no se declaran confirmados**: tokens máximos de entrada (propuesta 64.000), tokens máximos de salida (2.000), plazo total (120 s) y concurrencia máxima (4 por proceso). Condicionan la integración real (M5-T5 y M5-T7), no la forma de la respuesta |

## 7. Criterios de aceptación vinculados

Sin cambios respecto a 0.1: CA-152 a CA-167, CA-172 a CA-175, CA-199 a CA-202, CA-224 a CA-227, CA-234 y CA-276. **Este contrato no modifica ningún criterio y no declara ninguno cumplido**: la evidencia está en el plan de M5 (secciones 14, 17, 19 y 20) y la matriz de trazabilidad es de M5-T8.

## 8. Historial de versiones

| Versión | Fecha | Estado | Cambios |
|---|---|---|---|
| 0.1 | 2026-11-06 | `[PROPUESTO]`. Conservada en `m5-informes.md` como historial | Primera propuesta del contrato público de M5-01 y M5-02, independiente del proveedor de IA |
| 0.2 | 2026-11-18 | **Aprobada** por la persona responsable del producto | Esquema público completo campo por campo; `OPERACION_NO_PERMITIDA`; límites confirmados; reintento (P-12); declaración `base` (P-6); `persona` (P-13); nombres de campo; bloqueos agrupados (P-3); actividades y hechos con referencias (P-5); narrativa como lista de secciones (P-11). La trazabilidad frente a 0.1 está en la sección 4.9 y en el historial de decisiones de la sección 6 |
