# SMARTWORK — Plan de implementación de M5 (informes individuales y consolidados con IA): análisis y tickets M5-T1 a M5-T8

| Campo | Contenido |
|---|---|
| **Estado** | `[PROPUESTO]` salvo lo indicado. Análisis SDD (M5-T0). **Nada de lo que propone este documento es requisito ni está aprobado**: las decisiones para aprobar están en la sección 9; los tickets, los nombres, los parámetros y las cifras llevan la marca `[PROPUESTO]`, `[ABIERTO]` o `[SUPUESTO]` hasta que la persona responsable las apruebe |
| **Versión** | 0.2 |
| **Fecha** | 2026-11-18 |
| **Base** | HEAD `2c45ba5` (cierre técnico de M4 consolidado en dos commits locales). M1 a M4 cerrados en su alcance; M4 «cerrado con reservas». **Estado a 2026-11-18:** análisis M5-T0 aprobado por la persona responsable con las resoluciones de la sección 12; **M5-T1 implementado y probado localmente; cierre en un único commit local** (sección 14); D-M5-04 y D-M5-06 pendientes de detalle (sección 13) |
| **Fuentes leídas** | `docs/producto/alcance-mvp.md` y `prd.md` (RN-03, RN-06, RN-26, RN-29 a RN-31, RN-36, RN-53 a RN-58, RN-60, RN-82 a RN-90, RN-101; RF-29, RF-30, RF-32, RF-33, RF-46 a RF-51, RF-74 a RF-76, RF-78, RF-83, RF-87, RF-93, RF-94, RF-96, RF-98, RF-100, RF-111; RNF-04, RNF-06, RNF-08, RNF-12, RNF-13; PA-09, PA-13, PP-11, PP-33); las cinco historias de `docs/backlog/M5-…/` (HU-5.1 a HU-5.5); `docs/api/m5-informes.md` (0.1), `m1-m5-dependencias.md`, `convenciones.md` (secciones 3, 4 y 9); `docs/arquitectura/adr/ADR-001`, `ADR-002` y `ADR-003` (0.3, con la decisión del 2026-11-18); `docs/arquitectura/arquitectura-general.md` (secuencia 6.4, DT-03, DT-06, R-03, R-05, R-07); `docs/modelo-datos/modelo-datos.md` (P7, RA-09, DM-08); `docs/backlog/tickets/{backend,frontend,base-de-datos,indice}.md` (BE-15, BE-16, FE-10); `docs/backlog/tickets/m4-plan-implementacion.md`; las matrices de trazabilidad de M1 a M4; `CLAUDE.md`; y el código real de M4 y de la política de visibilidad: `app/compartido/{visibilidad,pertenencias,politica_acceso,paginacion}.py`, `app/modulos/consulta/{supervision,servicio,repositorio,proyecciones}.py`, `app/modulos/bitacoras/{esquemas,secuencia}.py`, `app/config.py`, `pyproject.toml` y la estructura de `frontend/lib/features` |
| **No hace** | No implementa código, endpoints, migraciones, dependencias ni pantallas; no configura AWS ni crea recursos; no envía ningún dato a ningún servicio; no modifica contratos, ADR ni matrices; no cambia el estado de ningún criterio; no avanza a M5-T1 |

## 0. Qué está decidido y qué no

| Tema | Estado | Fuente |
|---|---|---|
| Amazon Bedrock como servicio de modelos, AWS Lambda para la integración y AWS como plataforma de infraestructura relacionada | `[CONFIRMADO]` el 2026-11-18, **solo para planificación futura y sin implementar ni configurar AWS hasta esta revisión SDD** | ADR-003 (0.3), `alcance-mvp.md` (PA-09) |
| Stack: Flutter Web, FastAPI, PostgreSQL, REST; la IA detrás de una interfaz propia (DT-03) | `[CONFIRMADO]` | ADR-001, `arquitectura-general.md` |
| Contratos públicos M5-01 y M5-02, independientes del proveedor | `[PROPUESTO]` (0.1, 2026-11-06). Las historias y los criterios que los respaldan (38) son requisitos confirmados | `m5-informes.md` |
| Requisitos funcionales de M5 (RF-29, RF-30, RF-32, RF-33, RF-46 a RF-51, RF-74 a RF-76, RF-78, RF-87 y los de visibilidad histórica) | `[CONFIRMADO]` | PRD |
| RNF-06 (no enviar datos de bitácoras a un servicio externo hasta decidir proveedor, datos enviados y conservación) | **`[PROPUESTO]`**: se trata como **bloqueo de cautela** hasta que se apruebe | PRD, PP-33 |
| Modelo concreto de Bedrock, región o perfil de inferencia, modo de retención, servicios AWS adicionales | `[ABIERTO]` | ADR-003 (B2, B3, B4), PA-09 |
| Marco legal aplicable y país (B7), «qué es necesario» enviar (PA-09) | `[ABIERTO]` | ADR-003, PA-09 |
| Límites, tiempos, reintentos y presupuesto (B8, B9; PA-13) | `[ABIERTO]` | ADR-003, `convenciones.md` 9 |
| Catálogo de agregaciones (P-M5-1), registro técnico de consumo (P-M5-2), PP-11 (enlace de cada afirmación con su registro de origen) | `[ABIERTO]` / `[PROPUESTO]` sin aprobar | `m5-informes.md` |
| Resumen libre de la bitácora **excluido** de lo enviado al servicio de IA | `[CONFIRMADO]` por defecto (ADR-003, B6) | ADR-003 |

**Regla de esta planificación:** ningún elemento de la columna «abierto» se convierte en requisito por inferencia. La arquitectura de la sección 6 es una propuesta para aprobar, no una decisión tomada.

## 1. Resumen funcional de M5

M5 entrega **dos operaciones de lectura con efecto externo** (generar un informe consume un servicio de pago, pero **no modifica ningún dato**):

| Contrato | Ruta | Quién | Historia | Criterios vinculados |
|---|---|---|---|---|
| **M5-01** Generar un informe individual | `POST /api/v1/informes/individuales` | La propietaria de los registros o el supervisor autorizado de su equipo | HU-5.1 | 30 |
| **M5-02** Generar un informe consolidado | `POST /api/v1/informes/consolidados` | Solo el supervisor del equipo con acceso efectivo | HU-5.3 | 23 |

**Cómo se genera un informe (propuesta de comportamiento ya contenida en los contratos y en ADR-003):**

1. La persona indica un período (`desde`, `hasta`) y, opcionalmente, una persona (individual) o un equipo (consolidado). Por defecto, ella misma o el equipo que supervisa.
2. El backend decide **qué puede ver** esa persona con la política única de M1 y selecciona **solo** los registros autorizados del período (filtrado al seleccionar, convenciones 3.3).
3. Si no hay registros autorizados, el informe lo dice (`sin_datos`) y **no se llama al generador**.
4. Con registros, el backend calcula las **agregaciones deterministas** y prepara los hechos. El generador de texto recibe hechos y cifras ya calculados y solo **redacta**.
5. El backend **valida** la redacción de forma determinista. Si no supera la validación, o el servicio falla o agota su tiempo, la respuesta es `INFORME_NO_GENERADO` sin contenido parcial.
6. El informe se devuelve en pantalla: sin identificador, sin edición, sin historial. Cada generación es nueva y lleva su fecha.

**Periodo y filtros.** Solo `desde`, `hasta` y la persona o el equipo. No hay filtros por estado, texto ni proyecto (no existen en el producto). El período tiene una amplitud máxima configurable (`INFORME_EXCEDE_LIMITES` antes de generar).

**Qué contiene la respuesta.** `tipo`, `periodo`, `generado_en`, `base` (declaración fija de RF-87), `sin_datos`, `agregaciones` (deterministas, diferenciadas), `hechos`, `bloqueos` y `narrativa` (única parte generada por IA). Hechos verificables, cifras calculadas y texto generado son **tres cosas distintas y se distinguen en la respuesta y en la pantalla** (RF-46, CA-162).

**Fuera de M5 (no se añade nada):** chatbot, búsqueda semántica o RAG, recomendaciones, evaluaciones o puntuaciones de personas, rankings (RF-47), edición de informes, historial de informes (RN-56), exportación, informes programados o enviados por correo, enlace de cada afirmación con su registro (PP-11, no aprobada).

## 2. Requisitos y criterios existentes

### 2.1 Criterios propios de M5: 38

| Historia | Criterios | Cantidad |
|---|---|---|
| HU-5.1 Informe individual | CA-152 a CA-160, CA-224 a CA-227, CA-234, CA-276 | 15 |
| HU-5.2 Informes apoyados en los registros | CA-161 a CA-167 | 7 |
| HU-5.3 Informe consolidado | CA-168 a CA-171, CA-228, CA-229, CA-235, CA-277 | 8 |
| HU-5.4 Cuando faltan registros | CA-172, CA-173, CA-199 a CA-202 | 6 |
| HU-5.5 Servicio de IA no disponible | CA-174, CA-175 | 2 |
| **Total** | Los 38 están vinculados a M5-01 o M5-02 (la unión de ambas listas) | **38** |

### 2.2 Criterios relacionados de otros módulos que M5 completa o ejercita

| Criterio | Qué falta en M5 | Estado actual (matriz de M4) |
|---|---|---|
| **CA-19, CA-20** (RF-83) | La parte de **informes**: ni un informe ni un acceso directo entregan a U registros de P anteriores al traslado | Parcial: la parte de consultas está probada |
| **CA-05** (RNF-08) | Que los informes no contengan credenciales en claro | Parcial: pantallas y registros de M1 a M4 probados; faltan los informes |
| **CA-02** (RF-01) | Quien no se ha identificado no genera informes | Su parte de M1 está probada; M5 añade la comprobación en las dos rutas |
| **RNF-04** (fiabilidad) | Muestra de informes contrastada con los registros (se verifica con CA-161) | Pendiente de M5 |
| **RNF-12** (texto libre como datos) | CA-166 | Pendiente de M5 |
| **RNF-13** (existencia indistinguible) | La misma respuesta ante una persona o un equipo inexistente y no autorizado | Pendiente de M5 |
| **RNF-06** (privacidad ante el servicio externo) | `[PROPUESTO]`: condiciona el primer envío real | Sin aprobar |

### 2.3 Reglas de negocio de referencia

