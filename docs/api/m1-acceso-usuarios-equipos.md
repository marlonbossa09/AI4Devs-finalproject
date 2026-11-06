# SMARTWORK — Contratos de la API: M1 Autenticación, usuarios y equipos

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]`. Contratos funcionales **preliminares**: se marcan los pendientes de decisiones operativas abiertas |
| **Versión** | 0.2 |
| **Fecha** | 2026-11-06 |
| **Convenciones** | `docs/api/convenciones.md` |
| **Arquitectura de referencia** | `docs/arquitectura/adr/ADR-002-autenticacion-y-acceso.md` (arquitectura técnica aprobada como referencia; el ADR sigue PROPUESTO hasta resolver el mecanismo operativo de la provisión) |

M1 tiene dos tipos de contrato:

- **Operaciones públicas (HTTP):** iniciar sesión, cerrar sesión, consultar la sesión, completar el primer acceso y completar la recuperación. No requieren persona operadora.
- **Órdenes de provisión administrativa:** crear equipos y personas, registrar y cancelar pertenencias, desactivar el acceso y emitir códigos. **El contrato funcional (entrada, validaciones, efectos, auditoría y errores) es independiente de cómo se invoque.** La forma de invocarlas (orden en el servidor u otra) es la decisión operativa pendiente, por lo que su campo «Invocación» queda marcado como pendiente. No existe tercer rol funcional ni panel avanzado (RN-33).

Reglas comunes de las órdenes de provisión:

- Las ejecuta una persona operadora autorizada. **Tener acceso al servidor no equivale a tener autorización administrativa** (ADR-002, sección 9). Una persona operadora no es un rol funcional del producto.
- Cada orden es atómica con su entrada de auditoría (`tipo_autor` igual a provisión, con la referencia nominal de quien opera y la de la invocación; IR-24, IR-34, IR-35). Nunca se registran credenciales ni códigos.
- Una orden rechazada no modifica datos ni deja entrada.
- La «fecha actual» la calcula el servidor en la zona de la organización (DM-06).

## M1-01a — Iniciar sesión

| Campo | Contenido |
|---|---|
| **Propósito** | Identificarme con mi identificador de acceso y mi contraseña para obtener una sesión |
| **Relacionados** | HU-1.1, HU-1.7 · RF-01, RF-54, RF-106, RF-107 · RN-61, RN-64, RN-96, RN-97 |
| **Método y ruta** | `POST /api/v1/sesion` |
| **Entrada** | Cuerpo: `identificador_acceso` y `contrasena`. No requiere sesión ni token CSRF; se verifica el origen de la petición |
| **Respuesta** | 201: `persona` (`id`, `nombre`), `rol_vigente` y `csrf_token`. La cookie de sesión viaja en la cabecera de la respuesta, nunca en el cuerpo. Atributos de la cookie: `__Host-`, `Secure`, `HttpOnly`, `SameSite=Strict` (ADR-002) |
| **Validaciones** | La contraseña se verifica con Argon2id. Un identificador inexistente, una contraseña incorrecta o una identidad que aún no completó el primer acceso producen el mismo error `CREDENCIALES_INVALIDAS`, con respuesta de tiempo comparable. Si las credenciales son correctas pero el acceso está desactivado o no hay pertenencia vigente, no se crea sesión y se responde `ACCESO_DESACTIVADO` o `SIN_PERTENENCIA_VIGENTE` (CA-29, CA-255, CA-259). Cada inicio genera un identificador de sesión nuevo. Se limita el ritmo de intentos fallidos. Ninguna respuesta ni registro contiene la contraseña (CA-05) |
| **Autorización** | Pública |
| **Errores** | `CREDENCIALES_INVALIDAS` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `DEMASIADAS_SOLICITUDES` · `SOLICITUD_INVALIDA` |
| **Auditoría y transacción** | Sin entrada de auditoría de dominio. Registro técnico de eventos de autenticación, sin secretos (ADR-002, sección 13; pendiente de aprobar, A11) |
| **Criterios vinculados** | CA-05, CA-29, CA-255, CA-259 |
| **Pendientes** | Retardos y límite de intentos, y duración de la sesión (parámetros de ADR-002, A9) |

## M1-01b — Cerrar sesión

| Campo | Contenido |
|---|---|
| **Propósito** | Terminar mi sesión actual y revocarla en el servidor. Consecuencia técnica del mecanismo (ADR-002, sección 5); no tiene historia propia |
| **Relacionados** | HU-1.1 · RF-01 · RN-61 |
| **Método y ruta** | `POST /api/v1/sesion/cierre` |
| **Entrada** | Sin cuerpo. Exige el token CSRF |
| **Respuesta** | 204 y la cookie queda invalidada |
| **Validaciones** | La sesión debe estar vigente. Borrar la cookie no basta: la revocación ocurre en el servidor |
| **Autorización** | Persona con sesión |
| **Errores** | `NO_IDENTIFICADA` · `SOLICITUD_INVALIDA` |
| **Auditoría y transacción** | Sin entrada de auditoría de dominio |
| **Criterios vinculados** | CA-01 |
| **Pendientes** | Ninguno |

## M1-01c — Consultar mi sesión

| Campo | Contenido |
|---|---|
| **Propósito** | Conocer quién soy y qué puedo ver para que la interfaz presente la vista que corresponde. **Propuesta pendiente de aprobación:** ningún requisito la exige expresamente |
| **Relacionados** | HU-1.1 · RF-01, RF-02 · RN-61, RN-11 |
| **Método y ruta** | `GET /api/v1/sesion` |
| **Entrada** | Sin cuerpo |
| **Respuesta** | 200: `persona` (`id`, `nombre`), `rol_vigente` (colaborador o supervisor), `fecha_actual` en la zona de la organización y `csrf_token` |
| **Validaciones** | Sesión vigente, acceso no desactivado (IR-37) y pertenencia vigente (IR-38) |
| **Autorización** | Persona con sesión. Sin sesión no se muestra ningún dato (CA-01, CA-02) |
| **Errores** | `NO_IDENTIFICADA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` |
| **Auditoría y transacción** | Lectura |
| **Criterios vinculados** | CA-01, CA-02, CA-03, CA-04 |
| **Pendientes** | Aprobar la operación y su contenido mínimo |

## M1-03b — Completar el primer acceso

| Campo | Contenido |
|---|---|
| **Propósito** | Canjear el código de un solo uso recibido y fijar mi propia contraseña |
| **Relacionados** | HU-1.5, HU-1.1 · RF-56 · RN-35, RN-64 |
| **Método y ruta** | `POST /api/v1/acceso/primer-acceso` |
| **Entrada** | Cuerpo: `identificador_acceso`, `codigo` y `contrasena_nueva`. No requiere sesión; se verifica el origen |
| **Respuesta** | 204. No se abre sesión: la persona inicia sesión con M1-01a |
| **Validaciones** | En una sola operación atómica: el código existe, no está usado ni caducado ni invalidado y corresponde a esa identidad; el acceso no está desactivado (DD-05); la contraseña cumple la política (longitud mínima y comparación con contraseñas conocidas, ADR-002 A8); se guarda solo el hash (Argon2id); se marca el código como usado (un segundo canje falla, CA-24) y se revocan las sesiones. El código identifica únicamente a esa persona (CA-25). Cualquier fallo del código produce el mismo `CODIGO_NO_VALIDO`. Los intentos fallidos con un mismo código lo invalidan tras un número configurable |
| **Autorización** | Pública, limitada por el código |
| **Errores** | `CODIGO_NO_VALIDO` · `CONTRASENA_NO_VALIDA` · `DEMASIADAS_SOLICITUDES` · `SOLICITUD_INVALIDA` |
| **Auditoría y transacción** | Entrada de auditoría del canje, sin el código ni la contraseña, con la persona como autora |
| **Criterios vinculados** | CA-05, CA-23, CA-24, CA-25 |
| **Pendientes** | Caducidad e intentos del código (A4) y lista de contraseñas conocidas (A8); la longitud mínima está decidida: 10 caracteres (ADR-002, versión 0.4) |

## M1-09b — Completar la recuperación del acceso

| Campo | Contenido |
|---|---|
| **Propósito** | Canjear el código de recuperación emitido por la provisión y fijar una contraseña nueva |
| **Relacionados** | HU-1.6 · RF-55, RF-106 · RN-34, RN-96 |
| **Método y ruta** | `POST /api/v1/acceso/recuperacion` |
| **Entrada** | Cuerpo: `identificador_acceso`, `codigo` y `contrasena_nueva`. No requiere sesión |
| **Respuesta** | 204. No se abre sesión |
| **Validaciones** | Las de M1-03b. Además, se revocan todas las sesiones de la persona. **Si el acceso está desactivado administrativamente, el canje se rechaza con `CODIGO_NO_VALIDO` y el acceso sigue desactivado** (DD-05, CA-254): recuperar una credencial no lo reactiva |
| **Autorización** | Pública, limitada por el código |
| **Errores** | `CODIGO_NO_VALIDO` · `CONTRASENA_NO_VALIDA` · `DEMASIADAS_SOLICITUDES` · `SOLICITUD_INVALIDA` |
| **Auditoría y transacción** | Entrada de auditoría del canje, sin secretos |
| **Criterios vinculados** | CA-27, CA-254 |
| **Pendientes** | Los de M1-03b |

## M1-02a — Crear un equipo (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Crear un equipo, que nace en provisión: puede carecer de colaboradores y de supervisor |
| **Relacionados** | HU-1.5 · RF-52, RF-57, RF-108, RF-112 · RN-33, RN-34, RN-98, RN-102 |
| **Invocación** | Orden de provisión `crear-equipo`. **Forma operativa pendiente** |
| **Entrada** | `nombre` |
| **Respuesta** | El Equipo creado (`id`, `nombre`) |
| **Validaciones** | `nombre` obligatorio, con máximo configurable (D-03). El equipo recién creado puede no tener supervisor (CA-250) |
| **Autorización** | Persona operadora autorizada. Un supervisor no dispone de esta función (CA-26) |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `CAMPO_OBLIGATORIO` · `TEXTO_DEMASIADO_LARGO` |
| **Auditoría y transacción** | Una entrada de provisión (CA-251) |
| **Criterios vinculados** | CA-22, CA-26, CA-250, CA-251 |
| **Pendientes** | Si el nombre del equipo debe ser único: ninguna regla lo dice |

## M1-02b — Crear una persona con su primera pertenencia (orden de provisión)

Reúne el catálogo preliminar M1-02 (crear personas) y M1-04 (alta con primera pertenencia): una persona no existe sin pertenencia.

| Campo | Contenido |
|---|---|
| **Propósito** | Crear una persona, su identidad de acceso (sin contraseña) y su primera pertenencia |
| **Relacionados** | HU-1.2, HU-1.5 · RF-03, RF-35, RF-36, RF-52, RF-57, RF-67, RF-108, RF-112, RF-116 · RN-33, RN-94, RN-98, RN-106 |
| **Invocación** | Orden de provisión `crear-persona`. **Forma operativa pendiente** |
| **Entrada** | `nombre`, `identificador_acceso`, `equipo_id`, `rol` (colaborador o supervisor) y `desde` (primer día de la pertenencia) |
| **Respuesta** | La Persona, su Pertenencia (equipo, rol y fecha de inicio) y el indicador de que aún no tiene contraseña. Un supervisor figura como miembro del equipo que supervisa (CA-09) |
| **Validaciones** | `desde` igual o posterior a la fecha actual (`FECHA_EFECTIVA_INVALIDA`; CA-252, CA-253). No hay altas históricas (RN-106). Un colaborador exige que el equipo tenga supervisor desde `desde` (IR-32): el equipo se provisiona primero con su supervisor. Un equipo tiene como máximo un supervisor y una persona supervisa un solo equipo (CA-08, CA-10). La persona pertenece a un único equipo (CA-06, CA-07). El identificador de acceso es único. Crea persona, identidad y pertenencia en una sola operación atómica. No emite código (M1-03a) |
| **Autorización** | Persona operadora autorizada (CA-26) |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `FECHA_EFECTIVA_INVALIDA` · `PERTENENCIA_INVALIDA` · `IDENTIFICADOR_DUPLICADO` · `CAMPO_OBLIGATORIO` · `TEXTO_DEMASIADO_LARGO` |
| **Auditoría y transacción** | Una entrada de provisión (CA-251) |
| **Criterios vinculados** | CA-06, CA-07, CA-08, CA-10, CA-22, CA-251, CA-252, CA-253, CA-26, CA-09 |
| **Pendientes** | Formato del identificador de acceso |

## M1-05 — Registrar un traslado o un cambio de rol (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Cambiar a una persona de equipo o de rol con efecto a partir de una fecha futura. Acepta varios cambios en una sola operación atómica, para casos como el relevo de un supervisor |
| **Relacionados** | HU-1.2, HU-1.3, HU-1.4 · RF-35, RF-36, RF-37, RF-53, RF-104, RF-105, RF-108 · RN-28, RN-94, RN-95, RN-98 |
| **Invocación** | Orden de provisión `registrar-traslado`. **Forma operativa pendiente** |
| **Entrada** | Lista `cambios`; cada elemento: `persona_id`, `equipo_id`, `rol`, `fecha_efectiva` |
| **Respuesta** | El historial completo de pertenencias de cada persona afectada: equipos anteriores y fechas de cada una, además de las nuevas (CA-13) |
| **Validaciones** | Cada `fecha_efectiva` es posterior a la fecha actual (CA-243). Se valida la línea temporal resultante completa: sin solapes ni huecos (CA-248), un único equipo por fecha (CA-14), un supervisor exactamente mientras el equipo tenga colaboradores y como máximo uno (CA-240 a CA-242), y el supervisor pertenece al equipo que supervisa (CA-10). La persona figura en el equipo nuevo y deja de figurar en el anterior (CA-12). Los registros de la jornada actual no cambian de equipo (CA-249). Si el conjunto falla, no cambia nada |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `FECHA_EFECTIVA_INVALIDA` · `PERTENENCIA_INVALIDA` · `RECURSO_NO_DISPONIBLE` (persona o equipo inexistente) |
| **Auditoría y transacción** | Una sola entrada con los valores anterior y nuevo de todos los cambios (IR-35) |
| **Criterios vinculados** | CA-06, CA-07, CA-08, CA-10, CA-12, CA-14, CA-240, CA-241, CA-242, CA-243, CA-248, CA-249, CA-11, CA-13 |
| **Pendientes** | Ninguno propio |

## M1-06 — Finalizar una pertenencia (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Terminar la pertenencia de una persona con efecto a partir de una fecha futura, sin alterar su historial |
| **Relacionados** | HU-1.7, HU-1.2 · RF-54, RF-106, RF-107, RF-108, RF-115 · RN-38, RN-96, RN-97, RN-98, RN-105 |
| **Invocación** | Orden de provisión `finalizar-pertenencia`. **Forma operativa pendiente** |
| **Entrada** | `persona_id` y `fecha_efectiva` |
| **Respuesta** | La pertenencia resultante, con su fin |
| **Validaciones** | `fecha_efectiva` posterior a la fecha actual (CA-258). No se finaliza al único supervisor de un equipo con colaboradores sin otro supervisor desde la misma fecha (CA-240). Desde la fecha efectiva, la persona no puede registrar bitácoras (CA-257). Ningún registro se elimina ni cambia de equipo (CA-30, CA-31); la planificación posterior se conserva con su actividad y su propietaria (CA-262) |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `FECHA_EFECTIVA_INVALIDA` · `PERTENENCIA_INVALIDA` · `RECURSO_NO_DISPONIBLE` |
| **Auditoría y transacción** | Una entrada de provisión |
| **Criterios vinculados** | CA-30, CA-31, CA-240, CA-257, CA-258, CA-262 |
| **Pendientes** | Reincorporación (PA-24): no hay contrato |

## M1-07 — Cancelar o sustituir una operación programada (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Cancelar o sustituir un alta futura, un traslado, un cambio de rol o una finalización que todavía no ha surtido efecto |
| **Relacionados** | HU-1.3 · RF-37, RF-53, RF-104, RF-109 · RN-28, RN-94, RN-99 |
| **Invocación** | Orden de provisión `cancelar-operacion-programada`. **Forma operativa pendiente** |
| **Entrada** | `persona_id`, `tipo` (alta, traslado, cambio de rol o finalización), `fecha_efectiva` de la operación que se cancela y, opcionalmente, `cambios` de sustitución (como en M1-05) |
| **Respuesta** | Las pertenencias resultantes |
| **Validaciones** | La operación debe tener `fecha_efectiva` posterior a la fecha actual: una ya efectiva no se modifica (CA-245). Se valida la línea temporal resultante completa; una cancelación que dejaría a un equipo con colaboradores sin supervisor se rechaza sin cambios (CA-246). La sustitución es una sola operación atómica (CA-247). Una alta futura cancelada deja a la persona sin pertenencia (CA-278) |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `FECHA_EFECTIVA_INVALIDA` · `PERTENENCIA_INVALIDA` · `RECURSO_NO_DISPONIBLE` |
| **Auditoría y transacción** | Una entrada que conserva la operación original, su cancelación o sustitución, el autor y los valores retirados (CA-244, CA-279) |
| **Criterios vinculados** | CA-244, CA-245, CA-246, CA-247, CA-278, CA-279 |
| **Pendientes** | Ninguno propio |

## M1-08 — Desactivar el acceso de una persona (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Impedir de inmediato toda operación autenticada de una persona, sin tocar su pertenencia ni sus registros |
| **Relacionados** | HU-1.7 · RF-54, RF-106, RF-108 · RN-38, RN-96, RN-98 |
| **Invocación** | Orden de provisión `desactivar-acceso`. **Forma operativa pendiente** |
| **Entrada** | `persona_id` y `motivo` (obligatoriedad pendiente) |
| **Respuesta** | La persona con `acceso_desactivado_en` |
| **Validaciones** | Efecto inmediato, en la misma transacción que la revocación de todas sus sesiones. No se bloquea aunque la persona sea el único supervisor de un equipo (RN-98): el equipo queda pendiente de supervisión efectiva, sin transferir permisos y conservando su pertenencia histórica (CA-260, CA-261). Pertenencias, registros y visibilidad no cambian (CA-256). Desde ese momento, toda operación autenticada se rechaza (CA-255) |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `ACCESO_YA_DESACTIVADO` · `RECURSO_NO_DISPONIBLE` |
| **Auditoría y transacción** | Una entrada de provisión |
| **Criterios vinculados** | CA-255, CA-256, CA-260, CA-261 |
| **Pendientes** | Si el motivo es obligatorio; cómo se comunica la condición de equipo pendiente de supervisión efectiva (DM-09) |

## M1-03a — Emitir el código de primer acceso (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Emitir el código de un solo uso con el que una persona completa su primer acceso |
| **Relacionados** | HU-1.5 · RF-52, RF-56 · RN-34, RN-35, RN-64 |
| **Invocación** | Orden de provisión `emitir-codigo-primer-acceso`. **Forma operativa pendiente** |
| **Entrada** | `persona_id` |
| **Respuesta** | El código, mostrado **una sola vez** a la persona operadora, y su `caduca_en`. No se guarda en claro |
| **Validaciones** | La persona tiene identidad sin contraseña establecida y el acceso no está desactivado. Emitir invalida cualquier código pendiente anterior. El código es individual y de un solo uso |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `ACCESO_DESACTIVADO_ADMINISTRATIVAMENTE` · `RECURSO_NO_DISPONIBLE` · `SOLICITUD_INVALIDA` (la persona ya completó el primer acceso) |
| **Auditoría y transacción** | Una entrada de emisión, sin el código |
| **Criterios vinculados** | CA-22, CA-23 |
| **Pendientes** | **Condicionado:** medio de entrega (A6) y caducidad (A4) |

## M1-09a — Emitir el código de recuperación (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Emitir el código de un solo uso para recuperar el acceso de una persona que lo perdió |
| **Relacionados** | HU-1.6 · RF-55, RF-106 · RN-34, RN-96 |
| **Invocación** | Orden de provisión `emitir-codigo-recuperacion`. **Forma operativa pendiente** |
| **Entrada** | `persona_id` y `verificacion` (texto breve y no secreto que registra cómo se verificó la identidad) |
| **Respuesta** | El código, mostrado una sola vez, y su `caduca_en` |
| **Validaciones** | La persona tiene contraseña establecida. **Si su acceso está desactivado, no se emite** (DD-05, CA-254). Emitir invalida el código pendiente anterior. Un supervisor no dispone de esta función (CA-28) |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `ACCESO_DESACTIVADO_ADMINISTRATIVAMENTE` · `RECURSO_NO_DISPONIBLE` · `CAMPO_OBLIGATORIO` |
| **Auditoría y transacción** | Una entrada con la verificación declarada, sin el código |
| **Criterios vinculados** | CA-27, CA-28, CA-254 |
| **Pendientes** | **Condicionado:** procedimiento de verificación de identidad (A5), medio de entrega (A6) y caducidad (A4) |

## Operaciones sin contrato

| Operación | Motivo |
|---|---|
| M1-10 Reactivar un acceso desactivado | No existe regla ni historia; necesita una RN antes (ADR-002, sección 11) |
| Consulta pública del historial de pertenencias y de la composición de un equipo | No se crea. CA-09 y CA-13 se verifican con las respuestas de M1-02b y M1-05, que muestran la composición y el historial completo. Ningún requisito dice quién más los consultaría, y una operación nueva sería funcionalidad no pedida |
| Reincorporación | PA-24 |
| Altas y ajustes históricos | PA-25; no existen en el MVP |

## Decisiones pendientes que afectan a este módulo

| Id | Decisión | Afecta |
|---|---|---|
| P1 | Forma operativa de la provisión y autenticación y autorización de la persona operadora (ADR-002, sección 9) | Todas las órdenes |
| P2 | Medio de entrega de los códigos (A6) y verificación de identidad al recuperar (A5) | M1-03a, M1-09a |
| P3 | Valores de caducidad, intentos y sesión (A4, A9) | M1-01a, M1-03b, M1-09b |
| P4 | Política de contraseñas (A8) | M1-03b, M1-09b |
| P5 | Aprobar M1-01c | M1-01c |
| P6 | Unicidad del nombre de equipo; obligatoriedad del motivo de desactivación | M1-02a, M1-08 |
| P7 | Registro técnico de eventos de autenticación (A11) | M1-01a |
