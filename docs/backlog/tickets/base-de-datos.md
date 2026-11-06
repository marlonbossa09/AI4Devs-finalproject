# SMARTWORK — Tickets de base de datos

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]`, tickets documentales |
| **Versión** | 0.1 |
| **Índice y flujo principal** | [indice.md](indice.md) |
| **Fuente** | `docs/modelo-datos/modelo-datos.md` (0.6) y `docs/api/` (0.5) |

Cada ticket agrupa criterios de aceptación por historia; no hay un ticket por criterio. La definición de terminado común está en el [índice](indice.md#definición-de-terminado-común). No se fija ninguna herramienta de migraciones: la elige la implementación.

#### DB-01 — Personas, equipos y pertenencias
- **Prioridad:** P0 · **Capa:** Base de datos
- **Objetivo:** Persistir `ORGANIZACION`, `EQUIPO`, `PERSONA` y `PERTENENCIA` con las restricciones que hacen imposible un historial inválido.
- **Historias y criterios:** HU-1.2 (CA-06 a CA-10, CA-240 a CA-242), HU-1.3 (CA-11 a CA-14, CA-243 a CA-248, CA-278, CA-279), HU-1.7 (CA-30, CA-31, CA-257, CA-258).
- **Contratos y documentos:** M1-02a, M1-02b, M1-05 a M1-08; modelo de datos, secciones 3.1 a 3.4 y 6.1 (IR-01 a IR-05, IR-27 a IR-32).
- **Descripción técnica:** Esquema con intervalos semiabiertos `[desde, hasta_exclusivo)`. Restricciones de la base de datos para lo expresable (no solapes por persona, un solo intervalo sin fin, `hasta_exclusivo` posterior a `desde`, como máximo un supervisor por equipo y fecha). Lo no expresable (contigüidad, equipo con colaboradores siempre con supervisor, fecha efectiva posterior a la actual) se valida en la capa de servicio dentro de la transacción (DM-05). Sin borrado físico de personas ni de pertenencias efectivas (IR-26).
- **Dependencias:** ninguna.
- **Terminado cuando:**
  - Un intento de insertar dos intervalos solapados de una persona falla en la base de datos.
  - Un intento de registrar dos supervisores simultáneos de un equipo falla.
  - La zona horaria de la organización es un dato de configuración consultable.
  - Un script de verificación demuestra que no existen huecos ni solapes dentro del período de actividad de cada persona sembrada.

#### DB-02 — Identidad, sesiones, códigos y operadores
- **Prioridad:** P0 · **Capa:** Base de datos
- **Objetivo:** Persistir las estructuras técnicas de acceso, separadas de las nueve entidades de dominio.
- **Historias y criterios:** HU-1.1 (CA-01 a CA-05), HU-1.5 (CA-23 a CA-25), HU-1.6 (CA-27, CA-254), HU-1.7 (CA-255, CA-259).
- **Contratos y documentos:** M1-01a a M1-01c, M1-03a, M1-03b, M1-09a, M1-09b; ADR-002, secciones 4 y 9; modelo, sección 3.10.
- **Descripción técnica:** `IDENTIDAD` (1 a 0..1 con `PERSONA`), `SESION`, `CODIGO_UNICO` y `OPERADOR`. Solo se guardan hashes de contraseña, de secreto de sesión, de token CSRF y de código. Identificador de acceso único y normalizado. Marcado de canje atómico de un código (un solo uso). `PERSONA.acceso_desactivado_en` se añade como columna del dominio.
- **Dependencias:** DB-01.
- **Terminado cuando:**
  - Ninguna tabla contiene una contraseña, un código ni un secreto de sesión en claro (revisión de esquema y de datos sembrados).
  - Dos canjes simultáneos del mismo código: solo uno se completa.
  - Un identificador de acceso repetido, con distinta capitalización, es rechazado.
  - `OPERADOR` no tiene relación con `PERSONA`.

#### DB-03 — Bitácoras, actividades, planificaciones y avances
- **Prioridad:** P0 · **Capa:** Base de datos
- **Objetivo:** Persistir el núcleo de M2 y M3 con sus invariantes.
- **Historias y criterios:** HU-2.1 a HU-2.9 (CA-32 a CA-80, CA-179 a CA-186, CA-209, CA-210, CA-263, CA-264, CA-280 a CA-282, CA-295, CA-296).
- **Contratos y documentos:** M2-01a a M2-08, M3-01 a M3-06; modelo, secciones 3.5 a 3.8 y 6.2 (IR-01, IR-06 a IR-18, IR-33).
- **Descripción técnica:** `BITACORA` (única por persona y fecha), `ACTIVIDAD` (propietaria inmutable, `estado_actual` derivado, marca de error), `PLANIFICACION` (original y continuación, sin edición), `AVANCE` (estado ∈ cuatro, descripción no vacía, motivo si Bloqueada, `registrado_en` e identificador asignados por el servidor). La secuencia válida (IR-11) y el recálculo de `estado_actual` (IR-12) se aplican en la capa de servicio, serializados por actividad (DM-01).
- **Dependencias:** DB-01.
- **Terminado cuando:**
  - Dos bitácoras de la misma persona y fecha no pueden coexistir.
  - No es posible cambiar la propietaria de una actividad ni borrar un avance.
  - Un avance con estado Bloqueada y sin motivo es rechazado por la base de datos.
  - Una actividad nueva sin título es rechazada.
  - Una consulta de comprobación (derivar y comparar) detecta cualquier `estado_actual` incoherente con la secuencia (DM-02).

#### DB-04 — Auditoría de solo anexado
- **Prioridad:** P0 · **Capa:** Base de datos
- **Objetivo:** Persistir `AUDITORIA` de forma que no pueda alterarse ni borrarse.
- **Historias y criterios:** HU-3.5 (CA-105 a CA-107, CA-267, CA-293, CA-294), HU-3.6 (CA-108 a CA-114, CA-285).
- **Contratos y documentos:** M3-07 y todas las operaciones que modifican; modelo, sección 3.9 (IR-23 a IR-26, IR-34 a IR-36).
- **Descripción técnica:** Una entrada por operación, con valores anterior y nuevo estructurados. `tipo_autor` (persona o provisión) con el autor correspondiente exclusivo. La aplicación usa un rol de base de datos que solo puede insertar y leer en esta tabla.
- **Dependencias:** DB-03.
- **Terminado cuando:**
  - El rol de la aplicación no puede actualizar ni borrar entradas (probado con intentos reales).
  - Una entrada con `tipo_autor` de provisión y un autor persona es rechazada.
  - Una operación de dominio atómica con su entrada: si una falla, ninguna queda (IR-24).

#### DB-05 — Registro de claves de idempotencia
- **Prioridad:** P1 · **Capa:** Base de datos
- **Objetivo:** Persistir las claves de reintento para evitar duplicados de escrituras no repetibles.
- **Historias y criterios:** sin historia propia; soporta T-04 de M2 y M3.
- **Contratos y documentos:** convenciones 5.3; modelo, sección 3.10.
- **Descripción técnica:** `CLAVE_IDEMPOTENCIA` por persona, operación y clave, con la huella de la petición, la respuesta y una caducidad configurable. Solo se guardan resultados con éxito.
- **Dependencias:** DB-01.
- **Terminado cuando:**
  - Dos peticiones simultáneas con la misma clave producen una sola fila.
  - Una clave caducada se trata como nueva.

#### DB-06 — Índices y consultas históricas
- **Prioridad:** P1 · **Capa:** Base de datos
- **Objetivo:** Hacer eficientes las consultas por equipo histórico, secuencia de avances y vista de supervisión.
- **Historias y criterios:** HU-1.4 (CA-15 a CA-21, CA-176 a CA-178, CA-212 a CA-217), HU-4.1 a HU-4.4.
- **Contratos y documentos:** M4-01 a M4-04; modelo, sección 12 (RA-01, DM-04).
- **Descripción técnica:** Índices para la función «equipo en una fecha» (persona y fechas de intervalo), para la secuencia de una actividad (fecha laboral, momento de registro, identificador) y para la auditoría por registro y fecha. Los volúmenes reales (PA-13) deciden si hace falta algo más.
- **Dependencias:** DB-01, DB-03, DB-04.
- **Terminado cuando:**
  - Los planes de ejecución de las consultas de M4-01 y M4-03 con datos de prueba usan índices.
  - Los índices no cambian ningún resultado de las pruebas de aceptación.

#### DB-07 — Datos ficticios para el flujo principal
- **Prioridad:** P0 · **Capa:** Base de datos
- **Objetivo:** Poder arrancar y demostrar el flujo principal sin datos reales.
- **Historias y criterios:** HU-1.2, HU-1.5 (preparación del flujo; sin criterios propios).
- **Contratos y documentos:** [indice.md](indice.md) (flujo FP-1); M1-02a, M1-02b.
- **Descripción técnica:** Semillas ficticias: una organización, dos equipos, un supervisor y dos colaboradores por equipo, con pertenencias vigentes. Las contraseñas se generan al ejecutar la semilla y se muestran una vez; nunca se versionan. Solo para desarrollo y demostración.
- **Dependencias:** DB-01, DB-02, DB-03.
- **Terminado cuando:**
  - Tras ejecutar la semilla, existen personas con pertenencia vigente y el supervisor de cada equipo.
  - Ningún dato sembrado corresponde a una persona real.
  - El repositorio no contiene contraseñas ni claves.
