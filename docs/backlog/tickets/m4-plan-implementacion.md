# SMARTWORK — Plan de implementación de M4 (consulta histórica y supervisión): análisis y tickets M4-T1 a M4-T9

| Campo | Contenido |
|---|---|
| **Estado** | `[PROPUESTO]`. Análisis SDD (M4-T0) sin código. **Nada de lo que propone este documento es requisito ni está aprobado**: las decisiones están en la sección 9 y las propuestas de tickets, de nombres y de parámetros llevan la marca `[PROPUESTO]` o `[ABIERTO]` hasta que la persona responsable las apruebe |
| **Versión** | 0.1 |
| **Fecha** | 2026-11-17 |
| **Base** | HEAD `5b6405d` (cierre técnico de M1 consolidado). M1, M2 y M3 cerrados en su alcance |
| **Fuentes leídas** | `docs/producto/alcance-mvp.md` y `prd.md` (RN-36, RN-47, RN-48, RN-81 a RN-90, RN-101, RN-105; RF-23 a RF-28, RF-45, RF-67 a RF-70, RF-83, RF-94, RF-95, RF-98, RF-99, RF-111, RF-115); `docs/modelo-datos/modelo-datos.md` (RA-01 a RA-12, DM-03, DM-04, DM-08, DM-09, DD-03, DD-04); `docs/api/m4-consulta-supervision.md` (M4-01 a M4-04, versión 0.5), `convenciones.md` (secciones 3, 6, 7 y 9), `indice.md`, `m2-bitacoras.md` y `m3-seguimiento-auditoria.md`; las cuatro historias de `docs/backlog/M4-…/`; `docs/backlog/tickets/{backend,frontend,base-de-datos,indice}.md`; `docs/evidencia/matriz-trazabilidad-m1.md` y `matriz-trazabilidad-m2-m3.md`; ADR-001 y ADR-002; y el código real: `app/compartido/{visibilidad,pertenencias,politica_acceso,dependencias}.py`, `app/modulos/{bitacoras,auditoria}/`, `app/errores.py`, `migrations/0001, 0003, 0004, 0010`, y `frontend/lib/features/logbook` |
| **No hace** | No implementa código, endpoints, migraciones ni pantallas; no modifica M1, M2 ni M3; no cambia el estado de ningún criterio; no avanza a M4-T1 |

## 1. Resumen del alcance de M4

M4 es **solo lectura**. Entrega cuatro contratos ya redactados (`m4-consulta-supervision.md`, todos «Cerrado» en el índice, sin código):

| Contrato | Ruta | Quién | Historia | Criterios vinculados |
|---|---|---|---|---|
| **M4-01** Consultar la bitácora de un compañero | `GET /api/v1/personas/{persona_id}/bitacoras/{fecha_laboral}` | Integrantes del equipo histórico del registro (colaboradores y supervisor) | HU-4.1 | 17 |
| **M4-02** Consultar el histórico por colaborador y fechas | `GET /api/v1/historico` | Según autorización de cada registro | HU-4.2 | 7 |
| **M4-03** Vista de supervisión del equipo en un período | `GET /api/v1/equipo/supervision` | Solo el supervisor con acceso efectivo (RA-12) | HU-4.3 | 29 |
| **M4-04** Historial de una actividad del equipo | `GET /api/v1/equipo/actividades/{actividad_id}` | Solo el supervisor con acceso efectivo | HU-4.4 | 9 |

**Criterios.** Las cuatro historias de M4 tienen 47 criterios propios (HU-4.1: 7, HU-4.2: 5, HU-4.3: 29, HU-4.4: 6). Los contratos vinculan 61 criterios distintos: los 47 más 14 de otras historias (CA-15 a CA-21, CA-176 a CA-178, CA-215 a CA-217 de HU-1.4 y CA-268 de HU-3.7). Además hay dependencias de M4 en M1 y M3 (sección 5): CA-03, CA-04, CA-30, CA-256 y CA-111.

**Decisiones del contrato ya confirmadas o aprobadas:** D-06 (el corte es el último día del período), D-07 («Actividad en continuidad» con identificador opaco), D-08 (rango obligatorio, persona opcional), D-09 (referencia mínima para la actividad heredada sin avances autorizados: *aprobada*, aún no marcada «sincronizada» en `indice.md`), D-10 (paginación configurable, decisión técnica aceptada), T-01 (404 indistinguible, aprobada) y D-11.

**Fuera de M4:** informes (M5), escritura sobre registros ajenos (no existe, CA-131 y CA-194), búsqueda por texto (no existe, CA-136), clasificaciones, rankings o puntuaciones de personas (RF-45), reactivación del acceso.

## 2. Qué existe hoy

### 2.1 Backend (M1, M2, M3)

| Pieza | Estado real | Dónde |
|---|---|---|
| «Equipo en una fecha» (DM-04) | **Implementada y probada** (M1-T1). Única definición del intervalo, con la misma expresión que la restricción de exclusión | `app/compartido/pertenencias.py` |
| Decisión de lectura (RA-01, RA-03, RA-10, RA-11, RA-12): `decidir_lectura`, `decidir_lectura_de_auditoria`, `Consultante`, `forma_de_actividad` (completa, neutral u oculta) | **Implementada y probada**, pero **ningún módulo la importa** (lo comprueba `test_ninguna_operacion_usa_todavia_la_politica_de_visibilidad_historica`, que M4 deberá actualizar a propósito) | `app/compartido/visibilidad.py` |
| Predicados SQL equivalentes (`condicion_lectura`, `condicion_lectura_auditoria`) con pruebas de equivalencia con la decisión en Python | **Implementados y probados** | ídem |
| Política de acceso de las rutas `/mi/…` (acceso desactivado, pertenencia vigente, fecha cubierta) | Implementada | `app/compartido/politica_acceso.py`, `dependencias.py` |
| Cálculo del estado actual y orden total de avances (fecha laboral, momento, id) | Implementado (M2-05) | `app/modulos/bitacoras/secuencia.py` |
| M2-01a, M2-07, M2-08, M3-07 | Implementados **solo para la propietaria**; lo ajeno responde siempre 404 `RECURSO_NO_DISPONIBLE` (convenciones 3.1, «provisional, pendiente de M4») | `modulos/bitacoras`, `modulos/auditoria` |
| Paginación `limite` / `continuar_desde` con cursor opaco y `siguiente` | Implementada **dos veces** (M2-08 y M3-07), con funciones privadas duplicadas; valores `pagination_default_limit=20` y `pagination_max_limit=100` | `servicio.py` de cada módulo, `config.py` |
| Organizaciones, equipos y pertenencias reales (CLI, traslados, finalización, desactivación) | Implementados y probados (M1) | `app/provision/` |