RN-03, RN-06, RN-26, RN-29 a RN-31, RN-36, RN-53 a RN-58, RN-60, RN-82 a RN-90, RN-101. Las reglas ya implementadas que M5 **reutiliza sin reescribir** son las de visibilidad histórica (RA-01 a RA-12, RN-36, RN-82, RN-86, RN-88, RN-101): la política vive en `app/compartido/visibilidad.py` y sus predicados SQL.

## 3. Contratos disponibles y faltantes

**Disponibles** (`m5-informes.md` 0.1, `[PROPUESTO]`): M5-01 y M5-02 con propósito, ruta, entrada, validaciones, autorización, catálogo de errores y criterios vinculados. Los códigos `INFORME_EXCEDE_LIMITES` (422) e `INFORME_NO_GENERADO` (503) ya figuran en el catálogo de `convenciones.md`.

**Faltantes o por corregir antes de programar** (hallazgos del análisis; ninguno cambia un requisito confirmado):

| Id | Hallazgo | Consecuencia | Ticket afectado | Decisión |
|---|---|---|---|---|
| H-M5-1 | **Esquema campo por campo** de `agregaciones`, `hechos`, `bloqueos` y `narrativa`: el contrato solo da la descripción y un catálogo propuesto. No hay tipos, nombres de campo ni forma de la persona en el consolidado | M5-T1 no puede fijar la respuesta sin una versión 0.2 del contrato | M5-T1, M5-T2, M5-T4 | D-M5-04, D-M5-03 |
| H-M5-2 | **Forma de la narrativa del consolidado**: el contrato define un único campo `narrativa`, pero el consolidado agrupa a varias personas | Si la narrativa es única, un solo texto mezcla a todas las personas; si es por persona, el esquema cambia | M5-T2, M5-T3 | D-M5-03 |
| H-M5-3 | **403 frente a 404 en M5-01**: el contrato responde `RECURSO_NO_DISPONIBLE` a quien pide el informe de una persona no autorizada, pero las convenciones (3.1, 3.2) reservan el 403 `OPERACION_NO_PERMITIDA` para un recurso **visible** sobre el que falta permiso. Un compañero del mismo equipo ve los registros de la persona (RN-36) pero no puede generar su informe (CA-154) | Dos lecturas posibles del mismo caso | M5-T4 | D-M5-02 |
| H-M5-4 | **No hay contrato interno entre FastAPI y la integración de IA** (entrada, salida, errores, versión). ADR-003 lo describe en prosa | Hay que redactarlo antes de implementar el adaptador | M5-T3, M5-T5 | D-M5-01 |
| H-M5-5 | **Parámetros sin nombre ni unidad**: los límites de M5 solo figuran en `convenciones.md` 9 como categoría. No existe el parámetro ni su valor | Sin ellos no se puede implementar `INFORME_EXCEDE_LIMITES` | M5-T3 | D-M5-06 |
| H-M5-6 | **Catálogo de agregaciones sin aprobar** (P-M5-1) | Condiciona el cálculo y los criterios CA-162 y CA-164 | M5-T1 | D-M5-04 |
| H-M5-7 | **El generador no puede garantizar «sin valoraciones» (CA-163)** de forma determinista. La validación detecta cifras, alias, referencias y entidades ausentes, pero no el tono | Debe quedar documentado como control por instrucción y revisión de muestra, no como garantía | M5-T3, M5-T7 | D-M5-05 |
| H-M5-8 | **Registro técnico de consumo** (P-M5-2) sin decidir. Un contador por equipo y día exigiría una tabla nueva | Define si M5 necesita migración | M5-T3 | D-M5-07 |
| H-M5-9 | **PP-33 y RNF-06 siguen `[PROPUESTO]`**: ninguna llamada real a Bedrock está autorizada | El desarrollo debe funcionar entera con un generador simulado y con la integración **desactivada por defecto** | M5-T5, M5-T7 | D-M5-08 |
| H-M5-10 | **Reutilización de lógica de M4**: el estado al corte y la inclusión de actividades están en `supervision.py` como funciones privadas. M5 necesita el mismo resultado (RN-86) | Copiarlas duplicaría reglas; extraerlas modificaría un módulo cerrado | M5-T1, M5-T2 | D-M5-09 |
| H-M5-11 | La interfaz de M4 solo lista a los integrantes **actuales** (M4-05). El contrato de M5 admite el informe de una persona que **ya no integra** el equipo (RN-53, CA-224, CA-225) | El backend lo soporta; la pantalla no podría elegir a esa persona | M5-T6 | Mejora no bloqueante (sección 10) |

## 4. Datos que deben utilizar los informes

### 4.1 Fuente de verdad

PostgreSQL. **La IA no es fuente de hechos**: redacta sobre hechos y cifras ya seleccionados y calculados (RN-26, RN-29, CLAUDE.md sección 9). Nada generado se persiste ni sustituye un registro.

### 4.2 Qué se usa (propuesta alineada con ADR-003, sección 7, y con las proyecciones de M4)

| Dato | ¿Se usa? | Observación |
|---|---|---|
| Período solicitado | Sí | `desde` y `hasta` |
| Por avance: fecha laboral, estado histórico, descripción | Sí | Solo avances autorizados para quien genera el informe (RA-01, RN-86) |
| Motivo de bloqueo, en los avances Bloqueada | Sí | RN-55, CA-165. Nunca el de registros de otro equipo (RN-101) |
| Título de la actividad | Sí, **solo si el origen está autorizado**; si no, «Actividad en continuidad» | RN-101, CA-276, CA-277 |
| Planificada o no planificada | Sí | Catálogo de agregaciones |
| Cifras deterministas (D-M5-04) | Sí, **como hechos dados** | El texto no calcula cifras: las recibe |
| Estado al corte | Solo si deriva de un avance autorizado; si lo determina otro equipo, se **omite** | RN-88, CA-234, CA-235 |
| Referencia mínima de una actividad heredada | Solo en la vista del equipo nuevo, sin título, descripciones ni motivos | RN-84, RF-94, CA-226 |
| **Resumen libre de la bitácora** | **No** | Excluido por decisión (ADR-003, B6) |
| Actividades marcadas por error | No se cuentan ni se envían | CA-167 |
| Planificación conservada (fecha no cubierta por pertenencia) | No | RA-11, DM-08 |
| Auditoría, datos de otros equipos, nombre del equipo | No | ADR-003, sección 7 |
| Identificadores internos, correos, nombres reales, credenciales | **Nunca** | Ver 4.3 |

### 4.3 Qué se oculta o transforma antes de salir del backend

1. **Seudonimización por petición** (ADR-003, sección 6, B5 propuesto): cada persona se sustituye por un alias («Persona 1», …); la tabla de alias vive solo en memoria durante la generación y el informe final se reconstruye localmente. El nombre real aparece únicamente en la respuesta que el backend devuelve a quien la pidió.
2. **Identificadores opacos por petición** para cada hecho (`h1`, `h2`, …), no los identificadores de la base de datos. Sirven para que la validación enlace cada afirmación con su hecho de origen (sin mostrarlo: PP-11 no está aprobada).
3. **Lista cerrada de campos**: el cuerpo que sale es construido por una función con campos explícitos, no serializando filas. Así ninguna credencial, correo ni identificador puede entrar por descuido (RNF-08, CA-05). Se verifica con una prueba de lista cerrada.
4. **Texto libre como dato** (RN-31): se entrega estructurado y delimitado, nunca concatenado a las instrucciones (sección 6.5).
5. **Límite reconocido:** las descripciones y los motivos pueden contener nombres propios u otros datos personales. No hay filtro fiable; se trata como dato personal potencial y se minimiza lo enviado.

## 5. Reglas de autorización

La autorización **es la de M1 a M4, sin política paralela**: se decide en el backend, antes de seleccionar, con `consultante_de`, `decidir_lectura`, `condicion_lectura`, `condicion_equipo` y `forma_en_supervision` de `app/compartido/visibilidad.py`.

| Regla | Origen | Cómo se aplica en M5 |
|---|---|---|
| Sin persona identificada, no se genera | RN-61, CA-02 | Dependencia de sesión existente (`NO_IDENTIFICADA`) |
| Acceso desactivado o sin pertenencia vigente | RN-96, RN-97 | `ACCESO_DESACTIVADO`, `SIN_PERTENENCIA_VIGENTE`, **antes** de cualquier dato |
| Informe individual: propietaria o supervisor del equipo | RN-53, CA-152 a CA-154 | Compañero sin ser supervisor: no puede (ver H-M5-3 y D-M5-02) |
| Informe consolidado: solo el supervisor con acceso efectivo, de su equipo | RN-54, RA-12, CA-168 a CA-170 | Colaborador: 403; equipo ajeno: 404 indistinguible |
| La propietaria obtiene todos sus registros del período, de ambos equipos | RF-93, CA-227 | La política concede la lectura del propio historial |
| El supervisor del equipo anterior obtiene solo los registros históricos de su equipo y de los períodos que conserva, sin nada posterior | RF-96, CA-157, CA-224, CA-225 | Cada registro se evalúa con `condicion_lectura` en su fecha laboral |
| El supervisor del equipo nuevo no recibe los detalles del equipo anterior; puede recibir la referencia mínima | RF-94, CA-226 | Mismas proyecciones que M4 |
| Sin estado al corte derivado exclusivamente de registros de otro equipo | RN-88, CA-234, CA-235 | `estado_al_corte_es_visible` |
| Sin título original ni motivos de bloqueo de otro equipo | RN-101, CA-276, CA-277 | Forma neutral |
| Personas trasladadas en el consolidado: solo los registros de las fechas que pertenecen históricamente al equipo | RF-83, CA-228, CA-229 | Pertenencia por fecha laboral |
| El filtro se aplica **al seleccionar**: totales, agregaciones y estado al corte solo sobre lo autorizado | Convenciones 3.3, RA-09 | Ningún agregado se calcula sobre datos que luego se oculten |
| Persona o equipo inexistente y no autorizado: respuestas indistinguibles | RNF-13, T-01 | Mismo código, mensaje y estructura |

**Equivalencia con M4 (prueba de coherencia):** para el mismo período, los recuentos por estado al corte del consolidado deben coincidir con `totales_por_estado` y `sin_estado_al_corte` de la vista de supervisión (M4-03). Es la comprobación proporcionada de RN-86: una sola política, dos presentaciones.

