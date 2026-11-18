# SMARTWORK — Contrato M5-02 «Generar un informe consolidado»: versión 0.2 (aprobada)

| Campo | Valor |
|---|---|
| **Estado** | **APROBADO** el 2026-11-18 por la persona responsable del producto (versión 0.2; C-1 aprobada el mismo día). **Sustituye al contrato 0.1** de `m5-informes.md`, que se conserva como historial. Sigue abierta solo la parte parcial de P-8 (7.2) |
| **Versión** | 0.2 (aprobada) |
| **Fecha** | 2026-11-18 |
| **Base** | `m5-informes.md` 0.1; `m5-01-informe-individual-v0.2.md`; `docs/backlog/tickets/m5-plan-implementacion.md` (M5-T2 y M5-T3); PRD; historias HU-5.2 a HU-5.5; ADR-003; `convenciones.md`; política de visibilidad de M1 y M4 |
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

Cualquier otro campo es `SOLICITUD_INVALIDA`. **Límites (D-M5-06, 2026-11-18):** período máximo de **31 días con ambos extremos incluidos** (**confirmado**) y máximo de **400 hechos por solicitud**, que en el consolidado es el **total de todas las personas** juntas y no 400 por persona (**confirmado**); los excedidos se rechazan con `INFORME_EXCEDE_LIMITES`, sin truncar nada. Siguen **abiertos** los límites de tokens de entrada y de salida, el plazo y la concurrencia. **Implementación de M5-T4:** la ruta **no está registrada** en la aplicación porque la respuesta de éxito depende de las preguntas abiertas.

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

## 5. Respuesta: 200 con `informe` de `tipo` `consolidado` (esquema público, campo por campo)

`[PROPUESTO]` hasta la revisión contractual. Las claves del informe son **obligatorias**; lo que no aplica se envía vacío o `null`. Los elementos de `actividades`, `hechos`, `bloqueos`, `agregaciones` y `narrativa` de cada persona son **exactamente los definidos en `m5-01-informe-individual-v0.2.md`, secciones 4.2 a 4.6** (mismas formas, reglas de visibilidad y consistencia); aquí solo se define lo propio del consolidado. **No hay colecciones de actividades, hechos ni bloqueos al nivel del informe**: cada una vive dentro de su persona.

### 5.1 Campos del informe

| Campo | Tipo | Contenido y visibilidad | Origen |
|---|---|---|---|
| `tipo` | texto | Siempre `consolidado` | 0.1 |
| `periodo` | objeto | `desde` y `hasta` (fechas laborales ISO) | 0.1 |
| `generado_en` | texto, ISO 8601 UTC con `Z` | Momento real de generación | RF-48, RN-29 |
| `base` | texto | La **misma declaración fija de producto** que en M5-01 (4.1; P-6, confirmada): «Este informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada.». Redacción aprobada de producto, **no una cita literal de RF-87**. Siempre presente, también con `sin_datos` | RF-87 |
| `sin_datos` | booleano | Verdadero si el equipo no tiene ningún avance autorizado; entonces `personas` está vacía y `agregaciones_del_equipo` es `null` | RN-57 |
| `personas` | lista | Una entrada por persona con **al menos un avance autorizado** (C-2), en orden alfabético estable por nombre con desempate por identificador interno (C-3). Nunca por cantidad ni por otro valor (RF-47) | C-2, C-3 |
| `agregaciones_del_equipo` | objeto o `null` | La **sección de equipo, determinista y sin narrativa** (D-M5-03): las mismas seis métricas aplicadas al conjunto de los hechos autorizados del equipo (5.3) | C-4, D-M5-04 |

### 5.2 `personas[]`