### 2.2 Frontend

Solo existe la experiencia de la propia persona (`features/logbook`: panel, bitácora, actividades, planificación, auditoría propia, etc.) y el inicio de sesión. **No hay pantallas, repositorios ni modelos de M4**; el rol `supervisor` solo cambia una etiqueta en el menú. El cliente no conoce `OPERACION_NO_PERMITIDA`.

### 2.3 Base de datos

No hay tablas ni columnas que falten para M4 (el equipo de un registro se deduce, no se almacena: DM-04). Índices existentes: exclusión GiST por persona y fecha, `pertenencia_equipo_idx (equipo_id, desde)`, `bitacora` única por `(persona_id, fecha_laboral)`, `avance (actividad_id, registrado_en, id)`, `avance (bitacora_id)`, `planificacion (bitacora_id)`, `actividad (propietaria_id)` y `(bitacora_origen_id)`, `auditoria (tipo_objeto, objeto_id, momento)`. **No se prevé ninguna migración**; DB-06 queda para decidir con los planes de ejecución reales (sección 8, M4-T2 y M4-T3).

## 3. Qué falta, y qué pertenece realmente a M4

| # | Tema pedido | Ya está en M2/M3/M1 | Falta y es de M4 |
|---|---|---|---|
| 1 | Consultar bitácoras históricas **propias** | M2-01a (una fecha), M2-08 (listado de actividades), M2-07 (detalle); la propietaria conserva su historial completo (RA-03, verificado con un traslado real) | Consulta **por rango** de fechas: es el caso «propias» de M4-02 (siempre incluye lo propio) |
| 2 | Actividades y bitácoras de **compañeros** | La política de lectura (sin uso) | M4-01 (bitácora de una fecha) y M4-02 (histórico). Las actividades de un compañero se ven **dentro** de su bitácora o del histórico, en forma completa o neutral; el contrato no prevé un endpoint de actividad para colaboradores (decisión D-M4-09) |
| 3 | Información de personas del equipo como **supervisor** | — | M4-03 y M4-04. **No existe ninguna forma de conocer quiénes integran el equipo ni sus nombres**: los contratos solo exponen `persona_id` (decisión D-M4-02, bloqueante para Flutter) |
| 4 | Permisos por pertenencias históricas | Política y predicados probados (M1-T1), con matriz de lectura, propiedad con líneas temporales aleatorias y equivalencia SQL ↔ Python | **Usarla** en las cuatro operaciones, sin segunda implementación |
| 5 | Avances y auditorías | M2-07 (avances propios); M3-07 solo propietaria (CA-111 pendiente) | Avances ajenos autorizados (M4-04 y dentro de M4-01); **auditoría para el supervisor** (extensión de M3-07: es un contrato de M3, bloqueado por M4) |
| 6 | Filtros, fechas, orden y paginación | `limite` y cursor opacos implementados | Rango obligatorio con **amplitud máxima configurable (parámetro nuevo, PA-13)**, orden estable por contrato (fecha, persona, id; estado al corte, propietaria, id) y un cursor que sirva a listados con claves distintas. Falta decidir el valor (D-M4-03) |
| 7 | 403 frente a 404 | Catálogo con 404 y los códigos de acceso | **`OPERACION_NO_PERMITIDA` no está en el catálogo de errores del backend ni en el cliente.** M4-03 y M4-04 lo necesitan (RN-13) y M2/M3 deberían emitirlo sobre recursos visibles pero ajenos (convenciones 3.1): D-M4-01 |
| 8 | Visibilidad tras traslados | Probada a nivel de dominio y base de datos con traslados reales | Prueba **HTTP** de extremo a extremo con traslado oficial (CA-15 a CA-18, CA-196, CA-197, CA-216, CA-217, CA-221, CA-222) |
| 9 | Desactivadas o sin pertenencia vigente | Quien consulta sin acceso efectivo no consulta nada; los registros de una persona desactivada o finalizada siguen siendo del equipo de su fecha (M1) | Lectura HTTP de esos registros por compañeros y supervisor (CA-30, CA-256) y tratamiento del equipo pendiente de supervisión efectiva en M4-03 (sección 5.2) |
| 10 | Planificaciones conservadas (DM-08) | CA-262 (se conservan los datos); la política las deja sin equipo (solo la propietaria); `planificacion_a_dict` presenta **toda** planificación como `vigente` | Proyección de clasificación para M4 (nunca las muestra como vigentes ni pendientes: CA-274). Con el MVP actual **no son alcanzables por ninguna ruta** (sin pertenencia no se opera y la reincorporación, PA-24, no existe): D-M4-07 |

## 4. Matriz de contratos y criterios de M4

La columna «Ticket» asigna cada criterio a quien lo demuestra. **Ningún criterio cambia de estado en este análisis**: el estado actual es el de la matriz de M1 y de la de M2/M3.

| Contrato | Criterios | Ticket |
|---|---|---|
| **M4-01** | CA-130, CA-132, CA-133, CA-193, CA-291; CA-15, CA-16, CA-17, CA-18, CA-21, CA-176, CA-177, CA-216, CA-217 | M4-T1 |
| | CA-131, CA-194 (solo lectura), CA-178 | M4-T1 (no hay ninguna ruta de escritura de M4) y M4-T6 (403 en las escrituras existentes) |
| **M4-02** | CA-134, CA-135, CA-136, CA-299, CA-300; CA-19, CA-20 (lo que alcanza al histórico; los informes son de M5) | M4-T2 |
| **M4-03 núcleo** | CA-137, CA-138, CA-139, CA-140, CA-141, CA-142, CA-143, CA-144, CA-145, CA-146, CA-147, CA-195, CA-198, CA-274 | M4-T3 |
| **M4-03 herencia entre equipos** | CA-196, CA-197, CA-218, CA-219, CA-220, CA-221, CA-222, CA-223, CA-230, CA-231, CA-232, CA-272, CA-301; CA-268 (de HU-3.7) | M4-T4 |
| **M4-04** | CA-148, CA-149, CA-150, CA-151, CA-233, CA-273, CA-275, CA-292; CA-215 | M4-T5 |
| **M3-07 para el supervisor** (contrato de M3) | CA-111 (RA-10); CA-110, CA-112 y CA-113 ya cubiertos para la propietaria | M4-T6 |