## 6. Propuesta de arquitectura AWS `[PROPUESTO]`

### 6.1 Responsabilidades

| Componente | Responsabilidad | No hace |
|---|---|---|
| **FastAPI (módulo `informes`, propuesto `app/modulos/informes/`)** | Autenticación y autorización; formato y límites de la petición; selección de registros autorizados; agregaciones deterministas; seudonimización; construcción del cuerpo mínimo; llamada a la interfaz de generación; **validación determinista de la salida**; reconstrucción de los nombres; respuesta o `INFORME_NO_GENERADO`; registro técnico sin contenido | No conoce el proveedor, el modelo ni la región. No importa el SDK del proveedor fuera del adaptador |
| **Interfaz propia de generación** (`GeneradorDeTexto`, DT-03) | Contrato interno estable entre el dominio de informes y cualquier proveedor. Adaptadores: ninguno (desactivado), simulado (desarrollo y pruebas) y AWS | No contiene lógica de informes |
| **AWS Lambda** (propuesto: **adaptador por proveedor**, ADR-003 sección 14) | Valida el esquema de entrada y su tamaño; construye el prompt (instrucciones fijas del sistema y datos delimitados); llama a Bedrock con los parámetros fijados; verifica el esquema de la salida; traduce los fallos a códigos del contrato interno; devuelve el uso de tokens | **No accede a PostgreSQL, no conoce la autorización, no guarda nada, no registra contenido, no lleva la tabla de alias** |
| **Amazon Bedrock** | Inferencia del modelo elegido, sin herramientas, sin acceso a la red, en el modo de retención verificado | No recibe identificadores, correos, nombres reales ni el resumen libre |

**Por qué el prompt vive en Lambda y la validación en FastAPI.** El prompt y las particularidades del modelo (formato de la llamada, parámetros admitidos) son del proveedor: cambiarlos no debe tocar el dominio ni el contrato público. La validación de la salida necesita los hechos autorizados y la tabla de alias, que **no deben salir de FastAPI**.

### 6.2 Alternativas de integración

| Opción | Descripción | Ventajas | Riesgos | Valoración |
|---|---|---|---|---|
| **A. FastAPI → Lambda (invocación síncrona con el SDK de AWS) → Bedrock** | La API invoca la función y espera la respuesta | Respeta la decisión confirmada (Lambda). Sin API Gateway ni URL pública. La autenticación es IAM, no un secreto compartido. El adaptador queda aislado. Un solo salto de red antes del modelo | Añade una dependencia (SDK oficial, `[A APROBAR]`). Latencia y arranque en frío. Cuando FastAPI no corre en AWS necesita credenciales para invocar la función (ver 6.7) | **Recomendada** |
| B. FastAPI → Bedrock directamente | La API llama al modelo | Menos piezas, menos latencia | **Contradice la decisión confirmada de usar Lambda para la integración.** Descartada salvo que se revise esa decisión | No |
| C. Lambda expuesta por URL de función o API Gateway, llamada por HTTP | La API llama a una URL | Cliente HTTP ya disponible (`httpx`) | Una superficie pública que proteger; más configuración; API Gateway no está justificado por ninguna necesidad contractual | No hasta que haya necesidad |
| D. Lambda asíncrona con cola y almacén de resultados | La petición devuelve un identificador y se consulta después | Tolera trabajos largos | **Introduce persistencia y un recurso consultable, que RN-56 y RF-75 excluyen** (el informe «no tiene identificador ni recurso para consultarlo después»). Exige SQS u otro almacén temporal | No: requeriría una decisión de producto nueva |

### 6.3 Flujo propuesto

```mermaid
sequenceDiagram
  participant C as Cliente web
  participant F as FastAPI (módulo informes)
  participant P as Política de M1
  participant D as PostgreSQL
  participant L as Lambda (adaptador)
  participant B as Bedrock

  C->>F: POST informe (desde, hasta, persona o equipo)
  F->>P: ¿Puede generarlo y para quién?
  P-->>F: Alcance autorizado o rechazo (403/404)
  F->>F: Límites: período, registros, tokens (antes de generar)
  F->>D: Registros autorizados del período
  alt Sin registros autorizados
    F-->>C: Informe sin_datos (no se llama a Lambda)
  else Con registros
    F->>F: Agregaciones deterministas, alias y ids opacos
    F->>L: Cuerpo mínimo (versión, período, hechos, agregaciones)
    L->>B: Instrucciones fijas + datos delimitados (sin herramientas)
    alt Fallo, tiempo agotado, salida inválida
      L-->>F: Error de contrato interno
      F-->>C: INFORME_NO_GENERADO (sin contenido parcial)
    else Respuesta estructurada
      B-->>L: Texto y referencias
      L-->>F: Esquema verificado y uso de tokens
      F->>F: Validación determinista (refs, cifras, alias, entidades)
      alt No supera la validación (como máximo un reintento)
        F-->>C: INFORME_NO_GENERADO
      else Supera
        F->>F: Reconstruir nombres; distinguir hechos, cifras y narrativa
        F-->>C: Informe en pantalla (sin conservarlo)
      end
    end
  end
```

### 6.4 Contratos internos `[PROPUESTO]` (a documentar como `docs/api/m5-integracion-ia.md` en M5-T3)

**Entrada a la interfaz de generación:** `version`; `tipo`; `periodo`; una o varias **personas** (alias), cada una con sus **hechos** (id opaco, fecha laboral, texto de actividad —título o «Actividad en continuidad»—, estado histórico, descripción, motivo de bloqueo si procede, planificada o no) y sus **agregaciones**; `idioma`; y, si procede, los límites de salida. Lista cerrada de campos.

**Salida:** `version`; secciones de **texto plano** (por persona en el consolidado, según D-M5-03), cada una con la lista de **ids de hechos** que respalda; `uso` (tokens de entrada y salida) y un código de fin. Sin HTML, sin enlaces ni imágenes (ADR-003, sección 8).

**Errores del contrato interno:** `NO_DISPONIBLE`, `TIEMPO_AGOTADO`, `LIMITADO` (limitación de peticiones del proveedor), `SALIDA_INVALIDA`, `CONTENIDO_RECHAZADO`, `ENTRADA_INVALIDA`. Hacia el cliente todos se traducen a `INFORME_NO_GENERADO` (con la indicación de si se puede reintentar) o a `INFORME_EXCEDE_LIMITES`, sin detalles del contenido.

### 6.5 Validación estructural y de contenido de la salida

| Control | Tipo | Qué detecta | Qué **no** garantiza |
|---|---|---|---|
| Esquema de la salida (campos, tipos, tamaños) | Determinista | Estructura inválida, HTML o enlaces | — |
| Cada sección enlaza con ids de hechos que existen y están autorizados | Determinista | Afirmaciones sin origen | Que el texto describa fielmente el hecho |
| Cada cifra del texto coincide con las calculadas | Determinista | Cifras inventadas o alteradas | — |
| Alias y fechas ⊆ los entregados | Determinista | Personas o fechas inventadas | Nombres propios no previstos dentro de una frase |
| Entidades ausentes en la entrada (nombres capitalizados, actividades) | **Heurístico** | Inventos evidentes | No es exhaustivo: queda como riesgo residual |
| Ausencia de valoraciones y de rankings (CA-163) | **Instrucción + revisión de muestra** | — | **No hay control determinista fiable**: debe aceptarse como riesgo residual (D-M5-05) |
| Resistencia a órdenes en el texto libre (CA-166) | Separación estructural, instrucción, salida con esquema y **pruebas adversariales** | Obediencia a una orden contenida en un dato | — |

Si cualquier control determinista falla, es un fallo de generación: **como máximo un reintento** y después `INFORME_NO_GENERADO` (ADR-003, sección 9). No se muestra nada hasta que la validación termina (sin respuesta en flujo).

### 6.6 Latencia, tiempos y modo de ejecución

La generación es **síncrona** (alternativa D descartada por RN-56). Hay que acotar el tiempo total con un **plazo global** configurable que englobe la invocación de Lambda, la llamada al modelo y el reintento; al agotarse, `INFORME_NO_GENERADO`. El consolidado es el caso crítico: una llamada con muchas personas aumenta la entrada y la latencia (ver D-M5-03). Los límites técnicos del servicio (tamaño de la carga de la invocación síncrona, tiempo máximo de la función, cuotas y limitación de peticiones del modelo) deben **verificarse en la cuenta** y no se dan por conocidos aquí `[A VERIFICAR]`.

### 6.7 Configuración y protección de credenciales

- Toda configuración de la integración es un parámetro de entorno leído por `app/config.py` (sin valores en el código), con la integración **desactivada por defecto**.
- Ninguna credencial de AWS en el repositorio, en los documentos, en los prompts ni en los registros (RNF-08, CLAUDE.md sección 6).
- **Identidad con permiso mínimo:** solo para invocar **esa** función; la función, a su vez, solo para invocar **ese** modelo o perfil. Cómo obtiene FastAPI su identidad depende de **dónde se despliegue**, que sigue sin decidir (ADR-003, sección 17): un rol asignado al servicio si corre en AWS, o credenciales temporales y rotables inyectadas como secreto si corre fuera. **No se decide aquí**; se difiere al ticket de despliegue.
- El registro de invocaciones del proveedor permanece **desactivado**.

### 6.8 Registro de operaciones sin datos sensibles

Un registro técnico por generación: tipo, período (fechas), resultado (éxito o código de error), duración, tokens, número de hechos y número de reintentos. **Sin** nombres, alias, textos, prompts ni respuestas, y sin identificadores de persona si no son imprescindibles (D-M5-07). Una prueba verifica con una cadena marcadora que no aparece en ningún registro.

### 6.9 Costes y límites de consumo

- **Precios:** los de la API directa de Anthropic están verificados en ADR-003 (1.1); el de **Bedrock no se encontró** y no se estima. **No se presenta ninguna cifra de coste de Bedrock ni de Lambda.** El escenario ilustrativo de ADR-003 (≈ 3,3 USD al mes con Sonnet 5.5 en la API directa y supuestos `[SUPUESTO]`) sigue siendo solo orden de magnitud.
- **Palancas de coste:** amplitud del período, número de hechos, longitud de las descripciones, reintentos, modelo y número de generaciones. El **tiempo de espera** de Lambda durante la llamada al modelo también se factura `[A VERIFICAR]`.
- **Límites propuestos (todos configurables, ADR-003 sección 10):** amplitud máxima del período; número máximo de hechos y de tokens de entrada y de salida por informe; generaciones simultáneas; presupuesto mensual con aviso. Al rebasar uno, se rechaza **antes** de llamar al proveedor con `INFORME_EXCEDE_LIMITES`.

