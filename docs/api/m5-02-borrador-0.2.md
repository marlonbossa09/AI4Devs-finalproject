# SMARTWORK — Contrato M5-02 «Generar un informe consolidado»: borrador de la versión 0.2

| Campo | Valor |
|---|---|
| **Estado** | **Borrador `[PROPUESTO]`.** No sustituye al contrato 0.1 de `m5-informes.md`, que no se ha modificado hasta la revisión contractual correspondiente. Cada campo indica si procede de una decisión **confirmada**, de una **aprobada en principio** o si sigue **`[PROPUESTO]`** o **`[ABIERTO]`**. Redactado por la aprobación de C-1 (2026-11-18) |
| **Versión** | 0.2 (borrador) |
| **Fecha** | 2026-11-18 |
| **Base** | `m5-informes.md` 0.1; `m5-01-borrador-0.2.md`; `docs/backlog/tickets/m5-plan-implementacion.md` (M5-T2 y M5-T3); PRD; historias HU-5.2 a HU-5.5; ADR-003; `convenciones.md`; política de visibilidad de M1 y M4 |
| **Qué cambia respecto a 0.1** | (1) esquema completo de la respuesta, separando lo que ya implementa el núcleo determinista (M5-T2) de la narrativa (M5-T3 y M5-T5) y de los campos de la ruta (M5-T4); (2) se registran las decisiones C-2 a C-6; (3) la narrativa pasa a ser **por persona** y la sección de equipo, **determinista** (D-M5-03, aprobada en principio); (4) se precisa el orden de evaluación entre el rol y el equipo. **No cambia ningún requisito, historia ni criterio de aceptación** |

## 1. Alcance

Un servicio de **lectura** que no modifica datos: genera el informe de un equipo para un período. Sin identificador ni recurso de consulta posterior; no se guarda (RN-56, RF-75). **Independiente del proveedor de IA** (contrato 0.1): no aparecen proveedor, modelo, región ni parámetros de inferencia. Bedrock y Lambda son dependencias futuras de M5-T5 y M5-T7.

## 2. Petición

`POST /api/v1/informes/consolidados` `[PROPUESTO: la ruta la implementa M5-T4; M5-T2 es un servicio interno sin ruta]`

| Campo | Tipo | Obligatorio | Regla | Estado |
|---|---|---|---|---|
| `desde` | fecha laboral ISO | Sí | No posterior a `hasta` (`SOLICITUD_INVALIDA`) | Contrato 0.1 |
| `hasta` | fecha laboral ISO | Sí | Ídem. Es también el **corte** del estado al corte (RF-70) | Contrato 0.1 |
| `equipo_id` | identificador opaco | No | Por defecto, el equipo que supervisa quien llama | Contrato 0.1 |

Cualquier otro campo es `SOLICITUD_INVALIDA`. Los límites (amplitud del período, número de hechos y demás) son parámetros configurables cuyos **valores siguen pendientes (D-M5-06)**.

## 3. Autorización y orden de evaluación (C-6 confirmada)

1. Persona identificada: `NO_IDENTIFICADA` (401).
2. Puede operar: `ACCESO_DESACTIVADO` (un supervisor desactivado no supervisa, RA-12) o `SIN_PERTENENCIA_VIGENTE` (403).
3. Formato (`desde` no posterior a `hasta`): `SOLICITUD_INVALIDA`, sin consultar nada.
4. **Rol y acceso efectivo:** solo el **supervisor vigente con acceso efectivo** (RN-54). Un colaborador, también quien fue supervisor y ya no lo es, recibe **`OPERACION_NO_PERMITIDA` (403)** (CA-169); es un 403 por rol sobre la función y no revela ningún equipo ni registro.
5. **Equipo solicitado:** el que supervisa quien llama. Un `equipo_id` ajeno o inexistente da **`RECURSO_NO_DISPONIBLE` (404) indistinguible** (CA-170, RNF-13).
6. Solo entonces se leen datos, **y solo los autorizados**, con la política única de M1 (D-M5-09) y el filtro aplicado en la propia consulta, antes de agrupar o calcular.

## 4. Población y reglas de los datos