### 4.1 Criterios que la petición pide revisar, y su relación con M4

El **estado actual** es el de las matrices (no se modifica). «M4 aporta» es lo que habrá que demostrar.

| Criterio | Estado actual | Qué aporta M4 | Ticket |
|---|---|---|---|
| CA-03 (el colaborador no tiene la vista consolidada) | Parcial (M1): el rol se distingue | `OPERACION_NO_PERMITIDA` del colaborador en M4-03 (RN-13) | M4-T3 |
| CA-04 (el supervisor dispone de la vista consolidada) | Bloqueado por M4 | La vista M4-03 | M4-T3, T4, T8 |
| CA-05 (sin credenciales en pantallas, registros e informes) | Parcial (M1): sin informes | Las respuestas de M4 no añaden campos sensibles; se comprueba en el cierre. Los informes son de M5 | M4-T9 |
| CA-15 a CA-20 | Parcial (M1): política probada, sin consulta HTTP | M4-01 (CA-15 a CA-18), M4-02 (CA-19, CA-20; informes de M5) | M4-T1, T2 |
| CA-30 y CA-256 (lectura por «persona autorizada» tras una baja o desactivación) | Parcial (M1) | Lectura HTTP por compañeros y supervisor de registros de personas finalizadas o desactivadas. **Ninguno de los dos está vinculado hoy a un contrato de M4** (se verifican con M4-01, M4-02 y M4-03): hueco documental que se cierra al aprobar este plan | M4-T1, T2, T3 |
| CA-111 (el supervisor ve la auditoría) | Bloqueado por M4 | Extensión de M3-07 con `condicion_lectura_auditoria` | M4-T6 |
| CA-176 a CA-178 | Parcial (M1) | M4-01 (CA-176, CA-177); CA-178 (ninguna modificación ajena) con la ausencia de rutas de escritura y el 403 de M4-T6 | M4-T1, T6 |
| CA-216 y CA-217 | Parcial (M1) | M4-01 sobre una planificación futura de una persona trasladada | M4-T1 |
| CA-249 | **Implementado y probado en la matriz de M1**; la matriz de M2/M3 lo lista como «consulta HTTP de M4» | Habrá que comprobar la parte de consulta ajena antes de la fecha efectiva. **Posible discrepancia entre las dos matrices** (sección 7, hallazgo H-1) | M4-T1, M4-T9 |
| CA-260 y CA-261 | **Implementados y probados en M1** | Quedan como están. Lo que M4 añade (comportamiento de la vista con el equipo pendiente de supervisión efectiva) se clasifica **aparte** (sección 5.2) | — |

## 5. Dependencias

### 5.1 De M1, M2 y M3

| Dependencia | Qué se reutiliza | Qué obliga a tocar (con aprobación) |
|---|---|---|
| **M1** | `visibilidad.py` (decisión y predicados), `pertenencias.py`, `consultante_de`, la provisión y los traslados reales para las pruebas de extremo a extremo, la matriz de M1 | `app/errores.py` (añadir `OPERACION_NO_PERMITIDA`, archivo compartido); la prueba que prohíbe usar la política (M4-T1) |
| **M2** | Esquemas de salida (`bitacora_a_dict`, `planificacion_a_dict`, `avance_a_dict`, `actividad_a_dict`), `secuencia.py` (orden total y estado actual), cursores y límites, tablas | M4 **importa** sin modificar; las funciones privadas de paginación no son reutilizables tal cual (D-M4-08). Las siete rutas `/mi/…` con identificador de objeto (avances, corrección, reactivación, marca, reversión, continuación y detalle de actividad) deberán emitir 403 sobre recursos visibles ajenos (M4-T6) |
| **M3** | M3-07 (servicio y repositorio de auditoría), la regla RA-10 ya implementada en la política | Extensión para el supervisor (M4-T6) |
| **Flutter** | Patrones de repositorio con Riverpod, `FakeAdapter`, pruebas de widget, diseño responsive, `AppShell`, `ApiError` y catálogo de mensajes | Menú por rol y nuevos mensajes |

### 5.2 Comportamientos de M4 que no son de M1 (clasificación aparte, `[PROPUESTO]`)

CA-260 y CA-261 definen cómo M1 identifica el equipo pendiente de supervisión efectiva y que sus colaboradores no reciben funciones de supervisión. Lo que M4 añade, sin criterio propio todavía:

| Comportamiento | Fuente | Ticket |
|---|---|---|
| Un supervisor desactivado no consulta M4-03 ni M4-04 (`ACCESO_DESACTIVADO`) | RA-12, IR-37 | M4-T3, T5 |
| Un colaborador de un equipo pendiente recibe `OPERACION_NO_PERMITIDA` en M4-03 y M4-04: no hay supervisor efectivo y los permisos no se transfieren | RA-12, RN-13 | M4-T3, T5 |
| Los compañeros del equipo pendiente conservan la lectura entre pares (M4-01 y M4-02) | RA-12, RN-12 | M4-T1, T2 |
| La vista **no** informa del equipo pendiente ni propone un sustituto (sin funcionalidad nueva) | DD-04 | Verificación en M4-T3 |

## 6. Seguridad y autorización

### 6.1 Reglas existentes que M4 debe aplicar sin reescribir