### 6.10 Estrategia de pruebas sin llamadas reales a Bedrock

| Capa | Técnica | Qué prueba |
|---|---|---|
| Dominio (selección, agregaciones, autorización) | PostgreSQL real desechable (como en M4) | Visibilidad histórica, traslados, estado al corte, cifras, equivalencia con la vista de supervisión |
| Interfaz de generación | **Generador simulado** determinista con modos configurables: correcto, lento, fallo, salida mal formada, salida con una afirmación inventada, salida que obedece una orden del texto libre | Validación, `INFORME_NO_GENERADO`, límites, reintento, CA-166, CA-174, CA-175 |
| Función Lambda | Función Python pura, con el **cliente de Bedrock inyectado** y simulado (sin red ni credenciales) | Esquemas de entrada y salida, construcción del prompt, mapeo de errores |
| Contrato FastAPI ↔ Lambda | Ejemplos de referencia compartidos (archivos de contrato) usados por ambos lados | Que los dos extremos acuerdan el mismo esquema |
| Adaptador de FastAPI hacia Lambda | Cliente del SDK simulado | Tiempos, reintentos, traducción de errores |
| Garantía | Las pruebas fallan si intentan una conexión a internet; ninguna prueba necesita credenciales de AWS | — |
| Interfaz Flutter | Fakes del repositorio, como en M4-T7 y M4-T8 | Estados de carga, sin datos, límites, fallo, lectura sin edición ni copia |

Las llamadas reales a Bedrock quedan **exclusivamente** en M5-T7, condicionadas a D-M5-08, con datos ficticios.

## 7. Riesgos de privacidad, seguridad y costes

| Id | Riesgo | Nivel | Mitigación propuesta | Residual |
|---|---|---|---|---|
| R-M5-1 | Un informe expone datos de otro equipo o de otra persona | Alto | Política única de M1; filtrado al seleccionar; matriz de traslados de M4 aplicada a informes; prueba de equivalencia con la vista de supervisión | Bajo si se prueba |
| R-M5-2 | Inyección de instrucciones por el texto libre | Alto | Separación estructural, instrucción explícita, sin herramientas ni red, salida con esquema, validación, pruebas adversariales (CA-166) | Medio: no se elimina del todo |
| R-M5-3 | Retención de prompts y respuestas por el proveedor | Alto | Modo de retención verificado en la cuenta antes del primer envío; sin registro de invocaciones; sin caché (ADR-003, sección 5) | **Abierto (B4):** no se declara qué modos admite el modelo |
| R-M5-4 | Procesamiento fuera del país o de la región (perfiles entre regiones) | Alto | Elegir región y perfil con el marco legal; evitar el perfil global si hay restricciones | **Abierto (B3, B7)** |
| R-M5-5 | Datos personales en el texto libre pese a la seudonimización | Medio | Minimizar, excluir el resumen libre, informar (ADR-003, sección 11) | Medio |
| R-M5-6 | Afirmaciones sin respaldo y valoraciones de personas | Alto | Validación determinista de cifras, referencias y alias; instrucción; revisión de muestra (RNF-04); no hay garantía determinista del tono (H-M5-7) | Medio |
| R-M5-7 | Filtración por los registros técnicos o por los registros de Lambda | Medio | Sin contenido en ningún registro; prueba con cadena marcadora; registro de invocaciones desactivado | Bajo |
| R-M5-8 | Credenciales de AWS filtradas | Alto | Nunca en el repositorio ni en documentos; identidad con permiso mínimo; rotación; integración desactivada por defecto | Medio hasta decidir el despliegue |
| R-M5-9 | Abuso de coste: informes repetidos o masivos | Medio | Límites por petición, concurrencia máxima, presupuesto con aviso. No hay límite de tasa de lecturas en M1 a M4; **M5 es la primera operación con coste externo** | Medio |
| R-M5-10 | Canal de tiempos: el 404 y el 403 pueden diferir en latencia | Bajo | Riesgo residual conocido de M4 (RNF-13); no se sobrediseña | Bajo |
| R-M5-11 | Percepción de vigilancia o de evaluación de personas | Medio | Sin rankings ni valoraciones; orden alfabético; texto fijo de la base del informe | Medio (PA-09) |
| R-M5-12 | Dependencia nueva (SDK de AWS) y su cadena de suministro | Bajo | Aprobación expresa antes de añadirla; versión fijada; el adaptador es el único lugar que la importa | Bajo |
| R-M5-13 | Informes inconsistentes entre ejecuciones (el texto cambia, las cifras no) | Bajo | Cifras deterministas (CA-164); el texto puede variar y se documenta | Bajo |

## 8. Plan de tickets

Distribución propuesta `[PROPUESTO]`: ocho tickets pequeños. Respecto a la distribución de partida de BE-15, BE-16 y FE-10, se hacen estos cambios y por qué:

- **El núcleo determinista se divide en individual y consolidado**: el individual es la base (selección, alias, agregaciones) y el consolidado añade la pertenencia por fecha y la agregación por equipo, que concentra el riesgo de seguridad.
- **La interfaz de generación, la validación y el fallo se separan de la integración con AWS**: se desarrollan y prueban enteras con un generador simulado. Así **ningún ticket anterior a M5-T5 necesita AWS** y ninguno envía datos.
- **Los endpoints se entregan cuando el flujo está completo** (M5-T4): un contrato público con la narrativa nula sería un contrato incompleto.
- **La verificación en la cuenta y la evaluación previa son un ticket propio** (M5-T7), condicionado a una aprobación expresa, porque es lo único que toca AWS.

Metodología de pruebas en todos los tickets (la acordada desde M4): pruebas focalizadas de la lógica que importa y de los casos críticos de seguridad, con PostgreSQL real solo donde aporte valor; **sin mutaciones rutinarias**, sin suite completa por ticket (solo en el cierre de módulo o ante un cambio transversal de riesgo) y sin cientos de pruebas. Las cifras de pruebas son un orden de magnitud `[SUPUESTO]`. Cada ticket termina con informe y espera aprobación antes del siguiente.

Orden y dependencias:

```
Decisiones D-M5-01 a D-M5-09 (sección 9) y contrato 0.2
   │
M5-T1 núcleo determinista individual
   └─ M5-T2 núcleo determinista consolidado
        └─ M5-T3 interfaz de generación, seudonimización, validación y fallo (generador simulado)
             └─ M5-T4 endpoints M5-01 y M5-02
                  ├─ M5-T5 integración AWS: función Lambda y adaptador (sin recursos reales)
                  │       └─ M5-T7 verificación en la cuenta y evaluación previa (CONDICIONADO, aprobación expresa)
                  └─ M5-T6 Flutter: informes
M5-T8 cierre técnico de M5
```

### M5-T1 — Núcleo determinista del informe individual (servicio interno)

- **Estado:** **implementado y probado localmente el 2026-11-18; cierre en un único commit local.** Con las decisiones de la sección 12.1 ya incluye «actividades por estado al corte». Detalle en la sección 14.
- **Objetivo:** seleccionar los hechos autorizados de una persona y un período y calcular sus agregaciones, sin IA, sin HTTP y sin persistencia.
- **Contratos:** M5-01 (estructura de `hechos`, `bloqueos`, `agregaciones`, `sin_datos`); ADR-003, secciones 7 y 9. **Prerrequisito:** contrato 0.2 con el esquema campo por campo (H-M5-1) y D-M5-04 aprobadas.
- **Criterios (parte determinista):** CA-156, CA-157, CA-162, CA-164, CA-165, CA-167, CA-172, CA-173, CA-199, CA-201, CA-202, CA-224, CA-225, CA-226, CA-227, CA-234, CA-276.
- **Componentes previstos:** nuevo módulo `app/modulos/informes/` (un módulo por M1 a M5, ADR-001 D2) con repositorio, selección y agregaciones, apoyado en `app/compartido/visibilidad.py`, `pertenencias.py` y `modulos/bitacoras/secuencia.py`. Sin migración. **Sin modificar M1 a M4** (D-M5-09).
- **Dependencias:** M1-T1 (política), M4 (proyecciones de referencia).
- **Pruebas esenciales (~15):** la propietaria obtiene todos sus registros de ambos equipos; el supervisor del equipo anterior solo los de su equipo y nada posterior al traslado; el del equipo nuevo, sin detalles anteriores y con la referencia mínima y sin estado al corte ajeno; título neutral y sin motivos de bloqueo ajenos; actividad marcada por error excluida; planificación conservada excluida; período sin registros autorizados → `sin_datos`; un único registro; registros que existen pero no están autorizados → `sin_datos` (CA-202); agregaciones iguales en dos ejecuciones y coincidentes con un recuento manual; el bloqueo muestra el motivo; ningún registro de otra persona.
- **Condición de cierre:** criterios anteriores con evidencia; ninguna selección contiene datos no autorizados; sin llamadas a ningún generador; regresión focalizada de la política de visibilidad y de M4.

### M5-T2 — Núcleo determinista del informe consolidado (servicio interno)

- **Objetivo:** seleccionar los hechos autorizados de un equipo y un período, agruparlos por persona en orden alfabético y calcular las agregaciones del equipo.
- **Contratos:** M5-02; D-M5-03 aprobada.
- **Criterios (parte determinista):** CA-162, CA-163 (orden alfabético, sin ranking), CA-164, CA-167, CA-172, CA-173, CA-199 a CA-202, CA-228, CA-229, CA-235, CA-277, CA-19 y CA-20 (parte de informes).
- **Componentes previstos:** ampliación del módulo `informes`.
- **Dependencias:** M5-T1.
- **Pruebas esenciales (~12):** traslado T→U con los dos supervisores; personas trasladadas solo en las fechas del equipo; estado al corte omitido si lo determina otro equipo y contado aparte; título original ausente; equipo sin registros; **equivalencia de recuentos por estado con la vista de supervisión (M4-03)** para el mismo período; orden alfabético estable; las agregaciones del equipo suman las de las personas.
- **Condición de cierre:** como M5-T1 más la prueba de equivalencia con M4-03.

