# SMARTWORK — Contratos de la API: M1 Autenticación, usuarios y equipos

| Campo | Valor |
|---|---|
| **Estado** | `[PROPUESTO]`. Contratos funcionales **preliminares**: se marcan los pendientes de decisiones operativas abiertas |
| **Versión** | 0.17 |
| **Fecha** | 2026-11-17 |
| **Convenciones** | `docs/api/convenciones.md` |
| **Arquitectura de referencia** | `docs/arquitectura/adr/ADR-002-autenticacion-y-acceso.md` (arquitectura técnica aprobada como referencia; el ADR sigue PROPUESTO hasta resolver el mecanismo operativo de la provisión) |

M1 tiene dos tipos de contrato:

- **Operaciones públicas (HTTP):** iniciar sesión, cerrar sesión, consultar la sesión, completar el primer acceso y completar la recuperación. No requieren persona operadora.
- **Órdenes de provisión administrativa:** crear equipos y personas, registrar y cancelar pertenencias, desactivar el acceso y emitir códigos. **El contrato funcional (entrada, validaciones, efectos, auditoría y errores) es independiente de cómo se invoque.** **Decisión A2 (`[CONFIRMADO]`, 2026-11-11):** se invocan mediante órdenes de línea de comandos en el servidor, sin endpoints HTTP administrativos, y quien las ejecuta se identifica como persona operadora con credencial propia (A7, opción C del ADR-002). **Implementadas: M1-02a y M1-02b (M1-T2), M1-05 (M1-T3), M1-06 y M1-07 (M1-T4), M1-08 (M1-T6) y, en M1-T8.2, la emisión de códigos M1-03a y M1-09a y, en M1-T8.3 y M1-T8.4, el canje del primer acceso M1-03b y el de la recuperación M1-09b (por API, sin pantallas Flutter); en M1-T7, además, el control de intentos fallidos de M1-01a y de la credencial de la persona operadora y la orden de purga de eventos técnicos de autenticación.** Con ellas, el primer acceso y la recuperación **funcionan por API, pero todavía no tienen las pantallas previstas en T8.5**; siguen pendientes la lista de contraseñas comprometidas, la purga de códigos y la evaluación integral de seguridad (T8.6), y la reactivación del acceso (M1-10) está fuera de alcance; el plan está en [m1-plan-implementacion.md](../backlog/tickets/m1-plan-implementacion.md). No existe tercer rol funcional ni panel avanzado (RN-33).

Reglas comunes de las órdenes de provisión:

- Las ejecuta una persona operadora autorizada. **Tener acceso al servidor no equivale a tener autorización administrativa** (ADR-002, sección 9). Una persona operadora no es un rol funcional del producto.
- Cada orden es atómica con su entrada de auditoría (`tipo_autor` igual a provisión, con la referencia nominal de quien opera y la de la invocación; IR-24, IR-34, IR-35). Nunca se registran credenciales ni códigos.
- Una orden rechazada no modifica datos ni deja entrada.
- Los errores de las órdenes (con sus detalles: motivos, equipo, fecha, tipo real de una operación) se dirigen a la persona operadora autorizada y no se exponen por la API HTTP: ninguna persona sin autorización los recibe.
- Los controles de PostgreSQL que protegen la edición de pertenencias efectivas usan el reloj real de la base de datos; el reloj inyectable de la orden (D7) sirve para probar las reglas de negocio.
- Una persona sin pertenencia vigente (por ejemplo, tras una finalización efectiva) no consulta sus registros, ni siquiera los propios (IR-38, `SIN_PERTENENCIA_VIGENTE`); sus registros y su propiedad se conservan.
- La «fecha actual» la calcula el servidor en la zona de la organización (DM-06).
- **Intentos fallidos de la persona operadora (M1-T7, `[CONFIRMADO]` el 2026-11-17):** una credencial incorrecta, un identificador desconocido o una persona operadora revocada avanzan un contador PROPIO de la persona operadora (por identificador, sin origen y separado del de las personas) con la misma curva que el inicio de sesión: cinco intentos libres y, después, esperas de 30 s, 1, 2, 4, 8, 16 y 32 min y 1 hora de máximo. Durante una espera la orden termina con el código de salida 4 y `DEMASIADOS_INTENTOS` (segundos de espera en `detalles`), sin verificar la credencial, también si es correcta. El contador se olvida tras 24 horas sin nuevos intentos y un acierto lo reinicia. **Nunca se deshabilita a la persona operadora**: las esperas caducan solas. La respuesta es la misma para un identificador desconocido y para una credencial incorrecta, y ninguna credencial aparece en argumentos, salidas, contadores ni eventos. La identificación se confirma en transacciones propias y cortas (no hay transacción abierta mientras se calcula Argon2).
- **Purga de códigos de un solo uso terminados (`purgar-codigos`, M1-T8.6, `[CONFIRMADO]` el 2026-11-17, D6):** orden de la CLI, con identificación de la persona operadora, que borra los códigos usados, invalidados o caducados que terminaron hace 30 días o más, con el reloj de PostgreSQL, y devuelve cuántos purgó, sin códigos, hashes ni personas. Nunca borra un código pendiente y vigente ni uno más reciente (la base de datos lo impide además a cualquier rol), no toca la auditoría funcional y es repetible. **No hay planificador: nada la ejecuta sola** (DT-07).
- **Purga de eventos técnicos de autenticación (`purgar-eventos-autenticacion`, M1-T7, `[CONFIRMADO]` el 2026-11-17):** orden de la CLI, con identificación de la persona operadora, que borra los eventos técnicos de autenticación anteriores a la retención (30 días como mínimo; parámetro `AUTH_EVENT_RETENTION_DAYS`) y devuelve cuántos purgó, sin contenido. La base de datos impide además borrar un evento de menos de 30 días a cualquier rol. **No hay planificador: nada la ejecuta sola**; hasta que el despliegue (DT-07) decida cómo programarla hay que lanzarla periódicamente. No toca la auditoría funcional, los contadores ni las sesiones. Su retención general sigue pendiente de PA-06.

## M1-01a — Iniciar sesión

