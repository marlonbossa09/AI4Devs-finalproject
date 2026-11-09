# SMARTWORK — Verificación integral de M2 y del cierre de jornada

| Campo | Contenido |
|---|---|
| **Naturaleza** | Informe de evidencia. No define requisitos |
| **Fecha** | 2026-11-09 |
| **Alcance** | M1-01a/b/c (sesión), M2-01a a M2-08 y M3-01/M3-02, tal como están en la fecha indicada |
| **Trazabilidad** | [matriz-trazabilidad-m2-m3.md](matriz-trazabilidad-m2-m3.md) |

## 1. Entornos

| Uso | Entorno |
|---|---|
| Pruebas automatizadas (destructivas) | Base `smartwork_test` únicamente. Las pruebas abortan si la configuración apunta a otra base |
| Integración real | Un clúster PostgreSQL desechable en el puerto 55432 (base `smartwork_dev`), con las migraciones 0001 a 0006 aplicadas, FastAPI sirviendo la API y el cliente Flutter compilado en un único origen (puerto 8001) y Chrome real |
| No tocado | `smartwork_app` y el resto de bases existentes. La migración 0006 **no se aplicó** a ninguna de ellas. No se cambió la configuración global de PostgreSQL |

Las contraseñas de las cuentas de prueba se generaron al azar, se guardaron solo en archivos temporales locales fuera del repositorio y se borraron al terminar. Ningún informe ni registro las contiene.

## 2. Suites de pruebas

| Suite | Resultado |
|---|---|
| Backend (`pytest`, `smartwork_test`) | **653 superadas, 1 omitida a propósito** |
| Frontend (`flutter test`) | **414 superadas** |
| `flutter analyze` | Sin incidencias |

Las pruebas de backend ejercen la API por HTTP contra PostgreSQL real. Las de Flutter usan un repositorio en memoria: comprueban pantallas y reglas, pero **no cuentan como integración real** (la matriz lo respeta).

**Mutaciones.** En cada ticket se rompió el código a propósito y se comprobó que alguna prueba fallaba. En T7 a T9: 11 + 17 mutaciones del backend (dos equivalentes, sin efecto observable: el nombre interno de una operación y cambiar `clock_timestamp()` por `now()` en una sola sentencia) y 16 + 13 + 21 + 7 de Flutter; ninguna sobrevivió salvo una redundancia anotada (la guarda de doble envío, que el botón en carga ya impide).

## 3. Verificación integral en la instalación desechable

Un guion de trabajo (fuera del repositorio) ejecutó dos fases contra el servidor real. Entre ellas se **reinició FastAPI** (se detuvo el proceso y se arrancó otro).

| # | Punto | Resultado |
|---|---|---|
| 1 | Inicio y cierre de sesión | Inicio (201 con token CSRF); credenciales incorrectas rechazadas; cierre (204); la sesión cerrada deja de funcionar |
| 2 | Apertura y consulta | Consultar una fecha sin bitácora devuelve 404 y no crea nada; abrir dos veces devuelve la misma bitácora |
| 3 | Planificación | Actividad nueva Pendiente con su planificación original; título vacío rechazado; jornada futura aceptada |
| 4 | Avances | En progreso, Bloqueada (exige motivo), Completada; tras completar se rechaza otro avance; un avance retroactivo anterior a la finalización no cambia el estado; no hay ejecución futura; estado fuera de los cuatro rechazado |
| 5 | Actividad no planificada | Origen propio, sin planificación y con su primer avance |
| 6 | Detalle y listado | Avances en el orden de la secuencia; planificación original conservada; la paginación (`limite` 2) recorre cada actividad una vez; filtro por estado; límite fuera de rango rechazado |
| 7 | Continuación planificada | 201, bitácora futura creada, estado intacto, sin avances; una Completada no se continúa |
| 8 | Resumen diario | Guardar; omitido equivale a vacío; el de una jornada pasada queda auditado; texto demasiado largo rechazado |
| 9 | Cierre | Sin resumen no se cierra y el detalle dice qué falta; con resumen y actividad se cierra; la jornada cerrada rechaza resumen y avances; una jornada futura no se cierra |
| 10 | Reapertura | Sin motivo rechazada; con motivo, 200; se puede corregir y volver a cerrar; la auditoría guarda `cierre`, `reapertura`, `cierre`, con motivo, autor y estados anterior y nuevo |
| 11 | Persistencia tras reiniciar FastAPI | Mismos recuentos de actividades, bitácoras, avances, planificaciones y auditoría; las respuestas de la API (detalle, bitácora con resumen, jornada cerrada, jornada futura) tienen una huella idéntica; la jornada cerrada sigue cerrada y rechazando escrituras; estados actuales coherentes. La sesión anterior siguió siendo válida |
| 12 | Acceso no autorizado | Sin sesión: 401 en cada clase de operación. Sin token CSRF: rechazada. Otra persona: 404 con el mismo cuerpo para todo recurso ajeno (actividad, avance, continuación, cierre, reapertura, bitácora). Con el acceso desactivado, la sesión previa deja de operar y no se puede iniciar sesión |