### M5-T3 — Interfaz de generación, seudonimización, validación y fallo (con generador simulado)

- **Objetivo:** dotar al dominio de una interfaz de generación independiente del proveedor, con seudonimización, validación determinista de la salida, límites previos y fallo explícito. **Sin AWS.**
- **Contratos:** contrato interno (sección 6.4, documento nuevo `m5-integracion-ia.md`); ADR-003, secciones 6, 8, 9, 10, 12 y 14; D-M5-01, D-M5-05, D-M5-06, D-M5-07.
- **Criterios:** CA-161, CA-163 (en lo verificable), CA-166, CA-174, CA-175, CA-200, CA-05 (informes), CA-159 (sin persistencia).
- **Componentes previstos:** protocolo `GeneradorDeTexto`; adaptador `ninguno` (desactivado por defecto) y adaptador simulado; seudonimización con tabla en memoria; constructor del cuerpo de lista cerrada; validador de la salida; parámetros de límites y tiempos en `app/config.py`; códigos `INFORME_EXCEDE_LIMITES` e `INFORME_NO_GENERADO`. Migración solo si D-M5-07 la exige.
- **Dependencias:** M5-T2.
- **Pruebas esenciales (~18):** cada modo del generador simulado (correcto, lento, fallo, mal formado, afirmación inventada, cifra alterada, alias desconocido, orden del texto libre obedecida); un reintento como máximo; plazo global; límites rechazados **antes** de generar; sin contenido parcial; el cuerpo enviado no contiene identificadores, correos, nombres reales ni credenciales (prueba de lista cerrada); el resumen libre no sale; cadena marcadora ausente de los registros; el texto libre llega delimitado y no concatenado.
- **Condición de cierre:** ninguna salida inválida llega a un cliente; sin red ni credenciales en las pruebas; contrato interno documentado.

### M5-T4 — Endpoints M5-01 y M5-02

- **Objetivo:** exponer los dos contratos con autorización, errores y ausencia de persistencia, usando el generador simulado.
- **Contratos:** M5-01 y M5-02 (versión 0.2); D-M5-02.
- **Criterios:** CA-152 a CA-155, CA-158 a CA-160, CA-168 a CA-171, CA-154, CA-169, CA-170, CA-02, CA-19 y CA-20 (informes), y el resto de los 38 de extremo a extremo.
- **Componentes previstos:** router y esquemas del módulo `informes`; registro en `main.py`; sin identificador ni recurso de consulta del informe.
- **Dependencias:** M5-T3.
- **Pruebas esenciales (~15):** roles (propietaria, supervisor, compañero, colaborador, supervisor ajeno); `NO_IDENTIFICADA`, `ACCESO_DESACTIVADO`, `SIN_PERTENENCIA_VIGENTE`; formato antes que recurso; persona o equipo inexistente y no autorizado indistinguibles; `INFORME_EXCEDE_LIMITES` y `INFORME_NO_GENERADO`; ningún método ni ruta para recuperar un informe; generar de nuevo produce una fecha nueva; la base de datos no cambia.
- **Condición de cierre:** criterios con evidencia HTTP real (uvicorn y PostgreSQL desechable); respuestas sin datos protegidos; regresión focalizada.

### M5-T5 — Integración AWS: función Lambda y adaptador (sin recursos reales)

- **Objetivo:** escribir en el repositorio la función Lambda (adaptador por proveedor) y el adaptador de FastAPI que la invoca, probados con simulacros. **No crea recursos AWS, no usa credenciales y no envía datos.**
- **Contratos:** contrato interno; ADR-003, secciones 8 y 14; D-M5-01 aprobada; aprobación de la dependencia del SDK.
- **Criterios:** CA-166, CA-174, CA-175 en el adaptador real; «cambiar de adaptador no modifica el contrato público» (BE-16).
- **Componentes previstos:** `integracion_ia/lambda/` (función pura con cliente inyectable) y adaptador `aws` en el módulo `informes`; configuración con la integración desactivada por defecto.
- **Dependencias:** M5-T4.
- **Pruebas esenciales (~12):** esquemas de entrada y salida; prompt con datos delimitados; errores traducidos; tiempos y reintentos del adaptador; archivos de contrato compartidos entre los dos extremos; sin credenciales en el repositorio; sin red en las pruebas.
- **Condición de cierre:** el adaptador `aws` es intercambiable con el simulado sin tocar el contrato público; ningún recurso real creado.

### M5-T6 — Flutter: informes (FE-10)

- **Objetivo:** solicitar y leer informes en pantalla, sin edición ni copia.
- **Contratos:** M5-01 y M5-02.
- **Criterios:** CA-158, CA-159, CA-162, CA-172, CA-173, CA-174, CA-175 en la interfaz.
- **Componentes previstos:** nueva feature `frontend/lib/features/informes/` (dominio, datos, presentación) con la misma estructura que `supervision` y `team`: Riverpod con generador, análisis explícito del JSON, estado solo en memoria, textos fijos de error, orden de estados `isLoading`/`hasError` antes del valor previo e invalidación del proveedor en cada consulta (defecto corregido en M4-T9). Formulario de período; el supervisor elige entre sí mismo y los integrantes actuales (M4-05); presentación diferenciada de hechos, cifras y narrativa; mensajes de «sin datos», de límites y de «el informe no pudo generarse».
- **Dependencias:** M5-T4 y las decisiones D-M5-04 y D-M5-03 (forma de la respuesta).
- **Pruebas esenciales (~12):** estados de carga, sin datos, límites y fallo sin contenido parcial; el informe no se conserva al salir; la pérdida de autorización en plena sesión no deja datos anteriores a la vista; el colaborador no ve la opción del consolidado; sin controles de edición; textos visibles solo como texto plano.
- **Condición de cierre:** análisis estático sin incidencias; criterios de interfaz con evidencia; recorrido real en Chrome con el generador simulado.

### M5-T7 — Verificación en la cuenta AWS y evaluación previa (CONDICIONADO)

- **Objetivo:** cumplir la evaluación previa de ADR-003 (sección 13) y verificar en la cuenta real la disponibilidad del modelo, el modo de retención, la región efectiva y la ausencia de rastro. **Es el único ticket que toca AWS y exige aprobación expresa** (D-M5-08); no se ejecuta ni se prepara su infraestructura antes.
- **Contenido propuesto:** conjunto de referencia en español con registros **ficticios** (jornadas de distinto tamaño, registros parciales, vacíos, bloqueos, actividades heredadas, textos con instrucciones maliciosas); comparación de Sonnet 5.5 y Haiku 5.5 con el mismo conjunto; medición de tokens, latencia y coste con precios verificados; consulta del modo de retención admitido y llamada de prueba con cadena marcadora; criterios y escala de calidad definidos antes de evaluar; revisión por una persona hispanohablante ajena al desarrollo.
- **Condiciones de cierre:** decisiones B1 a B4, B7 y B10 resueltas por escrito; informe con resultados reales. **Si el modelo no admite el modo de retención exigido, el resultado es no usar el servicio externo** (ADR-003, sección 4), no una excepción.
- **Pruebas:** las de la evaluación; no se añaden pruebas automáticas que dependan de AWS.

### M5-T8 — Cierre técnico de M5

- **Objetivo:** cierre del módulo con la misma disciplina que M4-T9.
- **Contenido:** matriz de trazabilidad de los 38 criterios (más CA-02, CA-05, CA-19 y CA-20 en su parte de informes) con evidencia de backend, Flutter e integración; regresión completa única de backend y Flutter; recorrido integral real (FastAPI, Flutter Web en Chrome y PostgreSQL desechable) con el generador simulado y, solo si se aprobó M5-T7, con el real; revisión básica proporcionada de accesibilidad y experiencia; confirmación de migraciones, rendimiento y seguridad; actualización de los documentos afectados; recomendación de consolidación en Git.
- **Condición de cierre:** ningún criterio declarado cumplido sin evidencia; los parciales (CA-19, CA-20, CA-05) se actualizan según lo ejecutado. M5 no se declara cerrado sin M5-T7 si se pretende el uso real de IA.

## 9. Decisiones para aprobación

Solo las que deben resolverse **antes de programar**. Cada una indica el ticket al que bloquea. **Ninguna alternativa se implementa sin aprobación.**

### D-M5-01 — Topología de la integración con AWS y dependencia del SDK

- **Problema:** cómo se comunican FastAPI, Lambda y Bedrock (sección 6.2) y si se añade el SDK de AWS al backend.
- **Alternativas:** (A) FastAPI invoca Lambda de forma síncrona con el SDK de AWS; (B) FastAPI llama a Bedrock directamente; (C) Lambda detrás de una URL o API Gateway; (D) Lambda asíncrona con cola.
- **Ventajas y riesgos:** ver sección 6.2. B contradice la decisión confirmada; C añade superficie pública sin necesidad contractual; D exige persistir resultados y contradice RN-56.
- **Recomendación:** **A.** Aprobar también la dependencia del SDK oficial de AWS (versión fijada, importada solo por el adaptador), porque implementar la firma de las peticiones a mano sería más arriesgado. No aprobar API Gateway, S3, SQS ni ningún otro servicio.
- **Afecta:** M5-T3 (contrato interno), M5-T5.

### D-M5-02 — Código de respuesta ante el informe individual de una persona visible que no es la propietaria

- **Problema:** H-M5-3. Un compañero del mismo equipo ve los registros de la persona, pero no puede generar su informe.
- **Alternativas:** (1) 403 `OPERACION_NO_PERMITIDA` cuando la persona solicitada es visible para quien llama (consecuente con las convenciones 3.1 y con M4-T6) y 404 indistinguible en los demás casos; (2) 404 `RECURSO_NO_DISPONIBLE` siempre, como indica el contrato.
- **Ventajas y riesgos:** (1) coherente con M2 a M4 y más útil para la persona usuaria; añade `OPERACION_NO_PERMITIDA` a M5-01. (2) sigue el contrato literal y oculta mejor la existencia; ofrece una respuesta distinta a la del resto de la API ante casos equivalentes.
- **Recomendación:** **(1)**. Es la regla ya aprobada y aplicada en M4; el contrato se corrige a 0.2.
- **Afecta:** M5-T4.

### D-M5-03 — Forma de la narrativa del informe consolidado

