# SMARTWORK — Contratos de la API: índice

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]`, cerrado como base de especificación; pendiente de la validación final de la persona responsable |
| **Versión** | 0.5 |
| **Fecha** | 2026-11-06 |
| **Base** | `docs/producto/alcance-mvp.md` (0.14), `docs/producto/prd.md` (0.12), `docs/backlog/indice.md` (0.9), `docs/modelo-datos/modelo-datos.md` (0.6) |

## 1. Documentos

| Documento | Contenido |
|---|---|
| [convenciones.md](convenciones.md) | Estilo, autorización, errores, apertura de bitácoras, reintentos, listados, textos, esquemas y parámetros configurables |
| [m1-acceso-usuarios-equipos.md](m1-acceso-usuarios-equipos.md) | Contratos de M1 |
| [m2-bitacoras.md](m2-bitacoras.md) | M2-01a a M2-08 |
| [m3-seguimiento-auditoria.md](m3-seguimiento-auditoria.md) | M3-01 a M3-07 |
| [m4-consulta-supervision.md](m4-consulta-supervision.md) | M4-01 a M4-04 |
| [m5-informes.md](m5-informes.md) | Contratos públicos de M5, independientes del proveedor |
| [m1-m5-dependencias.md](m1-m5-dependencias.md) | Decisiones de seguridad y privacidad que siguen pendientes |
| [ADR-002](../arquitectura/adr/ADR-002-autenticacion-y-acceso.md) | Autenticación (propuesto en lo operativo) |
| [ADR-003](../arquitectura/adr/ADR-003-integracion-de-ia.md) | Integración de IA (propuesto) |

## 2. Inventario y estado

**Estados:** *Cerrado*: completo y coherente con las decisiones confirmadas. *Preliminar*: completo en lo funcional, con una decisión operativa que se resuelve en la siguiente fase (sección 5). *Condicionado*: no se puede fijar sin esa decisión.

| Id | Operación | Método y ruta | Quién | HU | Estado | Pendiente |
|---|---|---|---|---|---|---|
| M2-01a | Consultar mi bitácora de una fecha | `GET /api/v1/mi/bitacoras/{fecha_laboral}` | Propietaria | 2.1, 2.7 | **Cerrado** | — |
| M2-01b | Abrir mi bitácora de una fecha | `POST /api/v1/mi/bitacoras` | Propietaria | 2.1, 2.7, 3.5 | **Cerrado** | — |
| M2-02 | Guardar el resumen libre | `PUT /api/v1/mi/bitacoras/{fecha_laboral}/resumen` | Propietaria | 2.1, 3.4, 3.5 | **Cerrado** | — |
| M2-03 | Planificar una actividad nueva | `POST /api/v1/mi/bitacoras/{fecha_laboral}/planificaciones` | Propietaria | 2.2, 2.3 | **Cerrado** | — |
| M2-04 | Planificar la continuación de una actividad | `POST /api/v1/mi/actividades/{actividad_id}/continuaciones-planificadas` | Propietaria | 2.3 | **Cerrado** | — |
| M2-05 | Registrar un avance | `POST /api/v1/mi/actividades/{actividad_id}/avances` | Propietaria | 2.4, 2.5, 2.8, 3.1, 3.2 | **Cerrado** | — |
| M2-06 | Registrar una actividad no planificada | `POST /api/v1/mi/actividades-no-planificadas` | Propietaria | 2.6 | **Cerrado** | — |
| M2-07 | Consultar una actividad propia | `GET /api/v1/mi/actividades/{actividad_id}` | Propietaria | 2.9, 3.1 | **Cerrado** | — |
| M2-08 | Listar mis actividades | `GET /api/v1/mi/actividades` | Propietaria | 3.1, 3.2 | **Cerrado** | — |
| M3-01 | Cerrar mi jornada | `POST /api/v1/mi/bitacoras/{fecha_laboral}/cierre` | Propietaria | 3.3 | **Cerrado** | — |
| M3-02 | Reabrir mi bitácora | `POST /api/v1/mi/bitacoras/{fecha_laboral}/reapertura` | Propietaria | 3.4 | **Cerrado** | — |
| M3-03 | Corregir un avance | `PATCH /api/v1/mi/avances/{avance_id}` | Propietaria | 3.4, 3.5, 3.8 | **Cerrado** | — |
| M3-04 | Reactivar una actividad Completada | `POST /api/v1/mi/actividades/{actividad_id}/reactivacion` | Propietaria | 3.8 | **Cerrado** | — |
| M3-05 | Marcar una actividad como registrada por error | `POST /api/v1/mi/actividades/{actividad_id}/marca-error` | Propietaria | 3.7 | **Cerrado** | — |
| M3-06 | Revertir la marca de error | `POST /api/v1/mi/actividades/{actividad_id}/marca-error/reversion` | Propietaria | 3.7 | **Cerrado** | — |
| M3-07 | Consultar la auditoría de un registro | `GET /api/v1/auditoria` | Propietaria; supervisor autorizado | 3.6 | **Cerrado** | — |
| M4-01 | Consultar la bitácora de un compañero | `GET /api/v1/personas/{persona_id}/bitacoras/{fecha_laboral}` | Equipo histórico | 4.1 | **Cerrado** | — |
| M4-02 | Consultar el histórico por colaborador y fechas | `GET /api/v1/historico` | Según autorización | 4.2 | **Cerrado** | — |
| M4-03 | Obtener la vista de supervisión del equipo | `GET /api/v1/equipo/supervision` | Supervisor con acceso efectivo | 4.3 | **Cerrado** | — |
| M4-04 | Consultar el historial de una actividad del equipo | `GET /api/v1/equipo/actividades/{actividad_id}` | Supervisor con acceso efectivo | 4.4 | **Cerrado** | — |
| M5-01 | Generar un informe individual | `POST /api/v1/informes/individuales` | Propietaria; supervisor autorizado | 5.1 a 5.5 | **Cerrado** (contrato público) | Catálogo de agregaciones |
| M5-02 | Generar un informe consolidado | `POST /api/v1/informes/consolidados` | Supervisor con acceso efectivo | 5.3 a 5.5 | **Cerrado** (contrato público) | Catálogo de agregaciones |
| M1-01a | Iniciar sesión | `POST /api/v1/sesion` | Pública | 1.1, 1.7 | Preliminar | Parámetros de acceso |
| M1-01b | Cerrar sesión | `POST /api/v1/sesion/cierre` | Persona con sesión | 1.1 | Preliminar | — |
| M1-01c | Consultar mi sesión | `GET /api/v1/sesion` | Persona con sesión | 1.1 | Preliminar | Aprobar la operación |
| M1-03b | Completar el primer acceso | `POST /api/v1/acceso/primer-acceso` | Pública con código | 1.5 | Preliminar | Parámetros de los códigos y de las contraseñas |
| M1-09b | Completar la recuperación | `POST /api/v1/acceso/recuperacion` | Pública con código | 1.6 | Preliminar | Ídem |
| M1-02a | Crear un equipo | Orden de provisión (invocación pendiente) | Persona operadora | 1.5 | Preliminar | Forma de la provisión |
| M1-02b | Crear una persona con su primera pertenencia | Orden de provisión (invocación pendiente) | Persona operadora | 1.2, 1.5 | Preliminar | Forma de la provisión |
| M1-05 | Registrar un traslado o un cambio de rol | Orden de provisión (invocación pendiente) | Persona operadora | 1.2, 1.3, 1.4 | Preliminar | Forma de la provisión |
| M1-06 | Finalizar una pertenencia | Orden de provisión (invocación pendiente) | Persona operadora | 1.7, 1.2 | Preliminar | Forma de la provisión |
| M1-07 | Cancelar o sustituir una operación programada | Orden de provisión (invocación pendiente) | Persona operadora | 1.3 | Preliminar | Forma de la provisión |
| M1-08 | Desactivar el acceso | Orden de provisión (invocación pendiente) | Persona operadora | 1.7 | Preliminar | Forma de la provisión |
| M1-03a | Emitir el código de primer acceso | Orden de provisión (invocación pendiente) | Persona operadora | 1.5 | **Condicionado** | Medio de entrega |
| M1-09a | Emitir el código de recuperación | Orden de provisión (invocación pendiente) | Persona operadora | 1.6 | **Condicionado** | Verificación de identidad y medio de entrega |

Resumen: **20 de 20 contratos de M2 a M4 cerrados**; **2 contratos públicos de M5 cerrados** (la integración interna depende de PA-09); **13 contratos de M1**, de ellos 11 preliminares y 2 condicionados.

Divisiones técnicas respecto al catálogo preliminar, sin añadir funcionalidad: M2-01 en consultar y abrir; M3-03 en la corrección de un avance (este contrato) y la del resumen (que reutiliza M2-02); M1-02 y M1-04 fusionados en M1-02b.

**Operaciones sin contrato, justificadas.** La reactivación de un acceso desactivado (M1-10) no tiene regla que la respalde. CA-09 (composición de un equipo) y CA-13 (historial de pertenencias) no requieren una operación adicional: se verifican con las respuestas de M1-02b y M1-05. Crear una consulta pública sería funcionalidad no pedida.

## 3. Decisiones

| Id | Qué decide | Requisito | Estado |
|---|---|---|---|
| T-01 | Respuesta pública indistinguible ante registros inexistentes y no autorizados | RNF-13 | **Aprobada y sincronizada** |
| T-03 | Prefijo `/api/v1` | ADR-001 | **Aprobada** |
| D-01 | Apertura de bitácoras explícita e implícita | RN-107 | **Aprobada y sincronizada** |
| D-02 | Auditoría de la primera escritura efectiva sobre una jornada pasada | RN-111 | **Confirmada y sincronizada** |
| D-03 | Contenido significativo obligatorio; título obligatorio; longitudes como parámetros configurables | RN-112 (y RN-21, RN-24, RN-50, RN-59, RN-70 ya existentes) | **Confirmada y sincronizada** |
| D-04 | Reapertura previa para modificar una jornada cerrada | RN-108 | **Aprobada y sincronizada** |
| D-04b | Las actividades marcadas no cuentan para el cierre | RN-109 | **Aprobada y sincronizada** |
| D-05 | Revertir la marca antes de corregir avances | RN-113 | **Confirmada y sincronizada** |
| D-06 | El corte es el último día del período | RN-48 | **Aprobada y sincronizada** |
| D-07 | «Actividad en continuidad» con identificador opaco | RN-101; PA-26 resuelto | **Confirmada y sincronizada** |
| D-08 | Rango obligatorio y persona opcional en el histórico | RN-25 | **Confirmada y sincronizada** |
| D-09 | Referencia mínima para la actividad heredada sin avances autorizados | RN-89 | **Aprobada** |
| D-11 | Auditoría de provisión separada de la consulta funcional | RN-110 | **Aprobada y sincronizada** |
| D-10 | Paginación y límites configurables | PA-13 | Decisión técnica aceptada |
| T-02 | Catálogo coherente de errores | Ninguno (técnica) | Decisión técnica aceptada |
| T-04 | Clave de idempotencia y serialización | RN-41 | Decisión técnica aceptada |

No quedan contradicciones que impidan cerrar un contrato.

## 4. Parámetros configurables

La lista y la regla de error de cada uno están en [convenciones.md](convenciones.md), sección 9. Los contratos fijan nombre, unidad, error al incumplirlos y comportamiento; ningún contrato fija un valor numérico. Los valores se deciden con PA-13 (y, para acceso e informes, en la fase de implementación con los ADR-002 y ADR-003).

## 5. Pendientes para la siguiente fase

| Pendiente | Dónde se documenta | Afecta |
|---|---|---|
| Forma operativa de la provisión y autorización de la persona operadora | ADR-002, secciones 9 y 14 | Órdenes de M1 |
| Medio de entrega de códigos y verificación de identidad al recuperar | ADR-002, sección 8 | M1-03a, M1-09a |
| Valores de duración, intentos y contraseña | ADR-002, sección 7 | M1-01a, M1-03b, M1-09b |
| Reactivación del acceso: falta una RN | ADR-002, sección 11 | M1-10 |
| Proveedor, modelo, región y retención de la IA; marco legal | ADR-003 | Integración interna de M5 |
| Catálogo definitivo de agregaciones | `m5-informes.md` | M5-01, M5-02 |

## 6. Verificación de la trazabilidad

Se comprobó con un script de la sesión de trabajo, que no forma parte del repositorio:

| Comprobación | Resultado |
|---|---|
| Contratos con los once campos exigidos (en M1, «Invocación» sustituye a «Método y ruta» y «Pendientes» a «Decisiones pendientes») | 35 de 35 |
| HU, RF y RN citados que existen | Todos |
| RF citados por un contrato que figuran en los requisitos de sus HU | Todos |
| Criterios vinculados que pertenecen a las HU citadas | Todos |
| Criterios de las historias de M1 a M4 vinculados a algún contrato | 263 de 263 |
| Criterios de las historias de M5 vinculados a algún contrato | 38 de 38 |
| Historias con al menos un contrato | 33 de 33 |
| Método y ruta iguales a los del índice; rutas sin duplicar | Sí |
| IR, RA y DM citadas que existen en el modelo | Todas |

HU-1.4 no tiene contrato propio: sus criterios se verifican con las operaciones de lectura de M2 y M4. Esta verificación comprueba la coherencia documental. No prueba que los contratos se cumplan.