| Actor | Regla (fuente) | Dónde está hoy |
|---|---|---|
| **Propietaria** | Lee todo lo suyo, sin filtro por equipo (RA-03), incluida la planificación conservada (RA-11) | `decidir_lectura` (motivo `propietaria`) |
| **Integrante activo del equipo** | Lee, solo lectura, los registros cuyo equipo en la fecha laboral es el suyo, aunque se haya incorporado después (RN-36, CA-193); no los de otro equipo ni los de períodos de otro equipo | `decidir_lectura`, `condicion_lectura` |
| **Supervisor** | Igual que un integrante para registros; la supervisión (M4-03, M4-04, auditoría) deriva solo de un intervalo de supervisor **vigente** con acceso efectivo (RA-12) | `Consultante.es_supervisor_vigente`, `condicion_lectura_auditoria` |
| **Persona trasladada** | El equipo de un registro es el de su pertenencia en la fecha laboral y no cambia después (RN-82): el equipo nuevo no lee lo anterior y el anterior no lee lo posterior | `pertenencia_en_fecha` |
| **Desactivada o sin pertenencia vigente** | No consulta nada, ni lo propio (IR-37, IR-38); sus registros siguen siendo del equipo de su fecha | `_rechazo_previo` |
| **Auditoría** | La ve la propietaria del registro y el supervisor autorizado del equipo de su fecha laboral; la de provisión, nadie (RA-10, D-11) | `decidir_lectura_de_auditoria` |
| **Lectura frente a escritura** | Nadie modifica registros ajenos (RN-23, RF-25); toda escritura cuelga de `/mi/…` | M2 y M3 |
| **Ocultación** | Recurso inexistente y no autorizado: 404 indistinguible (T-01); permiso insuficiente sobre un recurso visible: 403 `OPERACION_NO_PERMITIDA`; el filtro se aplica **al seleccionar**, también en recuentos, agrupaciones y estado al corte (convenciones 3.3) | Convenciones; falta el código 403 |

**Principio de diseño (`[PROPUESTO]`).** ADR-001 (D2 y D7) ya fija un módulo por cada M y una política única de autorización en el backend, aplicada a consultas, vistas e informes. Por tanto, un único camino: todo acceso de M4 pasa por `consultante_de`, `decidir_lectura`, `forma_de_actividad` y los predicados SQL de `visibilidad.py`. Si una regla de M4 no cabe ahí (referencia mínima, estado al corte autorizado), se **añade a esa política y se prueba con sus mismas propiedades**, no en el servicio de cada operación. Así se evita una segunda implementación contradictoria y los informes de M5 podrán reutilizar las mismas proyecciones (RA-09).

### 6.2 Riesgos de seguridad de M4

| # | Riesgo | Mitigación propuesta (`[PROPUESTO]`) |
|---|---|---|
| R-1 | Fugas por información derivada: totales por estado, número de elementos, cursor, orden o paginación calculados sobre registros no autorizados | Filtrar al seleccionar; recuentos y estado al corte solo sobre registros autorizados; pruebas con datos de otro equipo que cambien el resultado si hubiera fuga |
| R-2 | Referencia mínima o forma neutral que revele título, equipo anterior, número de avances, fecha del último avance o motivos de bloqueo (RA-04 a RA-06, CA-219, CA-220, CA-273) | Proyección única con lista cerrada de campos; pruebas que recorren todo el JSON buscando textos del equipo anterior |
| R-3 | Estado al corte determinado por un avance de otro equipo (RA-07, CA-230) | Calcular con la secuencia completa y mostrarlo solo si el avance que lo determina está autorizado; prueba con y sin avance autorizado (CA-230 y CA-231) |
| R-4 | Diferencia observable entre «no existe» y «no autorizado» en M4-01, M4-04 y errores de validación | Orden de evaluación de convenciones 3.2 (formato antes que recurso), mismo cuerpo y misma forma de respuesta; el canal de temporización queda como riesgo residual ya documentado |
| R-5 | Dos implementaciones de la regla de lectura (Python y SQL) que divergen | Reutilizar los predicados existentes y ampliar sus pruebas de equivalencia; no escribir condiciones de equipo a mano en los servicios (existe una prueba que vigila que el intervalo solo se defina en un lugar) |
| R-6 | Un colaborador o un supervisor desactivado obtiene la vista de supervisión | Comprobar `es_supervisor_vigente` y el acceso efectivo en cada petición, con la fecha real |
| R-7 | Enumeración de personas o fechas por sondeo (no hay límite de tasa en las lecturas) | Respuestas indistinguibles y rango de fechas acotado (D-M4-03); el límite de tasa de lecturas queda como pendiente de despliegue |
| R-8 | Rendimiento de las consultas por equipo y rango con la autorización aplicada al seleccionar | Planes de ejecución con datos de prueba (DB-06); decidir un índice solo con evidencia |
| R-9 | Exposición de datos personales de compañeros más allá de lo necesario (nombres, resumen libre) | Respuestas con la lista cerrada de campos de los contratos; el listado de integrantes (si se aprueba) solo con identificador, nombre y rol vigente |
| R-10 | Cambiar M2/M3 (404 a 403) rompe a la vez comportamiento cerrado | Ticket propio con aprobación, lista cerrada de operaciones y pruebas existentes actualizadas a propósito |

## 7. Hallazgos del análisis