- **Problema:** H-M5-2. Una narrativa única mezcla a todas las personas; una por persona cambia el esquema.
- **Alternativas:** (A) una sola llamada para todo el equipo y una narrativa única; (B) **una narrativa por persona** (llamadas independientes con concurrencia acotada) y una sección de equipo **determinista** (cifras y bloqueos, sin IA); (C) B más una narrativa de equipo generada solo a partir de las agregaciones.
- **Ventajas y riesgos:** (A) una llamada, pero una entrada grande, más latencia y más riesgo de comparar personas (RF-47). (B) cada petición es acotada y aísla el contexto de cada persona; más llamadas y más coste; si una falla, todo el informe falla (RN-58). (C) añade una llamada sin hechos de personas.
- **Recomendación:** **B.** Es la forma que mejor protege RF-47, acota la latencia y encaja con el orden alfabético por persona del contrato. Exige corregir el esquema de M5-02 (0.2) y no cambia ningún requisito.
- **Afecta:** M5-T2, M5-T3, M5-T6.

### D-M5-04 — Catálogo de agregaciones (P-M5-1) y esquema de la respuesta

- **Problema:** H-M5-1 y H-M5-6. El catálogo propuesto no está aprobado y el esquema no tiene campos.
- **Alternativas:** (A) aprobar el catálogo propuesto en el contrato: número de avances; jornadas con registros; actividades con registros; actividades por estado al corte (con «sin estado al corte» contadas aparte, como en M4-03); planificadas y no planificadas; actividades bloqueadas; (B) un catálogo menor; (C) otro catálogo.
- **Ventajas y riesgos:** todos son recuentos deterministas y sin porcentajes (RN-57). Añadir más aumenta el riesgo de ser interpretado como una evaluación.
- **Recomendación:** **A**, más que, una vez aprobada, se **redacte el contrato 0.2** con el esquema campo por campo y se revise **antes** de M5-T1.
- **Afecta:** M5-T1, M5-T2, M5-T6.

### D-M5-05 — Alcance de la validación de la salida y riesgo residual aceptado

- **Problema:** H-M5-7. No existe un control determinista de «sin valoraciones» (CA-163) ni de nombres propios no previstos.
- **Alternativas:** (A) validación determinista de esquema, referencias, cifras, alias y fechas, más heurística de entidades, más instrucción y revisión de muestra para el tono; (B) además, un segundo modelo que audite la salida; (C) condicionar el informe a la revisión humana previa.
- **Ventajas y riesgos:** (A) proporcionada y sin coste extra, con un riesgo residual explícito. (B) duplica coste y latencia y añade un segundo envío de datos (RNF-06). (C) contradice el objetivo de ahorrar trabajo manual.
- **Recomendación:** **A**, documentando el riesgo residual en la matriz de cierre y verificando CA-163 y RNF-04 por muestra.
- **Afecta:** M5-T3, M5-T7, M5-T8.

### D-M5-06 — Parámetros y valores iniciales de límites, tiempos y concurrencia (B8, B9, PA-13)

- **Problema:** H-M5-5. Los parámetros no existen y sus valores no están decididos.
- **Alternativas:** (A) aprobar los **nombres, las unidades y los comportamientos** y fijar valores iniciales conservadores, medidos después con datos realistas; (B) esperar a decidir todos los valores.
- **Parámetros propuestos:** `INFORME_MAX_RANGE_DAYS` (días; el máximo de M4 es 92, un informe puede ser menor); `INFORME_MAX_HECHOS`; `INFORME_MAX_TOKENS_ENTRADA`; `INFORME_MAX_TOKENS_SALIDA`; `INFORME_PLAZO_TOTAL_SEGUNDOS`; `INFORME_REINTENTOS_VALIDACION` (máximo 1 por ADR-003); `INFORME_CONCURRENCIA_MAXIMA`; `INFORME_HABILITADO` (desactivado por defecto).
- **Ventajas y riesgos:** (A) permite programar y medir; los valores son un supuesto `[SUPUESTO]` que no debe tomarse como regla del producto. (B) bloquea M5-T3.
- **Recomendación:** **A**, con los valores iniciales propuestos al arrancar M5-T3 y revisados en M5-T7 con mediciones reales.
- **Afecta:** M5-T3, M5-T4.

### D-M5-07 — Registro técnico de consumo (P-M5-2)

- **Problema:** H-M5-8. Controlar el consumo por equipo y día exigiría guardar contadores.
- **Alternativas:** (A) **sin tabla nueva**: registro técnico estructurado sin contenido, límites por petición, concurrencia global y presupuesto vigilado en el proveedor; (B) tabla de contadores por equipo y día, con migración; (C) ambos.
- **Ventajas y riesgos:** (A) no añade esquema ni conserva datos de personas; no limita por equipo y día. (B) límite fino, pero añade una migración y un almacén que M5 no necesita para cumplir sus criterios (RN-56).
- **Recomendación:** **A** en el MVP; revisar (B) si la medición de M5-T7 lo justifica, mediante una decisión nueva. Sin identificadores de persona en el registro.
- **Afecta:** M5-T3.

### D-M5-08 — Condiciones para el primer envío real de datos a Bedrock (RNF-06, B1 a B4, B7, B10)

- **Problema:** RNF-06 y PP-33 siguen `[PROPUESTO]`; modelo, región, retención y marco legal están abiertos. Ninguna llamada real está autorizada.
- **Alternativas:** (A) aprobar RNF-06 como **condición de habilitación**: ningún dato sale hasta resolver por escrito el modelo, la región o el perfil, el modo de retención verificado en la cuenta, el marco legal y la evaluación previa, con la integración desactivada por defecto; (B) aprobar el envío con datos ficticios para la evaluación, y real solo con los datos de los cuatro puntos; (C) otra condición.
- **Ventajas y riesgos:** (A) es la lectura más segura y consecuente con CLAUDE.md, sección 6. (B) permite evaluar sin datos reales (M5-T7 ya usa registros ficticios).
- **Recomendación:** **A + B**: la evaluación usa solo datos ficticios; los datos reales solo se envían tras resolver los cuatro puntos. Elegir el modelo y la región **con los resultados de la evaluación**, no antes.
- **Afecta:** M5-T5, M5-T7, M5-T8.

### D-M5-09 — Reutilización de la lógica de M4 sin modificar módulos cerrados

- **Problema:** H-M5-10. El cálculo de inclusión y de estado al corte está en funciones privadas de `supervision.py`.
- **Alternativas:** (A) M5 construye sus propias consultas con los **mismos predicados de la política de M1**, sin importar internos de M4, y se garantiza la equivalencia con una prueba contra M4-03; (B) extraer funciones comunes de `supervision.py` a `compartido/` (modifica un módulo cerrado); (C) consumir M4-03 como servicio interno (devuelve actividades sin descripciones de avances y está paginado).
- **Ventajas y riesgos:** (A) no toca M1 a M4, pero repite parte de la composición de consultas, que se vigila con la prueba de equivalencia. (B) evita repetir, pero cambia un módulo cerrado: requeriría aprobación como en D-M4-01. (C) no sirve: faltan datos y hay paginación.
- **Recomendación:** **A.** Si M5-T1 demuestra que repetir es peor, se propone (B) como cambio puntual y se pide aprobación.
- **Afecta:** M5-T1, M5-T2.

### Decisiones que **no** hace falta resolver antes de programar

Modelo y región (se deciden con M5-T7), marco legal (B7), valores definitivos de los límites, despliegue y cómo se obtiene la identidad de AWS, PP-11 (no se implementa), configuración de AWS Budgets y de CloudTrail (se tratan al crear recursos reales), y el selector de personas que ya no integran el equipo (sección 10, mejora no bloqueante).

## 10. Supuestos y limitaciones de esta planificación

- `[SUPUESTO]` La narrativa y la interfaz están en **español** (PA-13 deja abierto el idioma de la interfaz). Se confirma al aprobar D-M5-04.
- `[SUPUESTO]` Los límites técnicos de Lambda y de Bedrock (cargas, tiempos, cuotas, facturación del tiempo de espera, parámetros admitidos por el modelo) no se han verificado en esta fase; se comprueban en la cuenta (M5-T7).
- Los precios de Bedrock siguen sin encontrarse (ADR-003, 1.1): no se estima ningún coste de Bedrock ni de Lambda.
- No se ejecutó ninguna llamada a ningún servicio externo, no se abrió ninguna cuenta y no se creó ningún recurso.
- Las cifras de pruebas de cada ticket son un orden de magnitud `[SUPUESTO]`.
- **Limitación propuesta para M5-T6 (H-M5-11):** la pantalla ofrece a la propia persona y, al supervisor, a los integrantes actuales del equipo (M4-05). El informe de una persona que ya no integra el equipo está soportado por el backend (RN-53), pero la pantalla no permite elegirla, igual que ocurre en M4. Es una mejora no bloqueante `[ABIERTO]`.

## 11. Estado de este documento y de Git

- Este documento nació como el entregable de M5-T0 y se amplía con las secciones 12 a 14 (resoluciones de la persona responsable, extracción de D-M5-04 y D-M5-06 y registro de M5-T1).
- Del resto de la documentación solo se añadió el borrador del contrato M5-01 0.2 (`docs/api/m5-01-borrador-0.2.md`); no se modificó ningún contrato vigente, ADR, criterio ni matriz.
- M5-T1 se consolida en un único commit local (sin push). Los cambios de M5-T2 quedan sin confirmar.
- M5-T3 a M5-T8 no se inician sin aprobación.

## 12. Resoluciones de la persona responsable tras M5-T0 (2026-11-18)

Se registran tal como se comunicaron. Las marcas «pendiente» **no** se convierten en confirmadas.