- **Personas (C-2 confirmada):** únicamente las que tienen **al menos un avance autorizado** en el período. No se listan integrantes sin registros.
- **Avances:** los autorizados con fecha laboral en el período, de las personas que **eran del equipo en la fecha laboral de cada avance** (RF-83): una persona trasladada aporta al equipo anterior solo lo anterior al traslado y al nuevo solo lo posterior (CA-228, CA-229).
- **Trabajo de la supervisora (C-5 confirmada):** cuenta cuando su pertenencia al equipo en la fecha del avance lo autoriza.
- **Orden (C-3 confirmada):** alfabético y estable por nombre, con desempate por identificador interno. Criterio de comparación: sin distinguir mayúsculas ni acentos, con la «ñ» después de la «n» y antes de la «o»; el nombre mostrado no se altera. Nunca se ordena por cantidad ni por ningún otro valor (RF-47).
- **No entran:** planificaciones sin avances (conservadas o no), actividades marcadas por error, el resumen libre de la bitácora, actividades pendientes al corte sin avances en el período, correos, identificadores de acceso, credenciales, nombres de equipos y la auditoría.
- **Actividad iniciada en otro equipo:** forma neutral «Actividad en continuidad», sin título, origen ni motivos ajenos (RN-101; CA-277). Su estado al corte, si lo determina un avance de otro equipo, es `estado_no_disponible` (CA-235).

## 5. Respuesta: 200 con `informe` de `tipo` `consolidado`

### 5.1 Campos que implementa el núcleo determinista (M5-T2)

| Campo | Tipo | Definición | Estado |
|---|---|---|---|
| `tipo` | texto | Siempre `consolidado` | Contrato 0.1 |
| `periodo` | objeto `desde`, `hasta` | El período solicitado | Contrato 0.1 |
| `sin_datos` | booleano | Verdadero si el equipo no tiene ningún avance autorizado. Entonces `personas` está vacía y `agregaciones_del_equipo` es nulo | RN-57; CA-172, CA-173 |
| `personas` | lista ordenada | Una entrada por persona con al menos un avance autorizado (sección 4) | C-2, C-3 confirmadas |
| `agregaciones_del_equipo` | objeto | La **sección de equipo, determinista y sin narrativa** (D-M5-03). Mismas definiciones que las de cada persona aplicadas al conjunto de los hechos autorizados del equipo (sección 5.3). Nulo si `sin_datos` | C-4 confirmada |

Cada elemento de `personas`:

| Campo | Tipo | Definición |
|---|---|---|
| `persona` | objeto `id`, `nombre` | Solo el identificador y el nombre |
| `actividades` | lista | Las que algún hecho de la persona referencia, una vez cada una: `id` (opaco), `forma` (`completa` o `neutral`), `texto` (título si `completa`; «Actividad en continuidad» si `neutral`) y `planificada` (`true`, `false` o ausente si el origen está protegido) |
| `hechos` | lista por la secuencia de avances | Cada avance autorizado: `fecha_laboral`, referencia a su actividad, `estado` (histórico), `descripcion` y `motivo_bloqueo` (solo si Bloqueada) |
| `bloqueos` | lista | Cada avance Bloqueada con su motivo (`[ABIERTO]`: P-3) |
| `agregaciones` | objeto | Sección 5.3, de la persona |

La forma exacta de `hechos` y `actividades` es `[ABIERTA]`: P-5. Las referencias internas de los hechos no se exponen en la respuesta pública (PP-11 no aprobada).

### 5.2 Campos que se añadirán después `[PROPUESTO]`

| Campo | Quién lo aporta |
|---|---|
| `generado_en` (UTC) | M5-T4 (RF-48, RN-29) |
| `base` (declaración fija, RF-87) | M5-T4. Texto exacto `[ABIERTO]`: P-6 |
| `narrativa`, **dentro de cada elemento de `personas`**, texto o nulo | M5-T3 (interfaz y validación) y M5-T5 (integración). Única parte generada por IA. Una narrativa **por persona** (D-M5-03) a partir de los hechos y las cifras de esa persona; nula si `sin_datos`. No contiene valoraciones ni rankings (RF-47) |

Si la narrativa de una sola persona no puede generarse o no supera la validación, **no se devuelve contenido parcial**: el informe completo es `INFORME_NO_GENERADO` (RN-58; CA-174, CA-175).

### 5.3 Agregaciones (D-M5-04 **confirmada**: catálogo de seis métricas)

Recuentos deterministas sin porcentajes (RN-57), sobre los hechos autorizados, sin rankings ni puntuaciones. Por persona y para el equipo, con las mismas definiciones.