| # | Hallazgo | Consecuencia |
|---|---|---|
| H-1 | CA-249 y CA-21 figuran como «Implementado y probado» en la matriz de M1 (verificados con el traslado y el comportamiento actual), y la matriz de M2/M3 los lista como dependientes de la consulta HTTP de M4 | No se cambian hoy. Al cerrar M4 (T9) se vuelve a verificar su parte de consulta ajena y, si la evidencia lo exige, se corrige la matriz con esa evidencia |
| H-2 | `OPERACION_NO_PERMITIDA` está en los contratos pero **no existe en `CATALOGO` ni en el cliente Flutter** | Añadirlo (M4-T3) con su mensaje fijo |
| H-3 | Los contratos de M4 solo exponen `persona_id`; no hay operación para listar integrantes ni mostrar nombres, y M1 dejó expresamente sin contrato «la consulta pública del historial de pertenencias y de la composición de un equipo» | Bloquea Flutter (FE-07, FE-08) y la elección del colaborador del filtro de M4-02: D-M4-02 |
| H-4 | CA-30 y CA-256 no están vinculados a ningún contrato de M4 | Vincularlos al aprobar el plan (cambio documental sin funcionalidad nueva) |
| H-5 | La amplitud máxima del rango de fechas es un parámetro **sin nombre ni valor** (convenciones 9, PA-13) y no existe en `config.py` | D-M4-03 |
| H-6 | La proyección de planificación presenta toda planificación como `vigente`; las conservadas (DM-08) existen en los datos pero son inalcanzables por la API | D-M4-07 |
| H-7 | El contrato M4-03 menciona `motivo_inclusion` y `totales_por_estado`, pero no define el vocabulario del primero ni si las referencias mínimas cuentan en los totales | D-M4-06 |
| H-8 | La paginación existe duplicada en M2 y M3 con cursores distintos (por `creada_en` y por `momento`) | D-M4-08 |
| H-9 | D-09 está «aprobada» pero no «sincronizada» en `indice.md` | Sincronizar la documentación al aprobar el plan |
| H-10 | Unas 8 a 10 pruebas de M2/M3 afirman 404 sobre registros de compañeros o del supervisor del mismo equipo (muchas con «todavía» en el nombre) y `test_auditoria_api` afirma que el supervisor no consulta la auditoría ajena | Se actualizan **a propósito** en M4-T6, no por inercia |

## 8. Plan de tickets

Distribución propuesta `[PROPUESTO]`: nueve tickets pequeños, ajustados a los contratos reales. Respecto a la distribución de partida (T1 consultas históricas, T2 compañeros, T3 supervisión y auditoría, T4 Flutter, T5 cierre) se hacen estos cambios y por qué:

- La **lectura de compañeros (M4-01) va primero** porque define la proyección de actividad completa o neutral que reutilizan todos los demás contratos; el **histórico (M4-02)** es una lectura por rango sobre la misma proyección.
- **M4-03 se divide en dos** (núcleo y herencia entre equipos) porque tiene 29 criterios y concentra el riesgo de seguridad. El núcleo **falla cerrado**: lo que necesita forma neutral o referencia mínima no se muestra hasta el ticket siguiente, de modo que ningún ticket intermedio puede filtrar datos.
- La **auditoría del supervisor y el 403 son cambios en módulos cerrados (M3 y M2)**: se separan en un ticket propio que exige aprobación expresa (D-M4-01).
- **Flutter se divide en dos** (lectura entre pares y supervisión) para no repetir una pantalla gigante.

Metodología de pruebas en todos los tickets (la acordada): pruebas focalizadas de la lógica que importa y de los casos críticos de seguridad, con PostgreSQL real solo donde aporte valor; **sin mutaciones rutinarias**, sin suite completa por ticket (solo en el cierre de módulo o ante un cambio transversal de riesgo) y sin cientos de pruebas. Las cifras de pruebas son un orden de magnitud `[SUPUESTO]`. Cada ticket termina con informe y espera aprobación antes del siguiente.

Orden y dependencias:

```
M4-T1 bitácora de un compañero (M4-01) + proyecciones compartidas
   ├─ M4-T2 histórico (M4-02)
   ├─ M4-T3 supervisión: núcleo (M4-03) ──► M4-T4 supervisión: herencia entre equipos ──► M4-T5 historial de actividad (M4-04)
   └─ M4-T6 extensiones de M2 y M3: 403 y auditoría del supervisor (requiere D-M4-01)
M4-T7 Flutter: lectura entre pares (T1, T2 y D-M4-02)
M4-T8 Flutter: supervisión (T3 a T6)
M4-T9 cierre técnico
```

### M4-T1 — Bitácora de un compañero y proyecciones compartidas (M4-01)

- **Objetivo:** leer, solo lectura, la bitácora de un integrante del equipo de una fecha en que pertenecía a él (incluido su supervisor), y dejar construida la proyección de actividad completa o neutral que usan los demás contratos.
- **Contratos:** M4-01 (y convenciones 3.1 a 3.3, esquemas compartidos). Prerrequisitos de documentación: vincular CA-30 y CA-256 (H-4) y sincronizar D-09 (H-9).
- **Criterios:** CA-130, CA-132, CA-133, CA-193, CA-291; CA-15 a CA-18, CA-21, CA-176, CA-177, CA-216, CA-217; CA-131 y CA-194 (ninguna ruta de escritura de M4); CA-30 y CA-256 (lectura de registros de personas finalizadas o desactivadas); verificación de CA-249 (H-1).
- **Componentes afectados:** **un único módulo de M4** (ADR-001, D2: un módulo por cada M1 a M5) `[PROPUESTO: app/modulos/consulta/]` con router, servicio, repositorio y esquemas, que alojará también la supervisión; proyección compartida de actividad (completa, neutral, oculta) en `app/compartido/` `[PROPUESTO]`, apoyada en `forma_de_actividad`; registro del router en `main.py`; actualización deliberada de `test_ninguna_operacion_usa_todavia_la_politica_de_visibilidad_historica`. **No se modifica M2 ni M3.** Si `persona_id` es la propia persona, la respuesta equivale a M2-01a (se reutiliza su proyección).
- **Dependencias:** M1-T1 (política). Ninguna decisión bloqueante.
- **Pruebas esenciales (~15):** colaborador lee a un compañero del equipo; supervisor y supervisor-como-compañero (CA-133); incorporado después (CA-193); fecha de otro equipo y fecha inexistente indistinguibles (CA-132, CA-291); traslado real con dos equipos (CA-15 a CA-18, CA-216, CA-217, CA-176, CA-177); persona finalizada o desactivada leída por un compañero (CA-30, CA-256); consultante desactivado o sin pertenencia (403 de acceso); actividad en forma neutral sin título ni marca; planificación conservada excluida para quien no es propietaria; orden de evaluación (formato antes que recurso); ninguna ruta de escritura.
- **Condiciones de cierre:** criterios anteriores con evidencia; ninguna respuesta contiene título, marca ni motivos de otro equipo; la política de M1 es la única fuente de decisión (pruebas de equivalencia vigentes); regresión focalizada de M2, M3 y de la política; documentación (contrato, matriz y este plan).