**Idempotencia y concurrencia.** Un reintento con la misma clave devuelve la misma respuesta; la misma clave con otra petición se rechaza; 8 peticiones iguales a la vez producen un solo efecto; 8 avances simultáneos sobre una actividad se registran todos y el estado actual es el del último avance de la secuencia. Aparte, un script previo comprobó 8 cierres simultáneos (uno 200, siete 409) y 8 reaperturas, y un cierre frente a 6 ediciones del resumen: ninguna edición entró después del cierre.

**Consistencia.** La comprobación del repositorio (`scripts.verificar_datos`) no encontró ninguna actividad con el estado actual incoherente con su secuencia, y ningún avance entró en una jornada después de cerrarla.

## 4. Revisión de la interfaz (Chrome, escritorio 1400×900 y móvil 400×820)

Se recorrió con la interfaz real: inicio de sesión, Mi bitácora, actividades y detalle, planificación, continuación, resumen, cierre con confirmación, reapertura con motivo y la protección del texto sin guardar.

| Captura | Qué muestra |
|---|---|
| [01](capturas-m2/01-detalle-con-continuacion.png) | Detalle: planificación original y continuación planificada con estilos y etiquetas distintos; el estado no cambia |
| [02](capturas-m2/02-jornada-futura-con-continuacion.png) | La jornada futura muestra la misma actividad con su continuación |
| [03](capturas-m2/03-cierre-faltan-condiciones.png) | Cerrar sin resumen: se dice qué falta y no se envía nada |
| [04](capturas-m2/04-confirmar-cierre.png) | Confirmación del cierre |
| [05](capturas-m2/05-jornada-cerrada.png) | Jornada cerrada: panel distinto, fecha de cierre y «Reabrir jornada» |
| [06](capturas-m2/06-reabrir-con-motivo.png) | Diálogo de reapertura con motivo obligatorio |
| [07](capturas-m2/07-planificar-en-fecha-cerrada.png) | Formulario de planificación sobre una fecha cerrada: aviso y envío no ofrecido |
| [08](capturas-m2/08-texto-sin-guardar.png) | Aviso al salir con texto del resumen sin guardar |
| [09](capturas-m2/09-movil-planificar-en-fecha-cerrada.png) · [10](capturas-m2/10-movil-confirmar-cierre.png) | Lo mismo en móvil, con botones apilados y a todo el ancho |

En una jornada cerrada las tarjetas de actividad solo ofrecen «Ver detalle» (no «Registrar avance»), el resumen no es editable y los formularios de planificación, actividad no planificada y avance avisan y no se pueden enviar. **El servidor sigue rechazando esas escrituras** (`BITACORA_CERRADA`): la interfaz no sustituye a las validaciones del backend.

## 5. Hallazgos de la verificación y qué se hizo

| Hallazgo | Corrección |
|---|---|
| Si el usuario cambiaba la fecha **mientras** se cerraba la jornada o se guardaba el resumen, el proveedor de esa fecha se descartaba y la respuesta del servidor fallaba al aplicarse (error de referencia desmontada de Riverpod). Las suscripciones de un widget mueren con él | La suscripción que mantiene vivo el proveedor pasa a nivel de contenedor. Prueba con el cambio de fecha en vuelo para el cierre y el guardado del resumen |
| Los formularios de planificación, actividad no planificada y avance ofrecían enviar sobre una fecha cerrada y solo fallaban después | Avisan y no ofrecen el envío; el backend conserva su validación |
| Una pantalla desactualizada (la jornada se cerró desde otro sitio) seguía ofreciendo registrar | Un rechazo por jornada cerrada recarga el día, y el aviso aparece |

## 6. Lo que esta verificación no demuestra

- Otros navegadores, accesibilidad con lector de pantalla, rendimiento y volumen.
- El comportamiento tras el paso real del tiempo (cambio de día, caducidad de la sesión): se simuló con fechas relativas.
- Operaciones de M3-03 a M3-07, M4 y M5: no están implementadas.
- Un despliegue real. Las limitaciones previas a AWS ECS están en la sección 2.5 del [README](../../readme.md).
