# SMARTWORK — Contratos de la API: M5 Informes individuales y consolidados

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]`. Contratos **públicos**, independientes de cualquier proveedor de IA |
| **Versión** | 0.1 |
| **Fecha** | 2026-11-06 |
| **Convenciones** | `docs/api/convenciones.md` |
| **Integración interna** | `docs/arquitectura/adr/ADR-003-integracion-de-ia.md` (proveedor, modelo, región y retención sin aprobar) |

**Independencia del proveedor.** Estos contratos no mencionan ni dependen de AWS Bedrock, de la API de Anthropic ni de ningún modelo. Ninguna petición ni respuesta contiene el proveedor, el modelo, la región ni parámetros de inferencia. El generador de texto queda detrás de una interfaz interna (ADR-001, ADR-003) y puede cambiarse sin alterar estos contratos.

**Reglas que cumplen ambos contratos**

- **Registros autorizados.** La información usada es la que la persona que genera el informe puede consultar, con las mismas proyecciones que M4: título protegido con la referencia neutral, referencia mínima, estado al corte condicionado, y exclusión de la planificación conservada y de las actividades marcadas por error (RA-04 a RA-12, RN-86). El filtrado se aplica antes de construir cualquier dato (convenciones 3.3).
- **Métricas deterministas.** Las agregaciones se calculan sin IA a partir de los registros autorizados; con los mismos registros dan siempre el mismo valor y se muestran diferenciadas de los hechos (RN-26, RN-29, CA-162, CA-164). El texto narrativo no calcula cifras: las recibe.
- **Datos insuficientes o inexistentes.** Sin registros autorizados, el informe indica explícitamente que no hay datos disponibles, no contiene nada inventado y **no se llama al generador** (RN-57, CA-172, CA-173, CA-202). Con registros, aunque sean pocos o parciales, se genera con ellos y declara que se basa solo en los registros disponibles y autorizados; no hay umbrales ni porcentajes de cobertura (CA-199, CA-200, CA-201).
- **Fallo explícito.** Si el servicio de IA falla, agota su tiempo o su salida no supera la validación, se responde `INFORME_NO_GENERADO` y no se devuelve contenido parcial (RN-58, CA-174, CA-175).
- **Sin evaluaciones ni rankings.** El informe no contiene valoraciones de personas ni ordenaciones por rendimiento (RN-26, RN-55, CA-163). En el consolidado, las personas se listan por orden alfabético de nombre.
- **Sin persistencia automática.** El informe se consulta en pantalla, no se edita, no tiene identificador ni recurso para consultarlo después y no queda en un historial (RN-56, CA-158, CA-159). Cada generación produce un informe nuevo con su propia fecha (CA-160).
- **Sin efectos sobre los datos.** Generar un informe no modifica registros; por eso no exige clave de idempotencia. Cada llamada puede consumir recursos del servicio externo, por lo que está sujeta a los límites configurables de ADR-003.

**Estructura común de la respuesta (`informe`)**

| Campo | Contenido |
|---|---|
| `tipo` | `individual` o `consolidado` |
| `periodo` | `desde` y `hasta` |
| `generado_en` | Momento real de generación (RN-29) |
| `base` | Declaración fija de que el informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada (RF-87) |
| `sin_datos` | Verdadero si no hay registros autorizados; en ese caso el informe solo indica que no hay datos disponibles |
| `agregaciones` | Indicadores deterministas, diferenciados de los hechos (ver catálogo propuesto) |
| `hechos` | Registros del período: fecha laboral, ActividadVisible, estado histórico, descripción y, si procede, motivo de bloqueo |
| `bloqueos` | Actividades bloqueadas con su motivo (RN-55) |
| `narrativa` | Texto generado a partir de los hechos y las agregaciones recibidos; nulo si `sin_datos` |

**Catálogo propuesto de agregaciones (`[PROPUESTO]`, pendiente de aprobar):** número de avances del período; número de jornadas con registros; número de actividades con registros; actividades por estado al corte (el último día del período); actividades planificadas y no planificadas con registros; número de actividades bloqueadas. Son recuentos, no porcentajes: RN-57 excluye los porcentajes de cobertura. Las actividades marcadas por error no se cuentan (CA-167).

## M5-01 — Generar un informe individual

| Campo | Contenido |
|---|---|
| **Propósito** | Generar el informe de una persona para un período |
| **Relacionados** | HU-5.1, HU-5.2, HU-5.4, HU-5.5 · RF-29, RF-32, RF-33, RF-46, RF-47, RF-48, RF-49, RF-50, RF-51, RF-74, RF-75, RF-76, RF-78, RF-87, RF-93, RF-94, RF-96, RF-100, RF-111 · RN-26, RN-29, RN-30, RN-31, RN-53, RN-55, RN-56, RN-57, RN-58, RN-60, RN-86, RN-88, RN-101 |
| **Método y ruta** | `POST /api/v1/informes/individuales` |
| **Entrada** | Cuerpo: `desde` y `hasta` (obligatorios) y `persona_id` (opcional; por defecto, la persona que llama) |
| **Respuesta** | 200 con el `informe` (estructura común), de `tipo` individual, con la persona (`id`, `nombre`). Sin identificador ni enlace para recuperarlo |
| **Validaciones** | `desde` no posterior a `hasta`. Amplitud del período, número de registros y tamaño dentro de los límites configurados (`INFORME_EXCEDE_LIMITES`, antes de generar). Solo se usan registros autorizados del período solicitado (CA-156). Una persona trasladada: el supervisor del equipo anterior obtiene solo los registros históricos de su equipo y de los períodos que conserva, sin información posterior (CA-157, CA-224, CA-225); el supervisor del equipo nuevo no recibe los detalles del equipo anterior y puede recibir la referencia mínima, sin estado al corte protegido (CA-226, CA-234); la propietaria obtiene todos sus registros del período (CA-227). Ningún título original de otro equipo (CA-276). El texto libre de las bitácoras se trata como datos y nunca como instrucciones (CA-166). Cada hecho que afirma el informe consta en los registros (CA-161). El resumen libre de la bitácora no se envía al generador (ADR-003) |
| **Autorización** | La propietaria, o el supervisor autorizado de su equipo; un compañero no puede (CA-152, CA-153, CA-154). Si la persona solicitada no está autorizada, o no existe, `RECURSO_NO_DISPONIBLE` indistinguible (RNF-13) |
| **Errores** | `RECURSO_NO_DISPONIBLE` · `INFORME_EXCEDE_LIMITES` · `INFORME_NO_GENERADO` · `SOLICITUD_INVALIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | No modifica datos. Un registro técnico de generación (quién, tipo y período, sin contenido) para controlar el consumo es una propuesta pendiente (ADR-003) |
| **Criterios vinculados** | CA-152, CA-153, CA-154, CA-155, CA-156, CA-157, CA-158, CA-159, CA-160, CA-161, CA-162, CA-163, CA-164, CA-165, CA-166, CA-167, CA-172, CA-173, CA-174, CA-175, CA-199, CA-200, CA-201, CA-202, CA-224, CA-225, CA-226, CA-227, CA-234, CA-276 |
| **Pendientes** | Catálogo de agregaciones; límites y tiempos (ADR-003); proveedor (PA-09) solo afecta a la integración interna |