### M4-T2 — Histórico por colaborador y fechas (M4-02)

- **Objetivo:** recuperar lo que se hizo en un rango, filtrando opcionalmente por persona, con orden estable y paginación.
- **Contratos:** M4-02, convenciones 6.1 y 9.
- **Criterios:** CA-134, CA-135, CA-136, CA-299, CA-300; CA-19 y CA-20 (lo que alcanza al histórico); lectura de CA-30 y CA-256 en rango.
- **Componentes afectados:** módulo de M4; consulta SQL con `condicion_lectura` sobre `bitacora`; helpers de paginación y de validación de rango `[PROPUESTO: app/compartido/paginacion.py]` (código nuevo, sin refactorizar M2 ni M3: D-M4-08); parámetro de amplitud máxima en `config.py` y `.env.example` (D-M4-03); posible índice **solo si** el plan de ejecución lo exige (migración 0018 `[ABIERTO]`).
- **Dependencias:** M4-T1; D-M4-03 aprobada. D-M4-02 para el filtro desde Flutter, no para el backend.
- **Pruebas esenciales (~12):** rango obligatorio y exceso del máximo (`SOLICITUD_INVALIDA` con el máximo en detalles); parámetro desconocido y búsqueda por texto rechazados; filtro por persona con y sin autorización (lista vacía, no error); sin persona devuelve las autorizadas e incluye las propias; orden y cursor estables sin repetir ni omitir; cursor inválido; persona trasladada en rango que cruza el traslado; plan de ejecución con datos de prueba (DB-06).
- **Condiciones de cierre:** criterios con evidencia; el recuento y la página no dependen de registros no autorizados; decisión sobre el índice documentada con su plan de ejecución.

### M4-T3 — Vista de supervisión: núcleo (M4-03)

- **Objetivo:** vista consolidada del supervisor para un período, con inclusión, estado al corte, estado actual, totales y paginación, **sobre las actividades del equipo cuyo origen y avances están autorizados**.
- **Contratos:** M4-03 (primera parte), convenciones 3.1, 3.3, 6.1.
- **Criterios:** CA-137 a CA-147, CA-195, CA-198, CA-274; CA-03 y CA-04 (403 del colaborador y 200 del supervisor); comportamientos derivados de RA-12 (sección 5.2).
- **Componentes afectados:** módulo de M4; función pura de estado al corte `[PROPUESTO]` en el módulo nuevo (reutiliza `secuencia.ordenar` sin modificarla); `OPERACION_NO_PERMITIDA` en `app/errores.py` (H-2); parámetro de rango (T2); consulta con predicados de `visibilidad.py` y agregación de totales **antes** de paginar. Función pura de estado al corte en el propio módulo.
- **Dependencias:** M4-T1 (proyecciones), M4-T2 (paginación y rango); D-M4-04, D-M4-05 y D-M4-06 aprobadas.
- **Pruebas esenciales (~20):** inclusión por planificación, avances y pendiente al corte (CA-138 a CA-140); exclusión de completadas anteriores (CA-141); propias del supervisor (CA-142); estado al corte frente al actual (CA-143, CA-144, CA-198, con continuación posterior); marcadas por error (CA-147); planificación conservada (CA-274); totales coinciden con un recuento manual solo de lo autorizado (R-1); sin clasificaciones de personas (CA-145); colaborador y supervisor desactivado; equipo pendiente; solo lectura (CA-195); falla cerrado ante origen o avance no autorizado.
- **Condiciones de cierre:** criterios con evidencia; ninguna actividad con origen no autorizado aparece (se amplía en T4); planes de ejecución revisados (DB-06); matriz y contrato actualizados.

### M4-T4 — Vista de supervisión: herencia entre equipos (M4-03)

- **Objetivo:** presentar con seguridad las actividades que cruzan un cambio de equipo: forma neutral, referencia mínima y estado al corte condicionado.
- **Contratos:** M4-03 (segunda parte); esquemas `ActividadVisible` y `ReferenciaMínima`.
- **Criterios:** CA-196, CA-197, CA-218 a CA-223, CA-230, CA-231, CA-232, CA-272, CA-301; CA-268 (actividad marcada por error de otro equipo, de HU-3.7).
- **Componentes afectados:** proyección de referencia mínima y de planificación conservada `[PROPUESTO]` (D-M4-07) en `app/compartido/`; ampliación de la política **y de sus pruebas** con el estado al corte autorizado (RA-07) y la referencia mínima (RA-06, RA-08); módulo de M4.
- **Dependencias:** M4-T3; D-M4-06 y D-M4-07 aprobadas.
- **Pruebas esenciales (~20, con traslados reales):** supervisor del equipo nuevo sin registros anteriores (CA-196); del equipo anterior sin los posteriores (CA-197); referencia mínima con su lista cerrada de campos y distinguida (CA-218, CA-219, CA-232); sin fecha del último avance si es del equipo anterior (CA-220); equipo anterior sin estado actual (CA-221, CA-222); avance del equipo nuevo con su detalle y referencia neutral (CA-223, CA-272, CA-301); estado al corte con y sin avance autorizado (CA-230, CA-231); marcada por error de otro equipo oculta (CA-268); recorrido del JSON en busca de cualquier texto del equipo anterior.
- **Condiciones de cierre:** criterios con evidencia; **ninguna fuga** en las pruebas de recorrido del JSON; las propiedades de la política actualizadas siguen pasando (equivalencia SQL ↔ Python).

### M4-T5 — Historial de una actividad del equipo (M4-04)

- **Objetivo:** que el supervisor siga la evolución de una actividad de su equipo sin poder modificarla.
- **Contratos:** M4-04, D-09.
- **Criterios:** CA-148 a CA-151, CA-233, CA-273, CA-275, CA-292; CA-215.
- **Componentes afectados:** módulo de M4; proyecciones de T1 y T4.
- **Dependencias:** M4-T4.
- **Pruebas esenciales (~10):** avances autorizados en el orden de la secuencia con fecha y estado histórico (CA-148); actividad heredada sin avances autorizados devuelve solo la referencia mínima con 200 (CA-233, CA-292, D-09); título protegido (CA-275); motivos de otro equipo ocultos (CA-273); actividad completada heredada o de persona no supervisada igual que un recurso no disponible; colaborador recibe 403; sin clasificaciones (CA-151); solo lectura (CA-149, CA-150).
- **Condiciones de cierre:** criterios con evidencia; mismas pruebas de recorrido del JSON que T4.