| Id | Resolución | Estado |
|---|---|---|
| D-M5-01 | Arquitectura **futura** FastAPI → Lambda síncrona → Amazon Bedrock, utilizando el SDK oficial. Sigue sin aprobarse cualquier servicio adicional (API Gateway, S3, SQS u otro). Se implementa en M5-T5 y se verifica en M5-T7; **nada se configura ni se llama en M5-T1** | **Aprobada** |
| D-M5-02 | 403 para recursos visibles cuando la operación no está permitida; 404 para inexistentes o no visibles, conforme a las convenciones | **Aprobada** (M5-T1 la aplica; la definición de «visible» para una persona es la pregunta P-9 del borrador del contrato) |
| D-M5-03 | Narrativa por persona y sección determinista de equipo, respetando los contratos y sin rankings | **Aprobada en principio** (se concreta en M5-T2 y M5-T3; no afecta a M5-T1) |
| D-M5-04 | Catálogo de agregaciones, definiciones y fórmulas | **Pendiente de detalle** (extracción en 13.1) |
| D-M5-05 | Validación determinista más evaluación por muestras para detectar afirmaciones sin sustento y valoraciones no permitidas | **Aprobada** |
| D-M5-06 | Nombres y valores de límites, tiempos y concurrencia | **Pendiente de detalle** (extracción en 13.2) |
| D-M5-07 | Sin tabla nueva de consumo en el MVP | **Aprobada** |
| D-M5-08 | Primera evaluación real con datos ficticios; el uso de datos reales queda condicionado a resolver modelo, región, retención y marco de privacidad | **Aprobada** |
| D-M5-09 | Reutilizar la política histórica y los predicados existentes sin crear una segunda política de autorización | **Aprobada** |

Bedrock y Lambda figuran **únicamente** como dependencias futuras de M5-T5 y M5-T7. No hay en el código ni en la configuración ninguna referencia a AWS.

### 12.1 Decisiones de la persona responsable sobre M5-T1 (2026-11-18, segunda comunicación)

Aprobación **parcial** de M5-T1 y definiciones para cerrarlo. Estas definiciones se aplican a M5-T1; **el catálogo formal de D-M5-04 sigue pendiente de aprobación** y D-M5-06 sigue pendiente de valores.

| Elemento | Decisión |
|---|---|
| `avances` | Cantidad de avances autorizados en el período |
| `jornadas_con_registros` | Fechas laborales distintas con avances autorizados |
| `actividades_con_registros` | Actividades distintas con avances autorizados |
| `actividades_por_origen` | Grupos planificadas, no planificadas y `origen_no_disponible`. No se infiere un origen protegido |
| `actividades_con_bloqueo` | Actividades con algún avance autorizado en estado Bloqueada durante el período |
| `actividades_por_estado_al_corte` | Solo actividades con avances autorizados en el período; estado al corte según la secuencia y la política autorizada, sin sustituir estados protegidos por estados anteriores; grupo `estado_no_disponible` si el estado no puede exponerse. **No** se importa la población de actividades pendientes de M4-03 |
| Planificación sin avances | No cuenta como registro para las métricas basadas en avances (resuelve P-1) |
| P-9 | **Corrección obligatoria:** no se aprueba «perteneció alguna vez al equipo vigente». Se usa la visibilidad efectiva sobre la persona y el período; si no puede demostrarse, 404 uniforme |
| P-3, P-5, P-6, P-8 | Siguen **abiertas**; sus definiciones exactas están en el borrador del contrato (sección 6.2) |
| D-M5-06 | Sigue pendiente de valores; no se implementa ningún límite numérico |

## 13. Extracción de D-M5-04 y D-M5-06

### 13.1 D-M5-04 — catálogo de agregaciones

Fuente: contrato 0.1 (`m5-informes.md`, «Catálogo propuesto de agregaciones»), ADR-003 (sección 9) y este plan (D-M5-04). El catálogo formal **sigue sin aprobar**, pero **las seis definiciones se decidieron el 2026-11-18 (sección 12.1) para M5-T1** y están implementadas en `app/modulos/informes/agregaciones.py`, sin ninguna ruta.

Reglas que ya están confirmadas y acotan cualquier agregación: son recuentos y no porcentajes (RN-57), se calculan de forma determinista sobre registros autorizados (RF-51, RN-29), se distinguen de los hechos (RF-46, RN-26), no cuentan actividades marcadas por error (CA-167), no contienen valoraciones ni rankings (RF-47) y con los mismos registros dan siempre el mismo valor (CA-164).

| # | Campo | Definición propuesta | Fórmula | Valor | Requisito que lo fundamenta | Decisión todavía necesaria | M5-T1 |
|---|---|---|---|---|---|---|---|
| 1 | `avances` | Cantidad de avances autorizados en el período | número de hechos | entero ≥ 0 | RF-51, RN-29; catálogo P-M5-1 | Aprobación formal del catálogo | Implementado (decisión del 2026-11-18) |
| 2 | `jornadas_con_registros` | Fechas laborales distintas con avances autorizados | fechas laborales distintas entre los hechos | entero ≥ 0 | Ídem | Ídem | Implementado (decisión del 2026-11-18) |
| 3 | `actividades_con_registros` | Actividades distintas con avances autorizados | actividades distintas entre los hechos | entero ≥ 0 | Ídem | Ídem | Implementado (decisión del 2026-11-18) |
| 4 | `actividades_por_origen` | `planificadas`, `no_planificadas` y `origen_no_disponible` (las de forma neutral; no se infiere un origen protegido) | sobre las actividades de la fila 3, según su origen autorizado | tres enteros ≥ 0 | Catálogo; RN-101 | Aprobación formal del catálogo | Implementado (decisión del 2026-11-18) |
| 5 | `actividades_con_bloqueo` | Actividades con algún avance autorizado en estado Bloqueada durante el período (no «bloqueada al corte») | actividades distintas con al menos un hecho Bloqueada | entero ≥ 0 | Catálogo; RF-74 | Aprobación formal del catálogo | Implementado (decisión del 2026-11-18) |
| 6 | `actividades_por_estado_al_corte` | Solo actividades con avances autorizados en el período; estado del último avance hasta el corte (el corte es `hasta`) si está autorizado; grupos `pendiente`, `en_progreso`, `bloqueada`, `completada` y `estado_no_disponible` | Sobre la población de la fila 3: estado del último avance con fecha laboral ≤ `hasta` según la secuencia válida completa; no autorizado → `estado_no_disponible`, sin sustituirlo por un avance anterior. Los cinco grupos suman la fila 3 | cinco enteros ≥ 0 | Catálogo; RN-88, RA-07; RF-70 | Aprobación formal del catálogo | Implementado (decisión del 2026-11-18) |

### 13.2 D-M5-06 — límites, tiempos y concurrencia

Fuente: contrato 0.1 (`INFORME_EXCEDE_LIMITES`, `INFORME_NO_GENERADO`), `convenciones.md` sección 9, ADR-003 (secciones 9, 10 y 12) y D-M5-06 de este plan. **El plan no propuso ningún valor numérico** y esta extracción **no inventa ninguno**: la columna «Valor» recoge solo lo que figura en una fuente y se marca como referencia. **Ningún parámetro se implementó en M5-T1** (el núcleo no aplica límites; los aplica M5-T3).

| Parámetro (nombre propuesto en el plan) | Definición | Unidad | Valor inicial propuesto | Referencia en las fuentes | Decisión todavía necesaria |
|---|---|---|---|---|---|
| `INFORME_MAX_RANGE_DAYS` | Amplitud máxima del período, con los extremos incluidos. Al rebasarla: `INFORME_EXCEDE_LIMITES` antes de generar | días | **Ninguno propuesto** | `QUERY_MAX_RANGE_DAYS` de M4 vale 92 (D-M4-03, confirmado **solo** para M4-02 y M4-03; no se traslada a M5) | Valor |
| `INFORME_MAX_HECHOS` | Número máximo de avances autorizados de un informe | número | **Ninguno propuesto** | Dimensionado de ADR-003: 22 jornadas × 4 avances = 88 avances por persona y mes (`[SUPUESTO]` del ADR, no dato del producto) | Valor |
| `INFORME_MAX_TOKENS_ENTRADA` | Máximo de tokens de entrada por informe | tokens | **Ninguno propuesto** | ADR-003, sección 10; depende del modelo y de cómo se cuentan los tokens (M5-T3 y M5-T7) | Valor |
| `INFORME_MAX_TOKENS_SALIDA` | Máximo de tokens de salida | tokens | **Ninguno propuesto** | ADR-003, sección 10 | Valor |
| `INFORME_PLAZO_TOTAL_SEGUNDOS` | Plazo global que engloba la invocación, la generación y el reintento; al agotarse, `INFORME_NO_GENERADO` | segundos | **Ninguno propuesto** | ADR-003, sección 12. Los límites técnicos de Lambda y de Bedrock **no están verificados** | Valor |
| `INFORME_REINTENTOS_VALIDACION` | Reintentos de generación cuando la salida no supera la validación | número | «Como máximo un reintento» (ADR-003, sección 9, **propuesto**, no aprobado como número) | ADR-003, secciones 9 y 12 | Confirmar el valor |
| `INFORME_CONCURRENCIA_MAXIMA` | Generaciones simultáneas | número | **Ninguno propuesto** | ADR-003, sección 10 | Valor |
| `INFORME_HABILITADO` | Interruptor de la integración con el generador | booleano | Desactivado por defecto (consecuencia de RNF-06 y D-M5-08, no una cifra) | D-M5-08 | Confirmar el nombre |

**No aplicables en el MVP tras D-M5-07 (sin tabla nueva de consumo):** los límites «generaciones por equipo y día» y «presupuesto mensual con aviso y rechazo» que menciona ADR-003 (sección 10) exigen contadores persistentes. No se implementan.

## 14. M5-T1 — registro de la implementación

### 14.1 Estado

**Implementado y probado localmente; consolidado en un único commit local.** Servicio **interno**: no hay ruta, no se registra en `main.py`, no llama a ningún generador, no usa AWS, no persiste nada y no envía datos fuera del proceso. No se tocó Flutter. M5-T2 a M5-T8 no se iniciaron.

### 14.2 Archivos

| Archivo | Cambio |
|---|---|
| `backend/app/modulos/informes/__init__.py` | Módulo nuevo (un módulo por M1 a M5, ADR-001 D2) |
| `backend/app/modulos/informes/individual.py` | Servicio `preparar_informe_individual`, estructura de campos cerrados (`InformeBase`, `Persona`, `ActividadDelInforme`, `Hecho`, `Bloqueo`) y reglas de autorización |
| `backend/app/modulos/informes/repositorio.py` | Una consulta de avances con `condicion_lectura` aplicada al seleccionar, y la lectura del nombre de la persona |
| `backend/app/modulos/informes/agregaciones.py` | Las cinco agregaciones propuestas (13.1) |
| `backend/app/compartido/visibilidad.py` | **Un cambio en un componente compartido:** se añade `persona_es_visible(persona, desde, hasta)` (solo elige 403 o 404; no concede la lectura de ningún registro). Corregida tras la revisión (P-9): visibilidad **en el período** |
| `backend/app/compartido/pertenencias.py` | Se añade `solapa` (intervalo de pertenencia que comparte una fecha con un período), junto a `cubre`: sigue habiendo una sola definición del intervalo |
| `backend/tests/test_informe_individual.py` | 16 pruebas nuevas |
| `backend/tests/test_visibilidad_historica.py` | Se actualiza a propósito la lista cerrada de módulos que usan la política (como en M4-T1 y M4-T6): se añaden `informes/individual.py` e `informes/repositorio.py` |
| `docs/api/m5-01-borrador-0.2.md` | Borrador del contrato M5-01 0.2 (nuevo) |
| `docs/backlog/tickets/m5-plan-implementacion.md` | Este documento |

