# SMARTWORK — Tickets de frontend

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]`, tickets documentales |
| **Versión** | 0.1 |
| **Índice y flujo principal** | [indice.md](indice.md) |
| **Fuente** | `docs/api/` (0.5) y las historias de `docs/backlog/` |

Cliente web en Flutter Web (ADR-001). Cada ticket consume contratos ya definidos; la interfaz no decide autorizaciones ni reglas de negocio. Definición de terminado común en el [índice](indice.md#definición-de-terminado-común).

#### FE-01 — Estructura del cliente y acceso a la API
- **Prioridad:** P0 · **Capa:** Frontend
- **Objetivo:** Base del cliente: navegación, cliente HTTP y manejo de errores.
- **Historias y criterios:** transversal; sin criterios propios.
- **Contratos y documentos:** `docs/api/convenciones.md` (errores, paginación, idempotencia, CSRF); ADR-002, sección 12.
- **Descripción técnica:** Cliente que usa las cookies del navegador, envía el token CSRF y `Idempotency-Key` en las operaciones que lo exigen, y traduce los códigos de error a mensajes que no revelan datos protegidos. Mismo origen que la API.
- **Dependencias:** BE-01.
- **Terminado cuando:**
  - Todos los códigos del catálogo tienen un mensaje comprensible.
  - Una operación que modifica reutiliza la misma clave en un reintento.
  - El cliente no guarda contraseñas ni tokens en almacenamiento persistente del navegador.

#### FE-02 — Acceso: sesión, primer acceso y recuperación
- **Prioridad:** P0 (inicio de sesión) y P1 (primer acceso y recuperación) · **Capa:** Frontend
- **Objetivo:** Que la persona acceda y cierre su sesión.
- **Historias y criterios:** HU-1.1 (CA-01, CA-02, CA-05), HU-1.5 (CA-23 a CA-25), HU-1.6 (CA-27, CA-254), HU-1.7 (CA-29).
- **Contratos y documentos:** M1-01a, M1-01b, M1-03b, M1-09b.
- **Descripción técnica:** Pantalla de inicio de sesión con errores genéricos, pantallas de canje de código con fijación de contraseña, cierre de sesión, y mensajes diferenciados solo para acceso desactivado o sin pertenencia.
- **Dependencias:** FE-01, BE-03 (y BE-05 para primer acceso y recuperación).
- **Terminado cuando:**
  - Un error de credenciales no indica si falló el identificador o la contraseña.
  - Sin sesión, ninguna pantalla muestra datos de bitácoras.

#### FE-03 — Navegación y contexto por rol
- **Prioridad:** P0 · **Capa:** Frontend
- **Objetivo:** Presentar solo lo que corresponde al rol vigente.
- **Historias y criterios:** HU-1.1 (CA-03, CA-04).
- **Contratos y documentos:** M1-01c (pendiente de aprobar).
- **Descripción técnica:** Menú y rutas según el rol vigente devuelto por la API; la vista consolidada solo para supervisores. La API sigue siendo quien impide el acceso.
- **Dependencias:** FE-02, BE-03.
- **Terminado cuando:**
  - Un colaborador no ve la entrada a la vista de supervisión.
  - Forzar la ruta de supervisión como colaborador muestra el error de operación no permitida.

#### FE-04 — Mi jornada: bitácora, resumen, cierre y reapertura
- **Prioridad:** P0 · **Capa:** Frontend
- **Objetivo:** Que la persona vea y complete su jornada.
- **Historias y criterios:** HU-2.1 (CA-32 a CA-36, CA-280 a CA-282), HU-2.7 (CA-59 a CA-65), HU-3.3 (CA-89 a CA-98, CA-283), HU-3.4 (CA-99 a CA-101, CA-284).
- **Contratos y documentos:** M2-01a, M2-01b, M2-02, M3-01, M3-02.
- **Descripción técnica:** Pantalla de la jornada de una fecha con las tres fechas, resumen, estado de la bitácora y acciones de cierre y reapertura (con motivo). Mensajes que expliquen qué condición de cierre falta.
- **Dependencias:** FE-01, BE-06, BE-09.
- **Terminado cuando:**
  - Cerrar una jornada sin resumen o sin actividad válida muestra qué falta.
  - Reabrir exige un motivo.
  - Una jornada cerrada no ofrece editar sin reabrir.

#### FE-05 — Actividades: planificar, registrar avances, listar y detalle
- **Prioridad:** P0 · **Capa:** Frontend
- **Objetivo:** El flujo central de trabajo diario.
- **Historias y criterios:** HU-2.2 a HU-2.6, HU-2.8, HU-2.9 (CA-37 a CA-58, CA-66 a CA-80, CA-179 a CA-186), HU-3.1 y HU-3.2 (CA-81 a CA-88).
- **Contratos y documentos:** M2-03 a M2-08.
- **Descripción técnica:** Formularios de planificación, avance y actividad no planificada con estado, descripción y motivo de bloqueo condicional; selección explícita de la actividad que se continúa; detalle con la secuencia, el estado actual y la planificación diferenciados.
- **Dependencias:** FE-04, BE-07, BE-08.
- **Terminado cuando:**
  - El motivo de bloqueo solo se pide si el estado es Bloqueada.
  - Una actividad Completada indica que hay que reactivarla antes de continuarla.
  - La planificación se distingue visualmente del avance de ejecución.

#### FE-06 — Correcciones, reactivación y marca de error
- **Prioridad:** P1 · **Capa:** Frontend
- **Objetivo:** Corregir sin perder trazabilidad.
- **Historias y criterios:** HU-3.4 (CA-102 a CA-104), HU-3.7 (CA-115 a CA-123, CA-287 a CA-290, CA-297, CA-298), HU-3.8 (CA-124 a CA-129, CA-187 a CA-192, CA-269 a CA-271).
- **Contratos y documentos:** M3-03 a M3-06.
- **Descripción técnica:** Acciones de corregir un avance, reactivar y marcar o revertir una marca, con la explicación de los rechazos (`SECUENCIA_INVALIDA`, `MARCA_INVALIDARIA_CIERRE`, actividad marcada).
- **Dependencias:** FE-05, BE-11.
- **Terminado cuando:**
  - Un rechazo por secuencia o por cierre explica la causa y qué hacer.
  - Una actividad marcada muestra que hay que revertir la marca antes de corregir.

#### FE-07 — Consulta de equipo e histórico
- **Prioridad:** P1 · **Capa:** Frontend
- **Objetivo:** Leer lo que hacen los compañeros y recuperar el histórico.
- **Historias y criterios:** HU-4.1 (CA-130 a CA-133, CA-193), HU-4.2 (CA-134 a CA-136, CA-299, CA-300).
- **Contratos y documentos:** M4-01, M4-02.
- **Descripción técnica:** Vista en solo lectura de la bitácora de un compañero; consulta del histórico con rango obligatorio, persona opcional y paginación; sin búsqueda por texto.
- **Dependencias:** FE-01, BE-12.
- **Terminado cuando:**
  - Ninguna pantalla de lectura ofrece botones de edición.
  - La consulta del histórico no se envía sin rango de fechas.

#### FE-08 — Vista de supervisión e historial de actividad
- **Prioridad:** P0 (vista) y P1 (historial) · **Capa:** Frontend
- **Objetivo:** Que el supervisor vea el estado de su equipo en un período.
- **Historias y criterios:** HU-4.3 (CA-137 a CA-147, CA-195 a CA-198, CA-218 a CA-223, CA-230 a CA-233, CA-272 a CA-274, CA-301), HU-4.4 (CA-148 a CA-151, CA-275, CA-292).
- **Contratos y documentos:** M4-03, M4-04.
- **Descripción técnica:** Selección del período, totales por estado, listado paginado con estado al corte y estado actual indicado aparte, referencias mínimas diferenciadas, actividades heredadas con «Actividad en continuidad», historial en solo lectura.
- **Dependencias:** FE-03, BE-13.
- **Terminado cuando:**
  - No hay clasificaciones ni puntuaciones de personas en ninguna pantalla.
  - La referencia mínima se distingue visualmente del acceso completo.
  - Ningún botón permite modificar registros desde la vista.

#### FE-09 — Auditoría de un registro
- **Prioridad:** P1 · **Capa:** Frontend
- **Objetivo:** Consultar los cambios de un registro.
- **Historias y criterios:** HU-3.6 (CA-108 a CA-114, CA-285, CA-286).
- **Contratos y documentos:** M3-07.
- **Descripción técnica:** Línea de tiempo de una bitácora, actividad o avance con autor, momento, operación, motivo y valores anterior y nuevo.
- **Dependencias:** FE-01, BE-10.
- **Terminado cuando:**
  - Se puede reconstruir cada corrección y cada ciclo de cierre y reapertura.
  - Ante un registro no autorizado se muestra el mismo mensaje que ante uno inexistente.

#### FE-10 — Informes
- **Prioridad:** P2 · **Capa:** Frontend · **Condicionado a la integración de IA (ADR-003)**
- **Objetivo:** Solicitar y leer informes individuales y consolidados.
- **Historias y criterios:** HU-5.1 (CA-152 a CA-160), HU-5.2 (CA-161 a CA-167), HU-5.3 (CA-168 a CA-171), HU-5.4 (CA-172, CA-173, CA-199 a CA-202), HU-5.5 (CA-174, CA-175).
- **Contratos y documentos:** M5-01, M5-02.
- **Descripción técnica:** Formulario de período; presentación en pantalla del informe sin edición ni historial; distinción de hechos y agregaciones; mensajes de «sin datos», de límites excedidos y de «el informe no pudo generarse».
- **Dependencias:** FE-01, BE-15 (BE-16 para la narrativa).
- **Terminado cuando:**
  - Al salir del informe no queda ninguna copia guardada.
  - Con el servicio no disponible no se muestra ningún contenido parcial.

#### FE-11 — Accesibilidad y calidad de la interfaz
- **Prioridad:** P1 · **Capa:** Frontend
- **Objetivo:** Mitigar los riesgos conocidos de Flutter Web (accesibilidad, carga inicial, pruebas).
- **Historias y criterios:** transversal; ver R-11 de la arquitectura.
- **Contratos y documentos:** `docs/arquitectura/arquitectura-general.md`, riesgo R-11; ADR-001.
- **Descripción técnica:** Etiquetas semánticas, navegación por teclado, contraste suficiente y medición de la carga inicial en los flujos principales.
- **Dependencias:** FE-01.
- **Terminado cuando:**
  - El flujo principal se completa solo con el teclado.
  - Los controles tienen etiquetas legibles por un lector de pantalla.