### M4-T6 — Extensiones de M2 y M3: 403 en lo visible ajeno y auditoría del supervisor

- **Objetivo:** cumplir lo que los contratos ya piden y hoy está bloqueado por M4: respuesta 403 `OPERACION_NO_PERMITIDA` cuando una operación de escritura apunta a un registro visible de otra persona, y consulta de la auditoría por el supervisor autorizado (RA-10).
- **Contratos:** convenciones 3.1; M3-07 (CA-110 a CA-113); M2-04, M2-05, M2-07, M3-03 a M3-06.
- **Criterios:** CA-111; CA-178 y CA-194 (escritura sobre registros de compañeros); mantener CA-112, CA-113 y CA-286.
- **Componentes afectados (módulos cerrados, **requiere aprobación expresa**, D-M4-01):** siete rutas `/mi/…` con identificador de objeto (avances, corrección, reactivación, marca, reversión, continuación y detalle de actividad) y `servicio` y `repositorio` de auditoría. Comportamiento de lo invisible o inexistente: **sin cambios** (404).
- **Dependencias:** M4-T1 y D-M4-01.
- **Pruebas esenciales (~14):** por cada operación, un compañero del equipo recibe 403 y una persona de otro equipo o un id inexistente recibe el mismo 404 de siempre (indistinguible); el supervisor consulta la auditoría de su equipo en esa fecha y no la de otro equipo ni la de provisión; el compañero no consulta la auditoría ajena. Se actualizan a propósito las pruebas de M2/M3 que hoy afirman 404 sobre compañeros o supervisor (H-10).
- **Condiciones de cierre:** regresión focalizada de M2 y M3 (no la suite completa salvo que el cambio resulte transversal); lista cerrada de pruebas modificadas con su justificación; contratos y matrices de M2/M3 actualizados.

### M4-T7 — Flutter: lectura entre pares (FE-07)

- **Objetivo:** leer la bitácora de un compañero y recuperar el histórico, siempre en solo lectura.
- **Contratos:** M4-01, M4-02 (y el listado de integrantes si se aprueba D-M4-02).
- **Criterios:** los de M4-T1 y M4-T2 en su faceta de interfaz (sin botones de edición; el histórico no se envía sin rango; sin búsqueda por texto).
- **Componentes afectados:** `features/` nuevo o ampliación de `logbook` `[PROPUESTO]` con dominio, datos y presentación; navegación por rol en `AppShell`; mensajes de `OPERACION_NO_PERMITIDA` y de los errores nuevos; reutilización de widgets de lectura.
- **Dependencias:** M4-T1, M4-T2, D-M4-02 (sin él no se puede elegir a un compañero).
- **Pruebas esenciales (~15):** repositorio y modelos con `FakeAdapter`; pantalla de lectura sin acciones de edición; histórico con rango obligatorio, persona opcional y paginación; actividad neutral con «Actividad en continuidad»; diseño responsive; `flutter analyze`; recorrido representativo en Chrome.
- **Condiciones de cierre:** pruebas de widget y análisis sin incidencias; recorrido real con FastAPI y PostgreSQL desechable.

### M4-T8 — Flutter: supervisión (FE-08 y extensión de FE-09)

- **Objetivo:** que el supervisor vea el estado de su equipo en un período, el historial de una actividad y la auditoría de su equipo.
- **Contratos:** M4-03, M4-04, M3-07 (supervisor).
- **Criterios:** los de M4-T3 a T6 en su faceta de interfaz (sin clasificaciones de personas ni botones de modificación; la referencia mínima se distingue visualmente; estado al corte y estado actual indicado aparte).
- **Componentes afectados:** pantallas de supervisión, historial y auditoría de supervisor; selector de período; menú solo para supervisores con acceso efectivo.
- **Dependencias:** M4-T3, T4, T5, T6.
- **Pruebas esenciales (~20):** período y totales; elementos con estado al corte y actual; referencia mínima diferenciada; historial en solo lectura; ausencia de rankings; rol colaborador sin la opción; responsive; recorrido real con un traslado y un relevo (con el servidor de prueba de reloj controlado, como en M1-T5).
- **Condiciones de cierre:** como M4-T7.

### M4-T9 — Cierre técnico de M4

- **Objetivo:** cerrar el módulo con evidencia, clasificar cada criterio y revisar la consolidación.
- **Entregables:** matriz de trazabilidad de M4 (61 criterios más las dependencias de M1 y M3, con los estados «implementado y probado», parcial, pendiente, fuera de alcance aprobado o bloqueado) y reconciliación con las matrices de M1 y M2/M3 (H-1, con evidencia); regresión completa del backend y de Flutter; comprobación de migraciones solo si T2 creó alguna; recorrido real con FastAPI, Flutter Web y PostgreSQL desechable con un traslado, un relevo y una desactivación; revisión de seguridad focalizada de M4; actualización de contratos, ADR-002 si procede, alcance, README, plan y `prompts.md`; recomendación de commits (sin hacerlos sin autorización).
- **Condiciones de cierre:** sin defectos bloqueantes; ningún criterio declarado sin evidencia; pendientes de despliegue registrados.

## 9. Decisiones que requieren aprobación

Todas `[ABIERTO]` hasta que la persona responsable decida. La recomendación es una propuesta, no una regla.

### D-M4-01 — Alcance de los cambios en módulos cerrados (M4-T6)

| Alternativa | Implicaciones |
|---|---|
| **A. Aprobar en M4-T6 el 403 de las siete rutas y la auditoría del supervisor (recomendada)** | Cumple convenciones 3.1 (aprobada) y M3-07; cierra CA-111; obliga a actualizar unas 8 a 10 pruebas de M2/M3 a propósito; toca módulos cerrados con riesgo acotado (lista cerrada de operaciones) |
| B. Solo la auditoría del supervisor; mantener 404 en las escrituras | Obliga a **enmendar** convenciones 3.1 (T-01 está aprobada): una respuesta distinta de la documentada |
| C. Aplazar ambas | Deja CA-111 pendiente y la diferencia entre el contrato y el comportamiento; M4-01 mostraría un registro que las escrituras siguen tratando como inexistente |