### 14.3 Datos seleccionados y excluidos

**Se selecciona** (solo avances, autorizados uno a uno en la propia consulta): fecha laboral, estado histórico, descripción y motivo de bloqueo de cada avance del período; para el estado al corte, el último avance de cada actividad hasta el corte con su autorización decidida en SQL (el estado de uno protegido sale nulo de la base); de cada actividad referenciada, su título y su origen **solo si** quien consulta está autorizado sobre su jornada de origen, o la referencia neutral en caso contrario; el nombre y el identificador de la persona del informe.

**Se excluye por construcción:** actividades marcadas por error; planificaciones (conservadas o no: la consulta no lee la tabla); resumen libre de la bitácora; título, origen, descripciones y motivos de bloqueo de otro equipo; correo, identificador de acceso, hash de contraseña, sesiones y cualquier dato de identidad; nombres de equipos y auditoría. La estructura tiene una **lista cerrada de campos** y una prueba que comprueba que solo contiene esos.

**Texto no confiable:** `descripcion`, `motivo_bloqueo` y el título se conservan tal cual y se tratan como dato; `CAMPOS_DE_TEXTO_LIBRE` los lista para que M5-T3 los entregue delimitados.

**Seudonimización posterior (M5-T3, antes de cualquier envío a Bedrock):** sustituir la persona por un alias con tabla solo en memoria; sustituir el identificador de cada actividad por su referencia opaca; construir lo enviado con una función de lista cerrada (`CAMPOS_PARA_EL_GENERADOR`), nunca serializando esta estructura; no enviar el nombre ni ningún identificador. Las referencias de los hechos (`h1`, `h2`…) ya son opacas y no son identificadores de la base de datos.

### 14.4 Reglas de autorización aplicadas

Orden (convenciones 3.2): 1) puede operar (`ACCESO_DESACTIVADO`, `SIN_PERTENENCIA_VIGENTE`); 2) formato (`desde` no posterior a `hasta`); 3) la persona: la propia, o una persona **visible en el período pedido** a la que solo el supervisor vigente con acceso efectivo genera el informe (compañero visible: `OPERACION_NO_PERMITIDA`; inexistente o sin visibilidad demostrable en el período: `RECURSO_NO_DISPONIBLE` indistinguible); 4) solo los avances que `condicion_lectura` permite (propietaria: todos, de ambos equipos; supervisor: los de las fechas en que la persona era de su equipo). Es la política de M1 sin ninguna regla de equipo nueva; la única función añadida, `persona_es_visible`, es la regla de equipo elevada de «una fecha» a «alguna fecha del período», y una prueba de equivalencia la contrasta con `decidir_lectura` para todas las combinaciones de consultante, persona y período del escenario. **Corrección de P-9:** la primera versión usaba «perteneció alguna vez al equipo vigente», que revela relaciones históricas ajenas al período; ya no se usa.

### 14.5 Pruebas y evidencia de PostgreSQL

- Base **desechable**: `smartwork_test` del clúster de pruebas del puerto 55432. No se tocó `smartwork_app` ni el PostgreSQL local del puerto 5432. La consulta del informe usa el rol de la aplicación (solo `SELECT`).
- `tests/test_informe_individual.py`: **16 superadas**.
- Regresión focalizada de los componentes compartidos afectados tras la corrección (`test_visibilidad_historica.py`, `test_consulta_bitacora.py` y el archivo nuevo): **76 superadas**. (Antes de la corrección, la regresión más amplia con `test_consulta_supervision.py` y `test_consulta_extensiones_m2_m3.py` dio 107 superadas.)
- No se ejecutó la suite completa ni mutaciones. No hay un analizador estático configurado en el backend.

| Prueba | Qué comprueba |
|---|---|
| `el_informe_propio_trae_los_hechos…` | Informe propio con recuento manual de las cinco agregaciones, orden de la secuencia, bloqueo con motivo y resultado idéntico en dos ejecuciones |
| `el_periodo_acota_la_seleccion…` | El período acota (con su estado al corte); un período con solo una planificación futura es `sin_datos` |
| `el_supervisor_obtiene_el_informe…` | Informe de una persona del equipo y el propio |
| `un_companero_que_no_supervisa_recibe_403…` | 403 para compañero visible; 404 indistinguible (código, estado, mensaje y detalles iguales) para inexistente, otro equipo y otra organización |
| `sin_acceso_o_sin_pertenencia_vigente…` | Acceso desactivado y sin pertenencia vigente, también para lo propio |
| `el_formato_se_valida_antes_que_la_persona` | `SOLICITUD_INVALIDA` idéntico con cualquier persona |
| `el_supervisor_del_equipo_anterior…` | Solo lo de su equipo y nada posterior al traslado |
| `el_supervisor_del_equipo_nuevo…` | Actividad neutral sin título, sin motivo reservado, sin detalles ni nombre del equipo anterior y sin estado al corte |
| `la_propietaria_trasladada…` | Todos sus registros de ambos equipos con títulos completos |
| `las_actividades_marcadas_por_error_y_las_planificaciones_conservadas…` | Exclusión de ambas, también en el informe propio |
| `la_estructura_solo_tiene_los_campos_cerrados…` | Claves cerradas; ni identificador de acceso, ni contraseña, ni hash, ni nombre de equipo ni resumen |
| `el_texto_libre_se_conserva_como_dato…` | Una orden dentro de una descripción se conserva como dato y no altera selección ni cifras |
| `la_referencia_neutral_es_la_de_m4_y_el_informe_es_de_solo_lectura` | Mismo texto fijo que M4 y conteo de filas sin cambios |
| `persona_es_visible_equivale_a_que_alguna_fecha_del_periodo…` | Equivalencia con `decidir_lectura` para todas las combinaciones de consultante, persona y período del escenario |
| `403_o_404_dependen_de_la_visibilidad_en_el_periodo…` | Un período que toca la estancia en el equipo da 403; uno posterior al traslado da el mismo 404 que una persona que nunca perteneció |
| `el_estado_al_corte_sigue_la_secuencia…` | Traslado con un avance protegido que determina el estado al corte: `estado_no_disponible` sin sustituirlo por el Bloqueada anterior; con un corte anterior se muestra; la propietaria ve el último; los cinco grupos suman las actividades con registros |

### 14.6 Evidencia por criterio (parcial)

Ningún criterio se declara cumplido ni se modifica. M5-T1 solo aporta evidencia del **núcleo determinista**; los criterios que exigen la narrativa o la ruta se completan en M5-T3 y M5-T4.

| Criterios | Evidencia del núcleo en M5-T1 | Pendiente |
|---|---|---|
| CA-152, CA-153 | Informe propio y de una persona del equipo | La obtención completa del informe (narrativa y ruta): M5-T3 y M5-T4 |
| CA-154 | 403 para un compañero visible | Ruta: M5-T4 |
| CA-156, CA-157, CA-224, CA-225, CA-226, CA-227, CA-276 | Pruebas de traslado y de autorización de los datos | Verificación sobre el informe completo: M5-T4 |
| CA-162, CA-164 | Las seis cifras de 13.1 coinciden con un recuento manual y son deterministas | Catálogo formal pendiente de aprobar |
| CA-165 | Los bloqueos llevan su motivo | Unidad `[ABIERTA: P-3]` |
| CA-167 | Actividad marcada por error excluida de hechos y cifras | — |
| CA-172, CA-173, CA-202, CA-199, CA-201 | `sin_datos` sin hechos ni cifras inventadas; un único registro autorizado (Gina) genera con esa información; CA-202 con visibilidad en el período y ningún registro autorizado | **P-10** (sin visibilidad en el período da 404); que el generador no se invoque: M5-T3 |
| CA-234 | Un avance protegido determina el estado al corte: el informe del equipo nuevo no muestra un estado derivado exclusivamente de registros de otro equipo (`estado_no_disponible`) | Verificación sobre el informe completo: M5-T4 |
| CA-166 | Solo la parte de que el texto libre se conserva como dato | Resistencia a órdenes: M5-T3 y M5-T7 |
| CA-02, CA-05, CA-19, CA-20 | — | M5-T4 y M5-T8 |
| CA-155, CA-158 a CA-161, CA-163, CA-171, CA-174, CA-175, CA-200 | No aplican a este ticket | M5-T3, M5-T4 y M5-T6 |

### 14.7 Preguntas todavía abiertas

| Id | Pregunta | Tratamiento en M5-T1 |
|---|---|---|
| P-3 | Unidad de `bloqueos` (por avance o por actividad) | Abierta; implementado provisionalmente por avance |
| P-5 | Campos públicos de `hechos` y de `actividades` | Abierta; no bloquea el núcleo |
| P-6 | Texto de la declaración `base` | Abierta; es de M5-T4 |
| P-8 | Valores de los límites (D-M5-06) | Abierta; no se implementó ningún límite |
| **P-10** | Con la corrección de P-9, una persona sin visibilidad en ningún día del período da 404, también para un supervisor que antes obtenía `sin_datos`; CA-202 se cumple cuando hay visibilidad en el período y ningún registro autorizado | Nueva; se aplicó la instrucción de no revelar relaciones históricas. Confirmar |
| D-M5-04 | Aprobación formal del catálogo | Las definiciones se aplican por decisión del 2026-11-18 |

No quedó ninguna decisión indispensable sin resolver para M5-T1. **Riesgo conocido que no cambia el diseño:** el informe de un período muy largo no tiene aún un límite de amplitud (D-M5-06). El servicio interno no se expone hasta que M5-T3 y M5-T4 lo apliquen.