| Campo | Definición por persona | En `agregaciones_del_equipo` |
|---|---|---|
| `avances` | Avances autorizados en el período | Suma de los de las personas |
| `jornadas_con_registros` | Fechas laborales distintas con avances autorizados | **Fechas laborales distintas del conjunto autorizado** (C-4), no la suma de las de cada persona |
| `actividades_con_registros` | Actividades distintas con avances autorizados | Suma |
| `actividades_por_origen` | `planificadas`, `no_planificadas`, `origen_no_disponible` (sin inferir un origen protegido) | Suma de cada grupo |
| `actividades_con_bloqueo` | Actividades con algún avance autorizado Bloqueada en el período | Suma |
| `actividades_por_estado_al_corte` | Solo actividades con avances autorizados en el período; estado del último avance hasta `hasta` si está autorizado; grupos `pendiente`, `en_progreso`, `bloqueada`, `completada` y `estado_no_disponible` | Suma de cada grupo |

`estado_no_disponible` solo es un **recuento**: no identifica la actividad, no dice qué estado tiene y el estado protegido nunca sale de la base de datos. No se incluye la población de la vista de supervisión (M4-03).

## 6. Errores

| Código | HTTP | Cuándo |
|---|---|---|
| `NO_IDENTIFICADA` | 401 | No hay persona identificada |
| `ACCESO_DESACTIVADO` | 403 | Acceso desactivado (también el supervisor) |
| `SIN_PERTENENCIA_VIGENTE` | 403 | Sin pertenencia vigente |
| `SOLICITUD_INVALIDA` | 400 | Formato, `desde` posterior a `hasta` o campo desconocido |
| `OPERACION_NO_PERMITIDA` | 403 | Quien llama no es supervisor vigente con acceso efectivo |
| `RECURSO_NO_DISPONIBLE` | 404 | `equipo_id` ajeno o inexistente |
| `INFORME_EXCEDE_LIMITES` | 422 | Se rebasa un límite configurado, antes de generar. **Valores pendientes (D-M5-06)** |
| `INFORME_NO_GENERADO` | 503 | El servicio de IA falla, agota su tiempo o su salida no supera la validación (RN-58) |

Ningún mensaje ni detalle incluye títulos, descripciones, motivos, nombres de equipo ni contenido de registros.

## 7. Preguntas

### 7.1 Resueltas el 2026-11-18

| Id | Resolución |
|---|---|
| C-1 | **Aprobada:** este borrador con el esquema completo; el contrato 0.1 se mantiene sin sustituir hasta la revisión contractual |
| C-2 a C-6 | **Confirmadas** (secciones 3, 4 y 5) |
| D-M5-04 | **Confirmado** el catálogo de seis métricas y sus reglas |

### 7.2 Siguen abiertas

| Id | Qué dicen las fuentes | Qué falta decidir |
|---|---|---|
| **P-3** Unidad de `bloqueos` | Contrato 0.1: «Actividades bloqueadas con su motivo (RN-55)»; RF-74: «Los informes incluyen los bloqueos con sus motivos.» | Si la unidad es el avance bloqueado o la actividad. Provisional: por avance |
| **P-5** Campos públicos de `hechos` y `actividades` | Contrato 0.1: «Registros del período: fecha laboral, ActividadVisible, estado histórico, descripción y, si procede, motivo de bloqueo» | Qué campos de `ActividadVisible` lleva cada hecho (por ejemplo `estado_actual`) y si se repite la actividad o se referencia en una lista |
| **P-6** Texto de `base` | Contrato 0.1: «Declaración fija de que el informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada (RF-87)» | El texto exacto |
| **P-8** Valores de los límites | `convenciones.md` sección 9: ningún contrato fija un valor numérico; el 92 de M4 es solo de M4 | Los valores (D-M5-06) |
| **P-11** (nueva) | Contrato 0.1: `narrativa` = «Texto generado a partir de los hechos y las agregaciones recibidos» | Forma pública de la narrativa: un único texto por persona (secciones unidas con una línea en blanco, lo propuesto) o una lista de secciones. Se hace por persona (D-M5-03) |
| D-M5-06 | Valores de límites, tiempos y concurrencia | **Abierta.** Su propuesta para aprobación posterior se presentará con M5-T3 |

## 8. Criterios de aceptación vinculados

Sin cambios respecto a 0.1: CA-161 a CA-175, CA-199 a CA-202, CA-228, CA-229, CA-235 y CA-277. **Ningún criterio se modifica ni se declara cumplido**; la evidencia del núcleo está en el plan, sección 15.