| Campo | Tipo | Contenido |
|---|---|---|
| `persona` | objeto `id`, `nombre` | Solo el identificador y el nombre (P-13, confirmada). Solo de personas de la población aprobada (5.4) y solo en respuestas autorizadas; no se envían al generador de IA, que recibe un alias |
| `agregaciones` | objeto | Las seis métricas de la persona (M5-01, 4.5) |
| `actividades` | lista | Las de esa persona (M5-01, 4.2). Referencias `a1`… **únicas en todo el informe** |
| `hechos` | lista | Sus avances autorizados (M5-01, 4.3) |
| `bloqueos` | lista | Agrupados por actividad (M5-01, 4.4) |
| `narrativa` | lista o `null` | Una narrativa **por persona**: lista de secciones solo con `texto` (P-11). **`null` cuando `sin_datos` es verdadero está permitido**; con `sin_datos`, `personas` está vacía |

Si la narrativa de una sola persona no puede generarse o no supera la validación, **no se devuelve contenido parcial**: el informe completo es `INFORME_NO_GENERADO` (RN-58; CA-174, CA-175).

### 5.3 `agregaciones_del_equipo`

Las mismas seis métricas, con la misma definición aplicada al conjunto: `avances`, las actividades y los grupos son la **suma** de los de las personas; `jornadas_con_registros` son las fechas laborales distintas **del conjunto autorizado** (C-4), no la suma de las de cada persona.

| Campo | Definición (D-M5-04 **confirmada**) |
|---|---|
| `avances` | Cantidad de avances autorizados en el período |
| `jornadas_con_registros` | Fechas laborales distintas con avances autorizados |
| `actividades_con_registros` | Actividades distintas con avances autorizados |
| `actividades_por_origen` | Objeto `planificadas`, `no_planificadas` y `origen_no_disponible` (las de forma neutral: no se infiere un origen protegido) |
| `actividades_con_bloqueo` | Actividades con algún avance autorizado en estado Bloqueada durante el período (no «bloqueada al corte») |
| `actividades_por_estado_al_corte` | Objeto `pendiente`, `en_progreso`, `bloqueada`, `completada` y `estado_no_disponible`. **Solo** actividades con avances autorizados en el período; el estado es el del último avance hasta `hasta` (RF-70) y solo si está autorizado (RA-07, RN-88); si lo determina un avance protegido, la actividad va a `estado_no_disponible` y **no** se sustituye por un estado anterior. Los cinco grupos suman `actividades_con_registros` |

Todos son enteros no negativos, calculados con código determinista sobre los hechos autorizados, **sin porcentajes**, rankings ni puntuaciones. Se copian tal cual a la respuesta: no se recalculan ni se duplican.

### 5.4 Población y reglas

- Avances autorizados de las personas que **eran del equipo en la fecha laboral de cada avance** (RF-83; CA-228, CA-229); el trabajo de la propia supervisora cuenta si su pertenencia lo autoriza (C-5).
- No entran: planificaciones sin avances, actividades marcadas por error, el resumen libre, actividades pendientes al corte sin avances en el período, correos, identificadores de acceso, credenciales, nombres de equipos ni la auditoría.
- Actividad iniciada en otro equipo: forma neutral, sin título ni origen ni motivos ajenos (CA-277); su estado al corte, si lo determina otro equipo, es `estado_no_disponible` (CA-235).

### 5.5 Diferencias frente a la versión 0.1

| Aspecto | Versión 0.1 | Este borrador |
|---|---|---|
| Estructura | «agregaciones del equipo y, por persona en orden alfabético, sus hechos y bloqueos» | `personas[]` con su bloque completo y `agregaciones_del_equipo`; sin colecciones al nivel del informe |
| `narrativa` | Un único campo | Una lista de secciones por persona (D-M5-03, P-11) |
| `hechos`, `bloqueos` | Como en M5-01 0.1 | Como en M5-01 de este borrador (P-5, P-3) |
| Errores | Sin indicación de reintento | Con `reintento` y `motivo` (P-12) |

## 6. Errores

Los mismos que en M5-01 (sección 5), con estas particularidades:

| Código | HTTP | Cuándo |
|---|---|---|
| `OPERACION_NO_PERMITIDA` | 403 | Quien llama no es supervisor vigente con acceso efectivo: un colaborador, o quien fue supervisor y ya no lo es. Se evalúa **antes** que el equipo (C-6) |
| `RECURSO_NO_DISPONIBLE` | 404 | `equipo_id` ajeno o inexistente, indistinguible (CA-170, RNF-13) |
| `ACCESO_DESACTIVADO` | 403 | Un supervisor con el acceso desactivado no supervisa (RA-12) |
| `INFORME_EXCEDE_LIMITES` | 422 | Más de 31 días (extremos incluidos) o más de **400 hechos en total, de todas las personas juntas** (no 400 por persona); sin truncar |
| `INFORME_NO_GENERADO` | 503 | Basta una persona cuya narrativa falle |

El detalle de reintento (P-12) es el de M5-01, sección 5.

## 7. Decisiones y preguntas

### 7.1 Resueltas el 2026-11-18

| Id | Resolución |
|---|---|
| C-1 | **Aprobada** este borrador; el contrato 0.1 no se sustituye hasta resolver lo pendiente |
| C-2 a C-6 | **Confirmadas** |
| D-M5-03 | Narrativa por persona y sección de equipo determinista |
| P-6 | **Confirmada:** la declaración fija de producto es «Este informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada.». Es **redacción aprobada de producto**, no una cita literal de RF-87 (RF-87 fija la obligación, no el texto). Se usa en los dos tipos de informe, también con `sin_datos` |
| P-13 | **Confirmada:** se conserva el objeto público `persona` (`id`, `nombre`), solo en respuestas autorizadas; en el consolidado, solo las personas de la población aprobada. Ni el nombre ni el identificador van al generador de IA (alias y referencias internas) |
| Nombres de campo | **Confirmados:** `actividad_ref` (referencia opaca local al informe), `ocurrencias` (bloqueos autorizados agrupados por actividad), `titulo` y `origen` (solo si la política permite exponer el origen) y `referencia_neutral` (actividad heredada) |
| D-M5-04 | **Confirmado** el catálogo de seis métricas |
| D-M5-06 | **Confirmados** 31 días, 400 hechos **por solicitud (total del consolidado)**, 0 reintentos e `INFORME_HABILITADO` falso |
| P-3, P-5, P-11, P-12 | **Confirmadas** (ver M5-01, sección 6.1) |

### 7.2 Sigue abierta

| Id | Estado | Qué falta |
|---|---|---|
| **P-8** | **Parcial** | Siguen abiertos y **no se declaran confirmados**: tokens máximos de entrada (propuesta 64.000), tokens máximos de salida (2.000), plazo total (120 s) y concurrencia máxima (4 por proceso). Condicionan la integración real, no la forma de la respuesta |

## 8. Criterios de aceptación vinculados

Sin cambios respecto a 0.1: CA-161 a CA-175, CA-199 a CA-202, CA-228, CA-229, CA-235 y CA-277. **Este contrato no modifica ningún criterio ni declara ninguno cumplido**; la evidencia está en el plan de M5 (secciones 15, 17, 19 y 20) y la matriz de trazabilidad es de M5-T8.

## 8. Historial de versiones

| Versión | Fecha | Estado | Cambios |
|---|---|---|---|
| 0.1 | 2026-11-06 | `[PROPUESTO]`. Conservada en `m5-informes.md` como historial | Primera propuesta del contrato público de M5-02, independiente del proveedor de IA |
| 0.2 | 2026-11-18 | **Aprobada** por la persona responsable del producto | Esquema público completo campo por campo; `OPERACION_NO_PERMITIDA`; límites confirmados; reintento (P-12); declaración `base` (P-6); `persona` (P-13); nombres de campo; bloqueos agrupados (P-3); actividades y hechos con referencias (P-5); narrativa como lista de secciones (P-11). La trazabilidad frente a 0.1 está en la sección 5.5 y en el historial de decisiones de la sección 7 |