## M5-02 — Generar un informe consolidado

| Campo | Contenido |
|---|---|
| **Propósito** | Generar el informe de un equipo para un período |
| **Relacionados** | HU-5.3, HU-5.2, HU-5.4, HU-5.5 · RF-30, RF-32, RF-33, RF-46, RF-47, RF-48, RF-51, RF-74, RF-76, RF-78, RF-83, RF-87, RF-98, RF-111 · RN-26, RN-29, RN-31, RN-54, RN-55, RN-56, RN-57, RN-58, RN-60, RN-86, RN-88, RN-101 |
| **Método y ruta** | `POST /api/v1/informes/consolidados` |
| **Entrada** | Cuerpo: `desde` y `hasta` (obligatorios) y `equipo_id` (opcional; por defecto, el equipo que supervisa quien llama) |
| **Respuesta** | 200 con el `informe` (estructura común), de `tipo` consolidado: agregaciones del equipo y, por persona en orden alfabético, sus hechos y bloqueos. Sin identificador |
| **Validaciones** | Las mismas que M5-01. Además, el equipo es el que supervisa quien llama; no se incluyen registros de personas trasladadas de fechas que no pertenecen históricamente al equipo (CA-228, CA-229). No se muestra un estado al corte derivado exclusivamente de registros de otro equipo (CA-235). Ningún título original de otro equipo (CA-277) |
| **Autorización** | Solo el supervisor del equipo, con acceso efectivo (RA-12). Un colaborador recibe `OPERACION_NO_PERMITIDA` (CA-169). Un `equipo_id` ajeno produce `RECURSO_NO_DISPONIBLE` (CA-170) |
| **Errores** | `OPERACION_NO_PERMITIDA` · `RECURSO_NO_DISPONIBLE` · `INFORME_EXCEDE_LIMITES` · `INFORME_NO_GENERADO` · `SOLICITUD_INVALIDA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `NO_IDENTIFICADA` |
| **Auditoría y transacción** | Como M5-01 |
| **Criterios vinculados** | CA-161, CA-162, CA-163, CA-164, CA-165, CA-166, CA-167, CA-168, CA-169, CA-170, CA-171, CA-172, CA-173, CA-174, CA-175, CA-199, CA-200, CA-201, CA-202, CA-228, CA-229, CA-235, CA-277 |
| **Pendientes** | Los de M5-01 |

## Pendientes de M5 que no cambian los contratos públicos

| Id | Pendiente | Dónde se resuelve |
|---|---|---|
| PA-09 | Proveedor, modelo, región, retención y marco legal | ADR-003 |
| P-M5-1 | Catálogo definitivo de agregaciones | Aprobación funcional |
| P-M5-2 | Registro técnico de generación para controlar el consumo | ADR-003 |
| P-M5-3 | Límites de período, registros, tamaño, tiempo y presupuesto | Parámetros configurables (convenciones, sección 9) |
| PP-11 | Enlace de cada afirmación con sus registros de origen: propuesta no aprobada; el contrato no lo incluye | Alcance |