| Campo | Contenido |
|---|---|
| **Propósito** | Identificarme con mi identificador de acceso y mi contraseña para obtener una sesión |
| **Relacionados** | HU-1.1, HU-1.7 · RF-01, RF-54, RF-106, RF-107 · RN-61, RN-64, RN-96, RN-97 |
| **Método y ruta** | `POST /api/v1/sesion` |
| **Entrada** | Cuerpo: `identificador_acceso` y `contrasena`. No requiere sesión ni token CSRF; se verifica el origen de la petición |
| **Respuesta** | 201: `persona` (`id`, `nombre`), `rol_vigente` y `csrf_token`. La cookie de sesión viaja en la cabecera de la respuesta, nunca en el cuerpo. Atributos de la cookie: `__Host-`, `Secure`, `HttpOnly`, `SameSite=Strict` (ADR-002). **429 `DEMASIADAS_SOLICITUDES` (M1-T7):** sin cookie y con `Cache-Control: no-store`; la cabecera `Retry-After` lleva los segundos de espera (entero, como mínimo 1) y los mismos segundos van en `detalles` (`espera_segundos`); el mensaje es fijo y no revela si el identificador existe ni cuántos intentos quedan |
| **Validaciones** | La contraseña se verifica con Argon2id. Un identificador inexistente, una contraseña incorrecta o una identidad que aún no completó el primer acceso producen el mismo error `CREDENCIALES_INVALIDAS`, con respuesta de tiempo comparable. Si las credenciales son correctas pero el acceso está desactivado o no hay pertenencia vigente, no se crea sesión y se responde `ACCESO_DESACTIVADO` o `SIN_PERTENENCIA_VIGENTE` (CA-29, CA-255, CA-259). Cada inicio genera un identificador de sesión nuevo. **Control de intentos fallidos (M1-T7, `[CONFIRMADO]` el 2026-11-17; ADR-002, A9 y A11):** antes de calcular Argon2 se RESERVA el intento de forma atómica, en una transacción propia y corta (sin transacción ni bloqueo abiertos mientras se verifica el hash). El contador es por identificador normalizado y origen (HMAC de ambos, nunca en claro); la reserva cuenta el intento como fallido y solo una autenticación COMPLETA (contraseña correcta, acceso habilitado y pertenencia vigente) la devuelve y reinicia el contador, en la misma transacción que crea la sesión (`[CONFIRMADO]` el 2026-11-17): con las credenciales correctas pero el acceso desactivado o sin pertenencia vigente se responde `ACCESO_DESACTIVADO` o `SIN_PERTENENCIA_VIGENTE` sin reiniciar el contador y el intento sigue contando. Cinco intentos libres; después, el intento siguiente espera 30 s y la espera se duplica (1, 2, 4, 8, 16 y 32 min) hasta 1 hora de máximo. Durante la espera, TAMBIÉN con credenciales correctas, la respuesta es 429 `DEMASIADAS_SOLICITUDES` con `Retry-After`, sin verificar la contraseña y con la misma respuesta para un identificador que existe y para otro que no; una petición denegada no cambia ningún contador (no prolonga la espera). El contador se olvida tras 24 horas sin nuevos intentos. Límites por origen (intentos fallidos; cada acierto devuelve su reserva): 30 en 5 minutos y 200 en 1 hora, configurables. Nada es permanente: todo caduca solo. El origen es la dirección de la conexión; `X-Forwarded-For` solo se acepta de un proxy expresamente configurado como de confianza (DT-07). La sesión dura como máximo 24 horas y caduca tras 1 hora de inactividad (configurables). Ninguna respuesta ni registro contiene la contraseña (CA-05). **Desactivación concurrente (M1-T6):** tras verificar las credenciales, el inicio de sesión toma el bloqueo de la persona que también toma la orden de desactivar el acceso y comprueba el acceso con el instante real, de modo que una carrera con una desactivación no deja ninguna sesión válida |
| **Autorización** | Pública |
| **Errores** | `CREDENCIALES_INVALIDAS` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` · `DEMASIADAS_SOLICITUDES` · `SOLICITUD_INVALIDA` |
| **Auditoría y transacción** | Sin entrada de auditoría de dominio. Registro técnico de eventos de autenticación, sin secretos y separado de la auditoría de dominio (ADR-002, A11; `[CONFIRMADO]` el 2026-11-17; implementado en M1-T7): inicio correcto, inicio fallido, espera aplicada (una vez por espera, no por cada 429), cierre de sesión, acceso desactivado durante la autenticación y revocación por desactivación. Solo anexado; guarda HMAC del identificador y del origen, identificadores internos y datos fijados por el código; nunca contraseñas, cookies, tokens ni identificadores en claro. Retención técnica inicial de 30 días con la orden `purgar-eventos-autenticacion`; PA-06 general sigue pendiente |
| **Criterios vinculados** | CA-05, CA-29, CA-255, CA-259 |
| **Pendientes** | **No implementado: el tope agregado de 100 fallos por cuenta con deshabilitación automática de la contraseña** (A9; desviación temporal registrada, a revisar con la recuperación segura de M1-T8: no se declara resuelto el requisito agregado por el contador por cuenta y origen). Riesgos abiertos: ataques distribuidos, configuración del proxy para AWS ECS (DT-07), retención general de eventos y auditoría (PA-06) y recuperación de contraseña (M1-T8) |

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
| **Propósito** | Conocer quién soy y qué puedo ver para que la interfaz presente la vista que corresponde. Propuesta aprobada por la persona responsable e implementada (el cliente recibe el rol y la fecha actual del servidor) |
| **Relacionados** | HU-1.1 · RF-01, RF-02 · RN-61, RN-11 |
| **Método y ruta** | `GET /api/v1/sesion` |
| **Entrada** | Sin cuerpo |
| **Respuesta** | 200: `persona` (`id`, `nombre`), `rol_vigente` (colaborador o supervisor), `fecha_actual` en la zona de la organización y `csrf_token` |
| **Validaciones** | Sesión vigente, acceso no desactivado (IR-37) y pertenencia vigente (IR-38) |
| **Autorización** | Persona con sesión. Sin sesión no se muestra ningún dato (CA-01, CA-02) |
| **Errores** | `NO_IDENTIFICADA` · `ACCESO_DESACTIVADO` · `SIN_PERTENENCIA_VIGENTE` |
| **Auditoría y transacción** | Lectura |
| **Criterios vinculados** | CA-01, CA-02, CA-03, CA-04 |
| **Pendientes** | Ninguno: aprobada con su contenido actual |

## M1-03b — Completar el primer acceso

| Campo | Contenido |
|---|---|
| **Propósito** | Canjear el código de un solo uso recibido y fijar mi propia contraseña |
| **Relacionados** | HU-1.5, HU-1.1 · RF-56 · RN-35, RN-64 |
| **Método y ruta** | `POST /api/v1/acceso/primer-acceso` |
| **Entrada** | Cuerpo: `identificador_acceso`, `codigo` y `contrasena_nueva`. No requiere sesión; se verifica el origen |
| **Respuesta** | 204 sin cuerpo y con `Cache-Control: no-store`. No se abre sesión: la persona inicia sesión con M1-01a. **Implementada en M1-T8.3**; pantalla Flutter en M1-T8.5 (se abre desde el inicio de sesión y, al canjear, vuelve a él con un aviso sin abrir sesión) |
| **Validaciones** | En una sola operación atómica: el código existe, no está usado ni caducado ni invalidado y corresponde a esa identidad; el acceso no está desactivado (DD-05); la contraseña cumple la política (longitud mínima y comparación con contraseñas conocidas, ADR-002 A8); se guarda solo el hash (Argon2id); se marca el código como usado (un segundo canje falla, CA-24) y se revocan las sesiones. El código identifica únicamente a esa persona (CA-25). Cualquier fallo del código (desconocido, usado, caducado, invalidado, de otra persona, de una identidad que ya tiene contraseña o de un acceso desactivado) produce el mismo `CODIGO_NO_VALIDO` (400, mensaje y detalles fijos). Los intentos fallidos con un mismo código lo invalidan a los 10 (A4). **Orden (M1-T8.3):** origen y forma (400, sin contar intentos) → control de intentos de M1-T7 con dominio de canje propio (429 con `Retry-After`) → política de contraseña (`CONTRASENA_NO_VALIDA`, 422, que NO consume el código y NO depende de que el código sea válido) → canje atómico en una función de la base. La contraseña se guarda con Argon2id y se fija `contrasena_establecida_en`; se revocan las sesiones de la persona. Dos canjes simultáneos del mismo código dejan exactamente uno efectivo; el canje respeta el bloqueo por persona del inicio de sesión y la desactivación. Un canje efectivo reinicia el contador de intentos del canje |
| **Autorización** | Pública, limitada por el código |
| **Errores** | `CODIGO_NO_VALIDO` · `CONTRASENA_NO_VALIDA` · `DEMASIADAS_SOLICITUDES` · `SOLICITUD_INVALIDA` |
| **Auditoría y transacción** | Una entrada de auditoría atómica con el canje: operación `entrega_acceso`, fase `canje`, la persona como autora y afectada y la finalidad; sin el código, su hash ni la contraseña. Distinta de la entrada de emisión |
| **Criterios vinculados** | CA-05, CA-23, CA-24, CA-25 |
| **Pendientes** | Implementados los puntos decididos el 2026-11-17 (A3, A4, A8, D5, D7). **Contraseñas comprometidas (M1-T8.6):** comprobación local contra Pwned Passwords de Have I Been Pwned (`[CONFIRMADO]` el 2026-11-17): el SHA-1 de la contraseña nueva se busca en el conjunto instalado en el servidor (sin enviar nada a servicios externos); si figura, `CONTRASENA_NO_VALIDA` con el motivo `comprometida`, antes de mirar el código y sin consumirlo. **Solo actúa en un despliegue que haya instalado el conjunto completo** (unos 81 GB; `docs/operacion/pwned-passwords.md`); sin él la comprobación está inactiva y solo rige la longitud mínima. La pantalla está implementada (T8.5). Ver los riesgos en ADR-002 (M1-T8.3) |

## M1-09b — Completar la recuperación del acceso

| Campo | Contenido |
|---|---|
| **Propósito** | Canjear el código de recuperación emitido por la provisión y fijar una contraseña nueva |
| **Relacionados** | HU-1.6 · RF-55, RF-106 · RN-34, RN-96 |
| **Método y ruta** | `POST /api/v1/acceso/recuperacion` |
| **Entrada** | Cuerpo: `identificador_acceso`, `codigo` y `contrasena_nueva`. No requiere sesión |
| **Respuesta** | 204 sin cuerpo y con `Cache-Control: no-store`. No se abre sesión. **Implementada en M1-T8.4**; pantalla Flutter en M1-T8.5 (se abre desde el inicio de sesión y, al canjear, vuelve a él con un aviso sin abrir sesión) |
| **Validaciones** | Las de M1-03b (origen y forma; control de intentos de M1-T7 con el dominio de canje; política de contraseña ANTES del código y sin consumirlo; canje atómico en una función de la base; 10 intentos fallidos invalidan el código; el mismo `CODIGO_NO_VALIDO` para cualquier código no válido, también el de otra finalidad). Además: la identidad debe TENER contraseña (si no, es un primer acceso), el hash se cambia y se renueva `contrasena_establecida_en`, y se revocan TODAS las sesiones de la persona en la misma transacción. **Si el acceso está desactivado administrativamente, el canje se rechaza con `CODIGO_NO_VALIDO` y el acceso sigue desactivado** (DD-05, CA-254): recuperar una credencial no lo reactiva |
| **Autorización** | Pública, limitada por el código |
| **Errores** | `CODIGO_NO_VALIDO` · `CONTRASENA_NO_VALIDA` · `DEMASIADAS_SOLICITUDES` · `SOLICITUD_INVALIDA` |
| **Auditoría y transacción** | Una entrada atómica con el canje: operación `recuperacion_acceso`, fase `canje`, la persona como autora y afectada, la finalidad y el número de sesiones revocadas; sin el código, su hash ni las contraseñas. Distinta de la entrada de emisión. Si falla cualquier parte, no se consume el código, no se cambia la contraseña y no se revoca ninguna sesión |
| **Criterios vinculados** | CA-27, CA-254 |
| **Pendientes** | Implementada con los mismos pendientes que M1-03b: comprobación de contraseñas comprometidas con Pwned Passwords local (T8.6), activa solo con el conjunto instalado. La pantalla está implementada (T8.5). La reactivación del acceso no forma parte de este contrato |

## M1-02a — Crear un equipo (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Crear un equipo, que nace en provisión: puede carecer de colaboradores y de supervisor |
| **Relacionados** | HU-1.5 · RF-52, RF-57, RF-108, RF-112 · RN-33, RN-34, RN-98, RN-102 |
| **Invocación** | Orden de provisión `crear-equipo`: `uv run python -m scripts.provision crear-equipo --operador … --organizacion … --nombre …` (CLI del servidor, A2 `[CONFIRMADO]` el 2026-11-11). **Implementada en M1-T2** |
| **Entrada** | `organizacion_id` (una organización existente) y `nombre` |
| **Respuesta** | El Equipo creado (`id`, `nombre`) |
| **Validaciones** | `nombre` obligatorio, con máximo configurable (D-03). El equipo recién creado puede no tener supervisor (CA-250) |
| **Autorización** | Persona operadora autorizada. Un supervisor no dispone de esta función (CA-26) |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `CAMPO_OBLIGATORIO` · `TEXTO_DEMASIADO_LARGO` · `NOMBRE_DE_EQUIPO_DUPLICADO` (P6) · `RECURSO_NO_DISPONIBLE` (organización inexistente) |
| **Auditoría y transacción** | Una entrada de provisión (CA-251) |
| **Criterios vinculados** | CA-22, CA-26, CA-250, CA-251 |
| **Aplicación (M1-T2)** | El nombre se recorta (espacio, tabulador y saltos de línea exteriores) y se compara sin distinguir mayúsculas; no se quitan acentos ni espacios interiores. La unicidad por organización la garantizan el servicio y un índice único en la base. Una sola transacción con una entrada de auditoría `alta` (`tipo_objeto` `equipo`, sin propietaria de registro) que identifica a la persona operadora. Resultado de la CLI: identificadores y nombre en JSON, sin secretos. La organización debe existir: **crear una organización no tiene contrato** (ver «Operaciones sin contrato») |
| **Pendientes** | Ninguno. **P6 (`[CONFIRMADO]`, 2026-11-11):** el nombre de un equipo es único por organización; el criterio de comparación (mayúsculas, espacios extremos) se fijará al implementarlo |

## M1-02b — Crear una persona con su primera pertenencia (orden de provisión)

Reúne el catálogo preliminar M1-02 (crear personas) y M1-04 (alta con primera pertenencia): una persona no existe sin pertenencia.

| Campo | Contenido |
|---|---|
| **Propósito** | Crear una persona, su identidad de acceso (sin contraseña) y su primera pertenencia |
| **Relacionados** | HU-1.2, HU-1.5 · RF-03, RF-35, RF-36, RF-52, RF-57, RF-67, RF-108, RF-112, RF-116 · RN-33, RN-94, RN-98, RN-106 |
| **Invocación** | Orden de provisión `crear-persona`: `uv run python -m scripts.provision crear-persona --operador … --nombre … --identificador-acceso … --equipo … --rol … --desde …` (CLI del servidor, A2 `[CONFIRMADO]` el 2026-11-11). **Implementada en M1-T2** |
| **Entrada** | `nombre`, `identificador_acceso`, `equipo_id`, `rol` (colaborador o supervisor) y `desde` (primer día de la pertenencia) |
| **Respuesta** | La Persona, su Pertenencia (equipo, rol y fecha de inicio) y el indicador de que aún no tiene contraseña. Un supervisor figura como miembro del equipo que supervisa (CA-09) |
| **Validaciones** | `desde` igual o posterior a la fecha actual (`FECHA_EFECTIVA_INVALIDA`; CA-252, CA-253). No hay altas históricas (RN-106). Un colaborador exige que el equipo tenga supervisor desde `desde` (IR-32): el equipo se provisiona primero con su supervisor. Un equipo tiene como máximo un supervisor y una persona supervisa un solo equipo (CA-08, CA-10). La persona pertenece a un único equipo (CA-06, CA-07). El identificador de acceso es único. Crea persona, identidad y pertenencia en una sola operación atómica. No emite código (M1-03a) |
| **Autorización** | Persona operadora autorizada (CA-26) |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `FECHA_EFECTIVA_INVALIDA` · `PERTENENCIA_INVALIDA` · `IDENTIFICADOR_DUPLICADO` · `CAMPO_OBLIGATORIO` · `TEXTO_DEMASIADO_LARGO` · `RECURSO_NO_DISPONIBLE` (equipo inexistente) |
| **Auditoría y transacción** | Una entrada de provisión (CA-251) |
| **Criterios vinculados** | CA-06, CA-07, CA-08, CA-10, CA-22, CA-251, CA-252, CA-253, CA-26, CA-09 |
| **Aplicación (M1-T2)** | La «fecha actual» se mide en la zona horaria de la organización del equipo con un reloj inyectable (D7), solo en los casos de uso: la CLI no tiene ninguna opción para fijarla. Un colaborador exige supervisión sin huecos y sin fin desde `desde` (IR-32); un supervisor no puede solapar con otro del equipo (IR-03); la base lo garantiza además con sus restricciones. La identidad se crea **sin contraseña** y no se emite ningún código: **la persona todavía no puede iniciar sesión** hasta que existan M1-03a y M1-03b (por eso CA-22 queda parcial). La entrada de auditoría (`tipo_objeto` `persona`) no contiene credenciales ni el identificador de acceso. La CLI no devuelve el identificador de acceso |
| **Pendientes** | Formato del identificador de acceso |

## M1-05 — Registrar un traslado o un cambio de rol (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Cambiar a una persona de equipo o de rol con efecto a partir de una fecha futura. Acepta varios cambios en una sola operación atómica, para casos como el relevo de un supervisor |
| **Relacionados** | HU-1.2, HU-1.3, HU-1.4 · RF-35, RF-36, RF-37, RF-53, RF-104, RF-105, RF-108 · RN-28, RN-94, RN-95, RN-98 |
| **Invocación** | Orden de provisión `registrar-traslado`: `uv run python -m scripts.provision registrar-traslado --operador … --cambio PERSONA:EQUIPO:ROL:AAAA-MM-DD [--cambio …]` (CLI del servidor, A2 `[CONFIRMADO]` el 2026-11-11). **Implementada en M1-T3** |
| **Entrada** | Lista `cambios`, una opción `--cambio` por elemento; cada elemento: `persona_id`, `equipo_id`, `rol` y `fecha_efectiva`, con el sentido «desde `fecha_efectiva` la persona pertenece a `equipo_id` con ese `rol`». Un traslado cambia el equipo, un cambio de rol cambia el rol y ambos pueden ir juntos |
| **Respuesta** | Por cada cambio, su tipo (`traslado`, `cambio_de_rol` o `traslado_y_cambio_de_rol`) y, por cada persona afectada, su historial completo de pertenencias: equipos anteriores y fechas de cada una, además de las nuevas (CA-13) |
| **Validaciones** | Cada `fecha_efectiva` es posterior a la fecha actual de la organización (CA-243). Una persona figura una sola vez por operación. Solo se cierra el último intervalo sin fin de la persona y se abre otro en la `fecha_efectiva`, que además es posterior al inicio de ese intervalo; **ningún intervalo existente se modifica ni se borra** (IR-30, CA-249). Se valida la línea temporal resultante completa: sin solapes ni huecos (CA-248), un único equipo por fecha (CA-14), un supervisor exactamente mientras el equipo tenga colaboradores y como máximo uno, en toda fecha posterior a la efectiva (CA-240 a CA-242), y el supervisor pertenece al equipo que supervisa (CA-10). La persona figura en el equipo nuevo y deja de figurar en el anterior (CA-12). Los registros de la jornada actual no cambian de equipo (CA-249). El equipo de destino pertenece a la misma organización. Un cambio que no varía ni el equipo ni el rol se rechaza. Una persona sin pertenencia, o cuya pertenencia ya está finalizada, no se traslada (PA-24, PA-31). Si el conjunto falla, no cambia nada |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `FECHA_EFECTIVA_INVALIDA` · `PERTENENCIA_INVALIDA` · `RECURSO_NO_DISPONIBLE` (persona o equipo inexistente) · `SOLICITUD_INVALIDA` (formato, persona repetida) · `CAMPO_OBLIGATORIO` (sin cambios) |
| **Auditoría y transacción** | Una sola entrada con los valores anterior y nuevo de todos los cambios (IR-35) |
| **Criterios vinculados** | CA-06, CA-07, CA-08, CA-10, CA-12, CA-14, CA-240, CA-241, CA-242, CA-243, CA-248, CA-249, CA-11, CA-13 |
| **Aplicación (M1-T3)** | La «fecha actual» se mide en la zona horaria de la organización del equipo de destino con el reloj inyectable (D7), solo en los casos de uso: la CLI no tiene ninguna opción para fijarla. Los motivos de `PERTENENCIA_INVALIDA` se informan en `detalles` con el índice del cambio (`indice`) o, para la supervisión, el equipo y la primera fecha que incumple (`equipo`, `fecha`): `sin_cambio`, `sin_pertenencia`, `pertenencia_finalizada`, `otra_organizacion`, `rol_no_valido`, `fecha_no_posterior_al_inicio_de_la_ultima_pertenencia`, `el_equipo_quedaria_sin_supervisor` y `el_equipo_tendria_mas_de_un_supervisor`. Se aplican primero todos los cierres y después todas las aperturas, en una sola transacción. Las órdenes que tocan las mismas personas o equipos se serializan con bloqueos consultivos tomados siempre en el mismo orden (el bloqueo de equipo es el de `crear-persona`); las restricciones de exclusión de la base de datos y, solo para el rol de provisión, un disparador diferido de IR-03 e IR-32 y otro que impide modificar un intervalo ya cerrado son la garantía final. La entrada de auditoría tiene `operacion` `cambio_pertenencia`, `tipo_objeto` `operacion_de_pertenencia`, como objeto la invocación de la orden y sin propietaria de registro, porque la operación afecta a varias personas y equipos; contiene, por cada cambio, la pertenencia cerrada y la nueva, y no contiene credenciales ni identificadores de acceso |
| **Pendientes** | Ninguno propio. **PA-31 (`[CONFIRMADO]`, 2026-11-11):** M1-05 exige una pertenencia previa y no se amplía para asignar la primera pertenencia a una persona ya creada que carece de toda pertenencia; M1-02b es la operación ordinaria para crear una persona con su pertenencia inicial. CA-11 queda parcial en el alcance que todavía no puede verificarse |

## M1-06 — Finalizar una pertenencia (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Terminar la pertenencia de una persona con efecto a partir de una fecha futura, sin alterar su historial |
| **Relacionados** | HU-1.7, HU-1.2 · RF-54, RF-106, RF-107, RF-108, RF-115 · RN-38, RN-96, RN-97, RN-98, RN-105 |
| **Invocación** | Orden de provisión `finalizar-pertenencia`: `uv run python -m scripts.provision finalizar-pertenencia --operador … --finalizar PERSONA:AAAA-MM-DD [--finalizar …] [--cambio PERSONA:EQUIPO:ROL:AAAA-MM-DD …]` (CLI del servidor, A2 `[CONFIRMADO]` el 2026-11-11). **Implementada en M1-T4** |
| **Entrada** | `persona_id` y `fecha_efectiva` (una opción `--finalizar` por persona; una orden puede finalizar a varias en una sola operación atómica). **Precisión de la implementación:** admite además `cambios` (como en M1-05) en la misma operación, para registrar a quien releva a un supervisor que se finaliza (sin ello, CA-240 impediría finalizar al único supervisor de un equipo con colaboradores, porque el relevo solo es válido si ocurre en la misma operación) |
| **Respuesta** | La operación (`finalizacion_pertenencia`), las finalizaciones y cambios registrados y el historial completo de pertenencias de cada persona afectada, con su fin |
| **Validaciones** | `fecha_efectiva` posterior a la fecha actual de la organización (CA-258) y al inicio del último intervalo de la persona. La persona tiene un último intervalo sin fin: una persona sin pertenencia o ya finalizada (también con una finalización programada) se rechaza, y una finalización se reprograma con M1-07 (PA-24: sin reincorporación). Se valida la línea temporal resultante completa: no se finaliza al único supervisor de un equipo con colaboradores sin otro supervisor desde la misma fecha efectiva (CA-240). Desde la fecha efectiva, la persona no puede registrar bitácoras (CA-257). Ningún registro se elimina ni cambia de equipo (CA-30, CA-31); la planificación posterior se conserva con su actividad y su propietaria (CA-262). Si el conjunto falla, no cambia nada |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `FECHA_EFECTIVA_INVALIDA` · `PERTENENCIA_INVALIDA` · `RECURSO_NO_DISPONIBLE` · `SOLICITUD_INVALIDA` (formato, persona repetida) · `CAMPO_OBLIGATORIO` (sin finalizaciones) |
| **Auditoría y transacción** | Una entrada de provisión `finalizacion_pertenencia` con los valores anterior y nuevo de todo lo afectado |
| **Criterios vinculados** | CA-30, CA-31, CA-240, CA-257, CA-258, CA-262 |
| **Aplicación (M1-T4)** | La finalización cierra el último intervalo sin fin y no abre otro (IR-31). Motor común con M1-07: misma validación de línea temporal, mismos bloqueos y misma forma de auditoría (`valor_anterior` y `valor_nuevo` con los fines anteriores y nuevos, las pertenencias retiradas y las nuevas). El historial efectivo no se modifica nunca; la base de datos lo garantiza además para el rol de provisión (migración 0011). Los motivos de `PERTENENCIA_INVALIDA` son los de M1-05 más `pertenencia_finalizada` |
| **Pendientes** | Reincorporación (PA-24): no hay contrato |

## M1-07 — Cancelar o sustituir una operación programada (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Cancelar o sustituir un alta futura, un traslado, un cambio de rol o una finalización que todavía no ha surtido efecto |
| **Relacionados** | HU-1.3 · RF-37, RF-53, RF-104, RF-109 · RN-28, RN-94, RN-99 |
| **Invocación** | Orden de provisión `cancelar-operacion-programada`: `uv run python -m scripts.provision cancelar-operacion-programada --operador … --cancelar PERSONA:TIPO:AAAA-MM-DD [--cancelar …] [--cambio PERSONA:EQUIPO:ROL:AAAA-MM-DD …] [--finalizar PERSONA:AAAA-MM-DD …]` (CLI del servidor, A2 `[CONFIRMADO]` el 2026-11-11). **Implementada en M1-T4** |
| **Entrada** | La operación que se cancela, identificada por `persona_id`, `tipo` (`alta`, `traslado`, `cambio_de_rol`, `traslado_y_cambio_de_rol` o `finalizacion`) y `fecha_efectiva`; y, opcionalmente, las operaciones de sustitución: `cambios` (como en M1-05) y finalizaciones (como en M1-06). **Precisiones de la implementación:** una orden puede cancelar varias operaciones (IR-39: las operaciones relacionadas, como un relevo, se cancelan o sustituyen juntas); el `tipo` debe coincidir con el que se deduce de los intervalos de la persona (si no, se informa el `tipo_real`); y la sustitución admite finalizaciones para poder reprogramar una finalización |
| **Respuesta** | Las operaciones canceladas, las nuevas y el historial completo de pertenencias de cada persona afectada |
| **Validaciones** | La operación debe tener `fecha_efectiva` posterior a la fecha actual: una ya efectiva no se modifica (CA-245). Cancelar retira el intervalo programado y restituye el fin del intervalo anterior (IR-39). **Solo se cancela un sufijo de las operaciones programadas de una persona:** una operación de la que dependen otras posteriores no se cancela sola (S-13); las posteriores se cancelan en la misma orden y, si se quieren conservar, se vuelven a registrar en ella (sustituir). Se valida la línea temporal resultante completa; una cancelación que dejaría a un equipo con colaboradores sin supervisor, o con dos supervisores, se rechaza sin cambios (CA-246, S-19; cancelar un relevo exige cancelar sus dos mitades juntas, S-20). La sustitución es una sola operación atómica (CA-247). Una alta futura cancelada deja a la persona sin pertenencia, sin poder operar, y la persona se conserva (CA-278). Un cambio de rol programado cancelado conserva el rol (CA-279) |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `FECHA_EFECTIVA_INVALIDA` · `PERTENENCIA_INVALIDA` · `RECURSO_NO_DISPONIBLE` (persona, equipo u operación inexistente) · `SOLICITUD_INVALIDA` (formato, operación repetida, tipo que no coincide) · `CAMPO_OBLIGATORIO` |
| **Auditoría y transacción** | Una entrada que conserva la operación original, su cancelación o sustitución, el autor y los valores retirados (CA-244, CA-279) |
| **Criterios vinculados** | CA-244, CA-245, CA-246, CA-247, CA-278, CA-279 |
| **Aplicación (M1-T4)** | Entrada de provisión `cancelacion_operacion`, o `sustitucion_operacion` si la orden registra operaciones nuevas, con el objeto y la propietaria nula de M1-05. `valor_anterior` conserva las pertenencias retiradas completas (equipo, rol, inicio y fin) y los fines anteriores restituidos; `valor_nuevo`, los fines restituidos, las operaciones nuevas y las pertenencias nuevas. **La entrada de la operación original no se toca** (la auditoría es de solo anexado): se identifica por el identificador de la pertenencia retirada, presente en el `valor_nuevo` de su propia entrada (una alta de M1-02b, por la persona y la fecha de inicio). **Unicidad del enlace (probada en M1-T5, `test_enlace_auditoria.py`):** cada pertenencia programada la crea una sola entrada de auditoría (un traslado, una sustitución, una finalización con relevo o, para el alta, la única entrada de alta de esa persona). **Caso ambiguo documentado:** el fin de una finalización que se registra, se cancela y se vuelve a registrar con la misma fecha en el mismo intervalo lo fijan dos entradas; la original de una cancelación es la más reciente anterior a ella (se desambigua por el orden, no por un identificador propio). **Antes de producción hacen falta identificadores explícitos de la operación original** en cada entrada de cancelación o sustitución; el enlace actual se conserva solo de forma provisional. Resolverlo con datos exigiría que la orden leyera la auditoría, lo que el rol de provisión no puede. La base de datos permite al rol de provisión borrar solo un intervalo que todavía no ha empezado y cambiar el fin de un intervalo solo cuando el fin actual y el nuevo son posteriores a hoy (la única excepción de IR-26) |
| **Pendientes** | Ninguno propio |

## M1-08 — Desactivar el acceso de una persona (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Impedir de inmediato toda operación autenticada de una persona, sin tocar su pertenencia ni sus registros |
| **Relacionados** | HU-1.7 · RF-54, RF-106, RF-108 · RN-38, RN-96, RN-98 |
| **Invocación** | Orden de provisión `desactivar-acceso`: `uv run python -m scripts.provision desactivar-acceso --operador … --persona … --motivo "…"` (CLI del servidor, A2 `[CONFIRMADO]` el 2026-11-11). **Implementada en M1-T6** |
| **Entrada** | `persona_id` y `motivo` (obligatorio: P6, `[CONFIRMADO]`, 2026-11-11; recortado, con el máximo configurable de texto largo). **Provisionalmente el motivo es un argumento de la CLI** (decisión del 2026-11-17): debe ser un texto breve y **sin datos sensibles**, porque queda visible en la lista de procesos y en el historial del intérprete de órdenes y se conserva en la auditoría |
| **Respuesta** | La persona, el instante de la desactivación (`acceso_desactivado_en`), las sesiones revocadas y las **advertencias de supervisión efectiva** (DM-09): una por cada equipo que queda pendiente, con su identificador, nombre, número de colaboradores en la fecha actual, supervisor asignado y fecha en que termina su asignación si ya hay un relevo programado. No se repite el motivo (**`[CONFIRMADO]` el 2026-11-17**: la advertencia estructurada de DM-09 forma parte del resultado y el motivo se registra en la auditoría, no en la salida normal de la CLI) |
| **Validaciones** | Efecto inmediato, en la misma transacción que la revocación de todas sus sesiones. **No se bloquea aunque la persona sea el único supervisor de un equipo (RN-98, DD-04; aprobado por la persona responsable el 2026-11-17):** si deja a un equipo con colaboradores en la fecha actual cuyo supervisor asignado ya no tiene acceso efectivo, el equipo queda pendiente de supervisión efectiva y se informa con la advertencia; no se modifica ninguna pertenencia, no se asigna ningún supervisor sustituto, no se transfieren permisos (RA-12) y no se crea ningún estado persistente (la condición se calcula con las reglas de supervisión, CA-260, CA-261). Pertenencias, registros y visibilidad no cambian (CA-256). Desde ese momento, toda operación autenticada se rechaza, también la de las sesiones ya emitidas (CA-255), y no se puede iniciar una sesión nueva (CA-29). Una persona inexistente se rechaza; **una solicitud repetida sobre un acceso ya desactivado se rechaza de forma explícita (`ACCESO_YA_DESACTIVADO`), sin cambios ni nueva entrada de auditoría** (`[CONFIRMADO]` el 2026-11-17) |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `CAMPO_OBLIGATORIO` (motivo vacío o ausente) · `TEXTO_DEMASIADO_LARGO` · `ACCESO_YA_DESACTIVADO` · `RECURSO_NO_DISPONIBLE` · `SOLICITUD_INVALIDA` (formato del identificador) |
| **Auditoría y transacción** | Una entrada de provisión `desactivacion_acceso` con el motivo, el valor anterior (`acceso_desactivado_en` nulo), el nuevo, las sesiones revocadas y las advertencias de supervisión. Atómica con el efecto: si falla, no se desactiva nada ni se revoca ninguna sesión |
| **Criterios vinculados** | CA-255, CA-256, CA-260, CA-261 |
| **Aplicación (M1-T6)** | El instante lo pone la base de datos (`now()`); el reloj inyectable de la orden solo fija la «fecha actual» de las advertencias. La orden toma el bloqueo consultivo de la persona que también toma el inicio de sesión y, después, los de pertenencias, siempre en el mismo orden (sin bloqueos mutuos). El servidor comprueba el acceso en cada petición con el instante real de la comprobación, no con el inicio de la transacción: así una carrera entre un inicio de sesión y la desactivación no deja ninguna sesión válida. La condición «equipo pendiente de supervisión efectiva» (DM-09: colaboradores en la fecha actual y supervisor asignado sin acceso efectivo) se calcula con `linea_temporal.supervision_en` y solo se advierte de los equipos afectados por ESTA orden. **Límites documentados:** DM-09 se define en la fecha actual (un supervisor que lo será solo en el futuro no genera advertencia hoy) y **las peticiones ya iniciadas cuando se confirma la desactivación pueden finalizar: no se garantiza su cancelación retroactiva** (decisión del 2026-11-17; lo pedido después se rechaza siempre) |
| **Pendientes** | La reactivación (M1-10) no tiene contrato (PA-12, A10) |

## M1-03a — Emitir el código de primer acceso (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Emitir el código de un solo uso con el que una persona completa su primer acceso |
| **Relacionados** | HU-1.5 · RF-52, RF-56 · RN-34, RN-35, RN-64 |
| **Invocación** | Orden de provisión `emitir-codigo-primer-acceso`. Orden CLI del servidor (A2, `[CONFIRMADO]` el 2026-11-11): `uv run python -m scripts.provision emitir-codigo-primer-acceso --operador … --persona …`. **Implementada en M1-T8.2** (solo la emisión; el canje es M1-03b, no implementado) |
| **Entrada** | `persona_id` |
| **Respuesta** | El código, mostrado **una sola vez** a la persona operadora **solo en una terminal interactiva** (entrada y salida; con una tubería, un archivo o sin terminal la orden se rechaza con `TERMINAL_INTERACTIVA_REQUERIDA` antes de tocar nada) y su `caduca_en`. No se guarda en claro, no va en el resultado JSON y no puede volver a mostrarse: si falla, se emite otro |
| **Validaciones** | La persona tiene identidad sin contraseña establecida y el acceso no está desactivado. Emitir invalida cualquier código pendiente anterior de la misma finalidad. El código es individual y de un solo uso. Todo se comprueba DENTRO del bloqueo por persona (una desactivación concurrente se serializa con la emisión). No exige pertenencia vigente |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `ACCESO_DESACTIVADO_ADMINISTRATIVAMENTE` · `RECURSO_NO_DISPONIBLE` · `SOLICITUD_INVALIDA` (la persona ya completó el primer acceso) · `TERMINAL_INTERACTIVA_REQUERIDA` · `SECRETO_DE_CODIGOS_NO_CONFIGURADO` · `CODIGO_NO_PRESENTADO` · `CODIGO_NO_CONFIRMADO` · `DEMASIADOS_INTENTOS` |
| **Auditoría y transacción** | Una entrada de emisión, atómica con el código, con la operación `entrega_acceso`, la persona afectada, la persona operadora y `valor_nuevo` con la fase `emision`, la finalidad, el identificador y la caducidad del código. Nunca el código ni su hash |
| **Criterios vinculados** | CA-22, CA-23 |
| **Pendientes** | Decididos el 2026-11-17: entrega directa (A6), 128 bits, 10 minutos y 10 intentos (A4); el código se muestra una sola vez y solo en una terminal interactiva. Modelo y generación preparados en M1-T8.1; la orden se implementa en T8.2. Por decidir en T8.2: formato de presentación del código |

## M1-09a — Emitir el código de recuperación (orden de provisión)

| Campo | Contenido |
|---|---|
| **Propósito** | Emitir el código de un solo uso para recuperar el acceso de una persona que lo perdió |
| **Relacionados** | HU-1.6 · RF-55, RF-106 · RN-34, RN-96 |
| **Invocación** | Orden de provisión `emitir-codigo-recuperacion`. Orden CLI del servidor (A2, `[CONFIRMADO]` el 2026-11-11): `uv run python -m scripts.provision emitir-codigo-recuperacion --operador … --persona … --procedimiento … --referencia …`. **Implementada en M1-T8.2** (solo la emisión; el canje es M1-09b, no implementado) |
| **Entrada** | `persona_id` y la verificación de identidad ESTRUCTURADA (A5, `[CONFIRMADO]` el 2026-11-17): `procedimiento` (`PRESENCIAL`, `VIDEOLLAMADA` o `PROCEDIMIENTO_INTERNO`, este último correspondiente a un protocolo documentado por la organización) y `referencia` administrativa de la evidencia (3 a 64 caracteres, sin espacios, no una descripción). Además la persona operadora debe DECLARAR expresamente, de forma interactiva, que verificó la identidad |
| **Respuesta** | El código, mostrado una sola vez y solo en una terminal interactiva (como M1-03a), y su `caduca_en`. El resultado JSON incluye la finalidad, el identificador del código, la caducidad y la verificación declarada, nunca el código |
| **Validaciones** | La persona tiene contraseña establecida. **Si su acceso está desactivado, no se emite** (DD-05, CA-254). Emitir invalida el código pendiente anterior. Un supervisor no dispone de esta función (CA-28) |
| **Autorización** | Persona operadora autorizada |
| **Errores** | `OPERADOR_NO_AUTORIZADO` · `ACCESO_DESACTIVADO_ADMINISTRATIVAMENTE` · `RECURSO_NO_DISPONIBLE` · `CAMPO_OBLIGATORIO` · `SOLICITUD_INVALIDA` (procedimiento o referencia no válidos; la persona no tiene contraseña) · `VERIFICACION_NO_DECLARADA` · `TERMINAL_INTERACTIVA_REQUERIDA` · `SECRETO_DE_CODIGOS_NO_CONFIGURADO` · `CODIGO_NO_PRESENTADO` · `CODIGO_NO_CONFIRMADO` · `DEMASIADOS_INTENTOS` |
| **Auditoría y transacción** | Una entrada atómica con el código, con la operación `recuperacion_acceso`, la persona afectada, la persona operadora y `valor_nuevo` con la fase `emision`, la finalidad y la verificación DECLARADA (procedimiento, referencia, fecha, `declarada_por_la_persona_operadora` verdadero y `verificada_por_el_sistema` falso). Nunca el código ni su hash |
| **Criterios vinculados** | CA-27, CA-28, CA-254 |
| **Pendientes** | Decididos el 2026-11-17: verificación fuera de banda (A5), entrega directa (A6), 128 bits, 10 minutos y 10 intentos (A4). **`verificacion` deja de ser un texto libre:** se registra de forma estructurada (persona operadora, fecha, procedimiento de una lista cerrada y referencia de la evidencia administrativa, sin datos sensibles innecesarios); la lista y el formato se aprueban en T8.2. La solicitud de recuperación es administrativa y fuera de banda (D10): no hay ruta pública de solicitud |

## Estado de implementación (cierre de M1, M1-T9)

Los 13 contratos de este documento están **implementados y probados** (M1-01a, M1-01b, M1-01c, M1-02a, M1-02b, M1-03a, M1-03b, M1-05, M1-06, M1-07, M1-08, M1-09a y M1-09b); M1-10 queda **fuera de alcance aprobado** (sin regla ni historia). La evidencia criterio por criterio está en `docs/evidencia/matriz-trazabilidad-m1.md`. Observaciones que **no** cambian ningún contrato y que no deben leerse como resueltas: la comprobación de contraseñas comprometidas de M1-03b y M1-09b **está inactiva mientras no se instale el conjunto de Pwned Passwords** en el despliegue; el tope agregado de 100 fallos de M1-01a no está implementado; la configuración de proxies de confianza, la programación de las purgas, el control de dos personas en la verificación de identidad y los identificadores explícitos del enlace histórico de M1-07 son pendientes de despliegue o de producción (matriz, sección 7).

## Operaciones sin contrato

| Operación | Motivo |
|---|---|
| M1-10 Reactivar un acceso desactivado | No existe regla ni historia; necesita una RN antes (ADR-002, sección 11) |
| Consulta pública del historial de pertenencias y de la composición de un equipo | No se crea. CA-09 y CA-13 se verifican con las respuestas de M1-02b y M1-05, que muestran la composición y el historial completo. Ningún requisito dice quién más los consultaría, y una operación nueva sería funcionalidad no pedida |
| Reincorporación | PA-24 |
| Altas y ajustes históricos | PA-25; no existen en el MVP |
| Crear una organización | No existe contrato ni historia. La provisión de equipos exige una organización existente; hoy la crean la semilla de desarrollo o el propietario del esquema. Decisión pendiente |

## Decisiones pendientes que afectan a este módulo

| Id | Decisión | Afecta |
|---|---|---|
| P1 | ~~Forma operativa de la provisión y autenticación y autorización de la persona operadora (ADR-002, sección 9)~~ **Resuelta el 2026-11-11:** órdenes CLI en el servidor (A2) y registro `OPERADOR` con credencial propia (A7). Quedan por detallar la credencial de la persona operadora y el alta de la primera | Todas las órdenes |
| P2 | ~~Medio de entrega de los códigos (A6) y verificación de identidad al recuperar (A5)~~ **Resuelta el 2026-11-17:** entrega directa; verificación fuera de banda con registro estructurado | M1-03a, M1-09a |
| P3 | Valores de caducidad, intentos y sesión (A4, A9). **A9 resuelta en lo implementado el 2026-11-17:** sesión de 24 h y 1 h de inactividad; esperas y límites de M1-01a. Siguen pendientes el tope agregado de 100 y los valores del código (A4) | M1-01a, M1-03b, M1-09b |
| P4 | ~~Política de contraseñas (A8)~~ **Resuelta el 2026-11-17 en lo implementado:** 10 caracteres como mínimo, sin composición ni caducidad, y comprobación local contra Pwned Passwords **inactiva hasta instalar el conjunto** en el despliegue (actualización propuesta trimestral, pendiente de validación operativa) | M1-03b, M1-09b |
| P5 | ~~Aprobar M1-01c~~ Aprobada | M1-01c |
| P6 | ~~Unicidad del nombre de equipo; obligatoriedad del motivo de desactivación~~ **Resuelta el 2026-11-11:** nombre único por organización y motivo obligatorio | M1-02a, M1-08 |
| P7 | ~~Registro técnico de eventos de autenticación (A11)~~ **Resuelta el 2026-11-17:** seis tipos de evento, retención técnica inicial de 30 días y purga por la CLI (PA-06 general sigue pendiente) | M1-01a |