### D-M4-02 — Cómo se elige a un compañero y se muestran los nombres

H-3: sin esto, Flutter no puede ofrecer M4-01, el filtro de M4-02 ni una vista de supervisión legible. Es una **ampliación del alcance** (un contrato nuevo) y requiere aprobación (CLAUDE.md, sección 8).

| Alternativa | Implicaciones |
|---|---|
| **A. Contrato nuevo de solo lectura `[PROPUESTO: M4-05]` que lista los integrantes vigentes del equipo con identificador, nombre y rol (recomendada)** | Mínimo dato necesario (R-9); sirve al selector de persona y a las pantallas; no cubre personas que ya no están en el equipo pero tienen registros históricos (limitación a documentar) |
| B. Añadir el nombre de la propietaria a las respuestas de M4-01 a M4-04 | Sin endpoint nuevo, pero no permite elegir a quién consultar y amplía cada respuesta |
| C. A y B | Más superficie de datos personales sin necesidad probada |

### D-M4-03 — Amplitud máxima del rango de fechas (parámetro de PA-13)

Hoy no existe parámetro ni valor. Se propone un parámetro de entorno (nombre `[PROPUESTO]`, por ejemplo `QUERY_MAX_RANGE_DAYS`), en días, común a M4-02 y M4-03, con `SOLICITUD_INVALIDA` y el máximo en `detalles` al excederlo (convenciones 6.1 y 9).

| Valor por defecto | Implicaciones |
|---|---|
| 31 días | Acota el coste y el sondeo; una consulta trimestral exigiría tres peticiones |
| **92 días (recomendada)** | Cubre un trimestre completo con coste razonable y sigue acotando el sondeo (R-7) |
| 186 días | Menos peticiones; más coste y más superficie de sondeo |

### D-M4-04 — Límites del período

El contrato exige `desde` y `hasta` pero no dice si `hasta` puede ser posterior a la fecha actual ni qué ocurre con `desde` posterior a `hasta`.

| Alternativa | Implicaciones |
|---|---|
| **A. `desde` ≤ `hasta` obligatorio; `hasta` futuro permitido, dentro de la amplitud máxima (recomendada)** | Permite ver lo planificado a futuro por el equipo; el estado al corte de un corte futuro es el del último avance existente |
| B. `hasta` no posterior a hoy | Más simple de razonar; impide ver planificación futura del equipo |

### D-M4-05 — Qué significa «la propietaria pertenece al equipo»

RN-47 la evalúa «en la fecha de corte» (para incluir pendientes) y RF-70 y CA-221 la usan para el **estado actual**. Propuesta `[PROPUESTO]`: la **inclusión** usa la pertenencia de la propietaria en la fecha de corte (`hasta`), y el **estado actual** solo se informa si la propietaria pertenece hoy al equipo del supervisor. Es una interpretación de textos que no la fijan con una sola frase; necesita confirmación.

### D-M4-06 — Detalles del contrato M4-03 que faltan

| Punto | Propuesta `[PROPUESTO]` | Efecto |
|---|---|---|
| Referencias mínimas y `totales_por_estado` | **No** entran en los totales (no tienen un estado al corte seguro, CA-230); la respuesta añade un recuento aparte de referencias mínimas | Cambia el contrato (versión 0.6) |
| Vocabulario de `motivo_inclusion` | Una lista con uno o más de `planificada_en_el_periodo`, `con_avances_en_el_periodo` y `pendiente_al_corte` | Cambia el contrato |

Alternativa: dejar la decisión para el diseño técnico de M4-T3; **no se recomienda**, porque define lo que el cliente Flutter y las pruebas esperan.

### D-M4-07 — Representación de las planificaciones conservadas (DM-08)

| Alternativa | Implicaciones |
|---|---|
| **A. Proyección compartida nueva para M4 que las clasifica por la cobertura de pertenencia y las excluye siempre; M2 queda como está (recomendada)** | No toca M2; con el MVP actual las conservadas no son alcanzables por la API, así que el `vigente` fijo de M2 no engaña a nadie hoy; el riesgo (si se admite la reincorporación, PA-24) queda anotado |
| B. Corregir también `planificacion_a_dict` de M2 | Cambia un módulo cerrado sin caso alcanzable que lo justifique |
| C. Aplazar | Dejaría CA-274 sin base de proyección |

### D-M4-08 — Paginación compartida

| Alternativa | Implicaciones |
|---|---|
| **A. Módulo compartido nuevo para M4; M2 y M3 no se tocan (recomendada)** | Sin riesgo para lo cerrado; queda una tercera copia lógica a unificar después |
| B. Unificar también M2 y M3 | Sin cambio de comportamiento, pero toca módulos cerrados |
| C. Copiar las funciones privadas en M4 | Más duplicación |

### D-M4-09 — ¿Los colaboradores consultan actividades sueltas de sus compañeros?

El contrato M4-04 es solo del supervisor. Las actividades de un compañero se ven dentro de su bitácora (M4-01) y del histórico (M4-02).

| Alternativa | Implicaciones |
|---|---|
| **A. No hay endpoint de actividad para colaboradores (recomendada; es lo aprobado)** | Sin cambios de alcance |
| B. Ampliar M4-04 a colaboradores | Exigiría una regla y una historia nuevas (alcance) |

## 10. Estado de este documento y de Git

- Este documento es lo **único** creado en M4-T0; no se ha tocado ningún otro archivo.
- Rama `feature/entrega-2-eq`, HEAD `5b6405d`. El documento queda **sin confirmar** en el árbol de trabajo. Sin commits, pushes ni merges. No se ha tocado `smartwork_app` ni el PostgreSQL 5432.
- Siguiente paso (si se aprueba): revisar las decisiones de la sección 9, vincular CA-30 y CA-256 a un contrato de M4 y sincronizar D-09 (cambios documentales), y autorizar **M4-T1**. No se avanza a M4-T1 sin esa autorización.
