# SMARTWORK — Tickets de backend

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]`, tickets documentales |
| **Versión** | 0.1 |
| **Índice y flujo principal** | [indice.md](indice.md) |
| **Fuente** | `docs/api/` (0.5), `docs/arquitectura/` y `docs/modelo-datos/modelo-datos.md` (0.6) |

Cada ticket implementa uno o varios contratos de [docs/api/](../../api/indice.md). Los criterios de aceptación se agrupan por historia; no hay un ticket por criterio. Definición de terminado común en el [índice](indice.md#definición-de-terminado-común).

#### BE-01 — Estructura del servicio y convenciones comunes
- **Prioridad:** P0 · **Capa:** Backend
- **Objetivo:** Dejar la base sobre la que se construyen todas las operaciones.
- **Historias y criterios:** transversal; sin criterios propios.
- **Contratos y documentos:** `docs/api/convenciones.md` (estilo, errores T-02, paginación D-10, textos D-03); ADR-001.
- **Descripción técnica:** Aplicación FastAPI de monolito modular con un módulo por funcionalidad (acceso, bitácoras, seguimiento, consulta, informes). Prefijo `/api/v1`. Estructura de error común con los códigos del catálogo. Validación de campos desconocidos como `SOLICITUD_INVALIDA`. Parámetros configurables (límites, longitudes, ventanas) leídos de la configuración, sin valores en el código. Fecha actual calculada en el servidor en la zona de la organización (DM-06).
- **Dependencias:** ninguna.
- **Terminado cuando:**
  - Cada código de error del catálogo se devuelve con su estado HTTP y sin detalles internos.
  - Una petición con un campo desconocido se rechaza.
  - Ningún valor de los parámetros configurables aparece fijado en el código.

#### BE-02 — Autorización histórica centralizada
- **Prioridad:** P0 · **Capa:** Backend
- **Objetivo:** Un único punto que decide qué ve y qué hace cada persona.
- **Historias y criterios:** HU-1.4 (CA-15 a CA-21, CA-176 a CA-178, CA-212 a CA-217), RNF-13 (CA-286, CA-291).
- **Contratos y documentos:** convenciones 3.1 a 3.3 (T-01); modelo, sección 12 (RA-01 a RA-12, DM-03, DM-04).
- **Descripción técnica:** Función «equipo en una fecha» y política que aplican el orden de evaluación (identidad, acceso, formato, visibilidad, permiso, reglas). Filtrado de autorización al seleccionar datos, antes de construir respuestas. Proyección de actividad completa o neutral («Actividad en continuidad»). Respuesta idéntica para recurso inexistente y no autorizado.
- **Dependencias:** BE-01, DB-01, DB-06.
- **Terminado cuando:**
  - Las pruebas de la matriz de permisos (propietaria, compañero del equipo histórico, supervisor, supervisor del equipo anterior, otro equipo) pasan.
  - Dos peticiones, una sobre un recurso inexistente y otra sobre uno ajeno, devuelven respuestas indistinguibles.
  - Ningún módulo reimplementa un filtro de visibilidad propio.

#### BE-03 — Autenticación con sesiones revocables
- **Prioridad:** P0 · **Capa:** Backend
- **Objetivo:** Que una persona se identifique, mantenga una sesión y la cierre.
- **Historias y criterios:** HU-1.1 (CA-01 a CA-05), HU-1.7 (CA-29, CA-255, CA-259).
- **Contratos y documentos:** M1-01a, M1-01b, M1-01c; ADR-002 (secciones 4, 5, 7 y 12).
- **Descripción técnica:** Verificación de contraseña con Argon2id; sesión en servidor con identificador opaco en cookie `__Host-`, `Secure`, `HttpOnly`, `SameSite=Strict`; token CSRF con cabecera propia y verificación del origen; comprobación en cada petición de sesión vigente, acceso no desactivado (IR-37) y pertenencia vigente (IR-38); respuestas uniformes ante credenciales inválidas; esperas crecientes ante fallos. Los valores de los parámetros se leen de la configuración (ADR-002, sección 7).
- **Dependencias:** BE-01, BE-02, DB-02.
- **Terminado cuando:**
  - Un identificador inexistente y una contraseña incorrecta producen la misma respuesta.
  - Tras desactivar el acceso, la siguiente petición con una sesión previa se rechaza.
  - Una petición que modifica sin token CSRF o desde otro origen se rechaza.
  - Ninguna respuesta ni registro contiene la contraseña (CA-05).

#### BE-04 — Provisión: personas, equipos y pertenencias
- **Prioridad:** P0 · **Capa:** Backend
- **Objetivo:** Poder crear equipos y personas y gestionar pertenencias sin romper el historial.
- **Historias y criterios:** HU-1.2 (CA-06 a CA-10, CA-240 a CA-242), HU-1.3 (CA-11 a CA-14, CA-243 a CA-248, CA-278, CA-279), HU-1.5 (CA-22, CA-26, CA-250 a CA-253), HU-1.7 (CA-30, CA-31, CA-257, CA-258, CA-262), CA-09, CA-13.
- **Contratos y documentos:** M1-02a, M1-02b, M1-05, M1-06, M1-07 (órdenes de provisión); ADR-002, sección 9.
- **Descripción técnica:** Casos de uso independientes de cómo se invoquen. Validación de la línea temporal completa antes de aplicar (IR-02, IR-03, IR-28, IR-32, IR-39) en una transacción atómica con su entrada de auditoría. Identificación y autorización de la persona operadora separadas del acceso al servidor. La forma de invocación se decide en la implementación.
- **Dependencias:** BE-01, BE-02, DB-01, DB-04.
- **Terminado cuando:**
  - Un traslado con efecto hoy o anterior se rechaza; uno posterior se acepta y no cambia los registros de hoy.
  - Una cancelación que dejaría un equipo con colaboradores sin supervisor se rechaza sin cambios.
  - Cada orden deja una única entrada de auditoría sin credenciales.

#### BE-05 — Códigos de acceso, recuperación y desactivación
- **Prioridad:** P1 · **Capa:** Backend · **Condicionado a ADR-002 (medio de entrega y verificación de identidad)**
- **Objetivo:** Completar el ciclo de vida del acceso.
- **Historias y criterios:** HU-1.5 (CA-23 a CA-25), HU-1.6 (CA-27, CA-28, CA-254), HU-1.7 (CA-255, CA-256, CA-260, CA-261).
- **Contratos y documentos:** M1-03a, M1-03b, M1-08, M1-09a, M1-09b; ADR-002, secciones 6 a 8.
- **Descripción técnica:** Emisión de códigos de un solo uso (mostrados una vez, solo hash guardado), canje atómico, revocación de sesiones, rechazo del canje con acceso desactivado (DD-05) y desactivación inmediata sin bloqueo por la regla del supervisor.
- **Dependencias:** BE-03, BE-04, DB-02.
- **Terminado cuando:**
  - Un código usado, caducado o de un acceso desactivado produce el mismo error.
  - La recuperación no reactiva un acceso desactivado.
  - Desactivar al único supervisor deja el equipo identificable como pendiente de supervisión efectiva.

#### BE-06 — Bitácoras y resumen
- **Prioridad:** P0 · **Capa:** Backend
- **Objetivo:** Abrir, consultar y completar la bitácora propia de una fecha.
- **Historias y criterios:** HU-2.1 (CA-32 a CA-36, CA-280 a CA-282), HU-2.7 (CA-59 a CA-65, CA-264), HU-3.5 (CA-294).
- **Contratos y documentos:** M2-01a, M2-01b, M2-02; convenciones 5.1.
- **Descripción técnica:** Apertura idempotente (`creada`), apertura implícita en la primera escritura, consulta sin creación, fecha cubierta por una pertenencia, tres fechas visibles, resumen con auditoría en jornadas pasadas.
- **Dependencias:** BE-02, DB-03, DB-04.
- **Terminado cuando:**
  - Abrir N veces la misma fecha, también en paralelo, deja una sola bitácora y una sola respuesta 201.
  - Consultar una fecha sin bitácora no la crea.
  - Una fecha anterior a la primera pertenencia se rechaza.

#### BE-07 — Actividades y planificación
- **Prioridad:** P0 · **Capa:** Backend
- **Objetivo:** Planificar y consultar actividades.
- **Historias y criterios:** HU-2.2 (CA-37 a CA-41, CA-263, CA-295), HU-2.3 (CA-42 a CA-44, CA-179 a CA-184, CA-209, CA-210), HU-2.6 (CA-53 a CA-58, CA-296), HU-3.1 y HU-3.2 (CA-81 a CA-88).
- **Contratos y documentos:** M2-03, M2-04, M2-06, M2-07, M2-08.
- **Descripción técnica:** Actividad nueva en Pendiente con planificación original; continuación planificada sin avances ni cambio de estado; actividad no planificada con su primer avance atómico; listado sin búsqueda por texto; título obligatorio; textos con máximos configurables.
- **Dependencias:** BE-06, DB-03.
- **Terminado cuando:**
  - Planificar una continuación no modifica el estado actual ni la secuencia.
  - Una actividad Completada rechaza su continuación hasta reactivarla.
  - Un título vacío se rechaza.

#### BE-08 — Avances, secuencia y estado actual
- **Prioridad:** P0 · **Capa:** Backend
- **Objetivo:** Registrar avances manteniendo una secuencia válida y el estado actual correcto.
- **Historias y criterios:** HU-2.4, HU-2.5, HU-2.8, HU-2.9 (CA-45 a CA-52, CA-66 a CA-80, CA-185, CA-186), HU-3.8 (CA-190, CA-203 a CA-208).
- **Contratos y documentos:** M2-05; modelo, secciones 8 y 9 (IR-09 a IR-12, DM-01, DM-02).
- **Descripción técnica:** Orden total por fecha laboral, momento de registro e identificador; validación de la secuencia (IR-11) para altas retroactivas; recálculo de `estado_actual` en la misma transacción; serialización por actividad; solo se exige abierta la bitácora de la fecha del avance.
- **Dependencias:** BE-07, DB-03.
- **Terminado cuando:**
  - Un avance retroactivo anterior a una finalización se acepta sin reactivar y no altera el estado de uno posterior.
  - Un avance tras una finalización sin reactivación se rechaza.
  - Dos registros simultáneos sobre una actividad dejan un estado actual coherente con la secuencia (comprobación DM-02).

#### BE-09 — Cierre y reapertura de jornada
- **Prioridad:** P0 (cierre) y P1 (reapertura) · **Capa:** Backend
- **Objetivo:** Cerrar la jornada y poder reabrirla con motivo.
- **Historias y criterios:** HU-3.3 (CA-89 a CA-98, CA-283), HU-3.4 (CA-99 a CA-101, CA-109, CA-266, CA-284).
- **Contratos y documentos:** M3-01, M3-02.
- **Descripción técnica:** Condiciones de cierre (actividad válida creada o continuada, resumen con texto), actividades marcadas por error fuera del cómputo, jornada futura no cerrable, cierre serializado con las marcas, entrada de auditoría por cada cierre y reapertura.
- **Dependencias:** BE-06, BE-08.
- **Terminado cuando:**
  - Una jornada sin actividad válida o con el resumen vacío no se cierra.
  - Reabrir sin motivo se rechaza; el cierre, la reapertura y el nuevo cierre constan en la auditoría.

#### BE-10 — Auditoría: registro y consulta
- **Prioridad:** P0 (registro transaccional) y P1 (consulta) · **Capa:** Backend
- **Objetivo:** Que toda operación auditable deje su entrada y que se pueda consultar.
- **Historias y criterios:** HU-3.5 (CA-105 a CA-107, CA-267, CA-293), HU-3.6 (CA-108 a CA-114, CA-285, CA-286).
- **Contratos y documentos:** M3-07; modelo, sección 10.
- **Descripción técnica:** Servicio de auditoría usado por los demás módulos dentro de su transacción. Consulta con objeto obligatorio, sin listado global, visible para la propietaria y el supervisor autorizado, y sin entradas de provisión.
- **Dependencias:** DB-04, BE-02.
- **Terminado cuando:**
  - Una consulta sin `tipo_objeto` y `objeto_id` se rechaza.
  - Las entradas de provisión no aparecen en la consulta funcional.
  - Un compañero ajeno recibe la misma respuesta que ante una auditoría inexistente.

#### BE-11 — Correcciones, reactivación y marca de error
- **Prioridad:** P1 · **Capa:** Backend
- **Objetivo:** Permitir corregir sin perder trazabilidad.
- **Historias y criterios:** HU-3.4 (CA-102 a CA-104), HU-3.7 (CA-115 a CA-123, CA-287 a CA-290, CA-297, CA-298), HU-3.8 (CA-124 a CA-129, CA-187 a CA-192, CA-211, CA-236 a CA-239, CA-269 a CA-271).
- **Contratos y documentos:** M3-03, M3-04, M3-05, M3-06.
- **Descripción técnica:** Corrección validada contra la secuencia completa sin crear reactivaciones automáticas; reactivación hacia tres estados; marca de error con comprobación de las condiciones de cierre de la jornada de origen; exigir revertir la marca antes de corregir sus avances.
- **Dependencias:** BE-08, BE-09, BE-10.
- **Terminado cuando:**
  - Una corrección que dejaría un avance tras una finalización sin reactivación se rechaza y no cambia datos ni auditoría.
  - Marcar la única actividad válida de una jornada cerrada se rechaza; marcar otra con actividades válidas se acepta sin reabrir.

#### BE-12 — Consulta de equipo e histórico
- **Prioridad:** P1 · **Capa:** Backend
- **Objetivo:** Leer las bitácoras de compañeros y el histórico.
- **Historias y criterios:** HU-4.1 (CA-130 a CA-133, CA-193, CA-194, CA-291), HU-4.2 (CA-134 a CA-136, CA-299, CA-300).
- **Contratos y documentos:** M4-01, M4-02.
- **Descripción técnica:** Lectura en solo lectura según equipo histórico; histórico con rango obligatorio, persona opcional, paginación con orden estable y sin búsqueda por texto.
- **Dependencias:** BE-02, BE-06.
- **Terminado cuando:**
  - Un registro de una fecha en que la persona estaba en otro equipo no se puede abrir.
  - Un parámetro de búsqueda por texto o un rango ausente se rechazan.

#### BE-13 — Vista de supervisión e historial de actividad
- **Prioridad:** P0 (vista) y P1 (historial) · **Capa:** Backend
- **Objetivo:** Dar al supervisor la vista consolidada de su equipo.
- **Historias y criterios:** HU-4.3 (CA-137 a CA-147, CA-195 a CA-198, CA-218 a CA-223, CA-230 a CA-233, CA-272 a CA-274, CA-301), HU-4.4 (CA-148 a CA-151, CA-275, CA-292).
- **Contratos y documentos:** M4-03, M4-04.
- **Descripción técnica:** Inclusión por período, estado al corte (último día del período) con visibilidad condicionada, estado actual solo si la persona pertenece al equipo, referencia mínima, título protegido, totales por estado sobre registros autorizados, paginación.
- **Dependencias:** BE-02, BE-08.
- **Terminado cuando:**
  - El supervisor de un equipo nuevo no ve títulos ni motivos del equipo anterior.
  - Una actividad marcada por error no aparece.
  - Los totales por estado coinciden con un recuento manual de los registros autorizados.

#### BE-14 — Idempotencia y concurrencia
- **Prioridad:** P1 · **Capa:** Backend
- **Objetivo:** Evitar duplicados ante reintentos y solicitudes simultáneas.
- **Historias y criterios:** sin criterios propios; soporta T-04.
- **Contratos y documentos:** convenciones 5.3.
- **Descripción técnica:** Cabecera `Idempotency-Key` obligatoria en las operaciones no repetibles, reproducción de la respuesta original, rechazo de la reutilización con otra petición y de la ejecución simultánea.
- **Dependencias:** BE-01, DB-05.
- **Terminado cuando:**
  - Repetir una petición con la misma clave no crea un segundo avance.
  - La reutilización de la clave con otra petición devuelve `CLAVE_IDEMPOTENCIA_REUTILIZADA`.

#### BE-15 — Informes: núcleo determinista
- **Prioridad:** P1 · **Capa:** Backend
- **Objetivo:** Preparar los datos autorizados y las agregaciones de un informe sin usar IA.
- **Historias y criterios:** HU-5.1 (CA-152 a CA-157, CA-160, CA-224 a CA-227, CA-234, CA-276), HU-5.2 (CA-162 a CA-165, CA-167), HU-5.3 (CA-168 a CA-171, CA-228, CA-229, CA-235, CA-277), HU-5.4 (CA-172, CA-173, CA-199 a CA-202).
- **Contratos y documentos:** M5-01, M5-02 (estructura de la respuesta); ADR-003, secciones 7 y 9.
- **Descripción técnica:** Selección con las proyecciones de M4, agregaciones deterministas, respuesta «sin datos» sin llamar al generador, ausencia de rankings, sin persistencia, límites configurables.
- **Dependencias:** BE-02, BE-08.
- **Terminado cuando:**
  - Con los mismos registros, las agregaciones dan siempre el mismo valor y coinciden con un recuento manual.
  - Un período sin registros autorizados devuelve «sin datos» sin invocar ningún generador.

#### BE-16 — Informes: generación de texto y fallos
- **Prioridad:** P2 · **Capa:** Backend · **Condicionado a ADR-003 (proveedor, modelo, región y retención)**
- **Objetivo:** Generar la narrativa a través de una interfaz propia, independiente del proveedor.
- **Historias y criterios:** HU-5.2 (CA-161, CA-166), HU-5.4 (CA-200), HU-5.5 (CA-174, CA-175), HU-5.1 (CA-158, CA-159).
- **Contratos y documentos:** M5-01, M5-02; ADR-003, secciones 8, 9, 12 y 14.
- **Descripción técnica:** Interfaz de generación con un adaptador por proveedor; seudonimización por petición; separación estructural del texto libre; validación determinista de la salida; fallo explícito sin contenido parcial; ningún dato enviado hasta aprobar proveedor, región, retención y marco legal.
- **Dependencias:** BE-15 y las decisiones de ADR-003.
- **Terminado cuando:**
  - Con el generador no disponible, la respuesta es `INFORME_NO_GENERADO` y no hay contenido parcial.
  - Una bitácora con órdenes en su texto libre no altera el informe.
  - Cambiar de adaptador no modifica el contrato público.
