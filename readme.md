# SMARTWORK

> Plataforma web para registrar y consultar bitácoras laborales: qué se planea hacer, qué se hizo realmente, qué quedó pendiente y qué bloqueos hubo.

**Estado.** La documentación técnica (Entrega 1) está completa y en [docs/](docs/). La **Entrega 2** implementa el **módulo M2 completo** (bitácoras híbridas) y, de M3, el **cierre y la reapertura de la jornada** (M3-01 y M3-02) la **reactivación de actividades completadas** (M3-04) la **marca de error de una actividad y su reversión** (M3-05 y M3-06) la **corrección auditada de avances** (M3-03) y la **consulta del historial de auditoría** (M3-07, solo de los propios registros), con los tres bloques conectados: cliente Flutter Web, API FastAPI y PostgreSQL. Una persona inicia sesión; abre o consulta su bitácora; planifica actividades y continuaciones; registra avances y actividades no planificadas; consulta el detalle y el listado de sus actividades; guarda el resumen diario; cierra la jornada cuando cumple las condiciones y la reabre indicando un motivo, retoma una actividad completada (reactivación) sin crear otra, y marca una actividad como registrada por error o revierte esa marca, sin borrar nada, y corrige el estado, la descripción o el motivo de un avance ya registrado sin crear otro, con auditoría, y consulta la auditoría de su jornada, de una actividad o de un avance. Es un subconjunto deliberado del MVP: **no** están implementados el resto de M1, M4 (consulta de equipo y supervisión, incluida la consulta de la auditoría por quien supervisa) ni M5 (informes con IA). **M2 está implementado y verificado en el entorno de verificación (clúster desechable); `smartwork_app` está en la migración 0008** (0006 a 0008 aplicadas el 2026-11-09 con un respaldo previo; la consulta de la auditoría no requiere ninguna migración nueva). **M3 (M3-01 a M3-07) está implementado y verificado de extremo a extremo** en el cierre técnico del 2026-11-11: M3-07 lo está solo para la persona propietaria, y el acceso del supervisor (CA-111) depende de M4. Hay una [matriz de trazabilidad](docs/evidencia/matriz-trazabilidad-m2-m3.md) y un [informe de verificación](docs/evidencia/verificacion-integral-m2.md). Límites y pendientes en la [sección 9](#9-decisiones-y-limitaciones-técnicas-pendientes).

## Índice

0. [Ficha del proyecto](#0-ficha-del-proyecto)
1. [Descripción general del producto](#1-descripción-general-del-producto)
2. [Arquitectura del sistema](#2-arquitectura-del-sistema)
3. [Modelo de datos](#3-modelo-de-datos)
4. [Especificación de la API](#4-especificación-de-la-api)
5. [Historias de usuario](#5-historias-de-usuario)
6. [Tickets de trabajo](#6-tickets-de-trabajo)
7. [Pull requests](#7-pull-requests)
8. [Alcance de las siguientes entregas](#8-alcance-de-las-siguientes-entregas)
9. [Decisiones y limitaciones técnicas pendientes](#9-decisiones-y-limitaciones-técnicas-pendientes)

---

## 0. Ficha del proyecto

### **0.1. Tu nombre completo:**

Edwin Quintana (EQ)

### **0.2. Nombre del proyecto:**

SMARTWORK

### **0.3. Descripción breve del proyecto:**

SMARTWORK sustituye la comunicación informal de las actividades diarias por mensajería con una bitácora laboral estructurada y consultable. Cada persona registra lo planificado, lo realizado, lo pendiente y los bloqueos; el supervisor ve el estado de su equipo; y los informes individuales y consolidados se generan con apoyo de IA a partir de lo realmente registrado.

### **0.4. URL del proyecto:**

https://54-210-163-251.sslip.io/
supervisor.demo  HZnrDVvY0CCKdp-qZsY

### 0.5. URL o archivo comprimido del repositorio

<https://github.com/marlonbossa09/AI4Devs-finalproject>. Entrega 1 (documentación): rama `feature/entrega-1-eq`. Entrega 2 (implementación del primer recorrido): rama `feature/entrega-2-eq`. Es el repositorio del proyecto final del curso AI4Devs, cuyas plantillas oficiales (`readme.md` y `prompts.md`) estructuran esta documentación. SMARTWORK se documenta como un producto de software profesional.

---

## 1. Descripción general del producto

### **1.1. Objetivo:**

**Problema.** Los equipos comunican hoy sus actividades diarias por mensajería instantánea. Eso provoca tres pérdidas: la información queda enterrada en conversaciones, no hay una forma fiable de consultar qué se hizo, cuándo y por qué, y quien necesita un informe lo reconstruye a mano. Además, no se distingue **lo planeado de lo realmente hecho**, ni se conserva **lo que quedó pendiente** y **los bloqueos**.

**Qué aporta.** Un único lugar donde cada persona registra su jornada; el trabajo que continúa de un día a otro se sigue sin duplicarse; toda corrección retroactiva queda auditada; y los informes se apoyan solo en los registros almacenados.

**Usuarios objetivo.** Dos roles funcionales y ningún tercero:

- **Colaborador:** registra y modifica sus propias actividades y consulta, en solo lectura, lo que le corresponde por su equipo.
- **Supervisor:** pertenece al equipo que supervisa, registra su propia bitácora y dispone de una vista consolidada de su equipo, sin modificar los registros ajenos.

La creación de usuarios y equipos se hace mediante una provisión administrativa controlada, sin panel de administración ni tercer rol. SMARTWORK **no** es una herramienta de evaluación del desempeño: no incorpora rankings ni valoraciones de personas.

Detalle: [alcance del MVP](docs/producto/alcance-mvp.md) y [PRD](docs/producto/prd.md).

### **1.2. Características y funcionalidades principales:**

Las cinco funcionalidades obligatorias (*must-have*) del MVP:

| Módulo | Qué hace | Historias | Contratos |
|---|---|---|---|
| **M1** Autenticación, usuarios y equipos | Acceso con credenciales propias, pertenencia de cada persona a un único equipo con un único supervisor, historial de pertenencias, baja lógica y provisión controlada | HU-1.1 a HU-1.7 | [M1](docs/api/m1-acceso-usuarios-equipos.md) |
| **M2** Bitácoras laborales híbridas | Una bitácora por persona y fecha laboral, con actividades estructuradas (cuatro estados, planificación original conservada, avances con descripción) y un resumen libre | HU-2.1 a HU-2.9 | [M2](docs/api/m2-bitacoras.md) |
| **M3** Seguimiento de actividades y auditoría | Continuidad entre jornadas sin duplicar, estado actual coherente con la secuencia de avances, cierre y reapertura de la jornada, correcciones, reactivación y auditoría de solo anexado | HU-3.1 a HU-3.8 | [M3](docs/api/m3-seguimiento-auditoria.md) |
| **M4** Consulta histórica y supervisión | Lectura de las bitácoras del equipo según el equipo al que pertenecía cada persona en esa fecha, histórico por fechas y vista consolidada del supervisor con estado al corte | HU-4.1 a HU-4.4 | [M4](docs/api/m4-consulta-supervision.md) |
| **M5** Informes individuales y consolidados con IA | Informes en pantalla a partir de registros autorizados, con indicadores calculados de forma determinista, sin valoraciones y con fallo explícito si la IA no responde | HU-5.1 a HU-5.5 | [M5](docs/api/m5-informes.md) |

Las 33 historias y sus 301 criterios de aceptación están en [docs/backlog/](docs/backlog/indice.md).

**Flujo principal de extremo a extremo (FP-1)**, el primero que se implementará:

```mermaid
sequenceDiagram
    actor OP as Provisión
    actor COL as Colaborador
    actor SUP as Supervisor
    participant S as SMARTWORK
    OP->>S: Crea el equipo, su supervisor y un colaborador
    COL->>S: Inicia sesión
    COL->>S: Abre su bitácora de hoy y planifica una actividad
    COL->>S: Registra un avance con su estado y descripción
    COL->>S: Guarda el resumen y cierra la jornada
    SUP->>S: Inicia sesión
    SUP->>S: Consulta la vista de su equipo en el período
    S-->>SUP: Actividades por estado al corte, solo lectura
```

Este flujo cubre M1 a M4 con prioridad máxima. M5 se implementa después (indicadores deterministas primero, narrativa con IA al final) porque depende de decisiones abiertas del proveedor. Detalle en los [tickets](docs/backlog/tickets/indice.md).

### **1.3. Diseño y experiencia de usuario:**

Interfaz web en Flutter, en español, con el diseño aprobado en el prototipo `smartwork_design_proposal.html`: barra lateral oscura, barra superior con la fecha del servidor, tarjetas, indicadores, calendario y formularios, con tipografías DM Sans y Manrope. Es responsive: escritorio, tableta (hasta 1100 px) y móvil (hasta 700 px, donde la barra lateral pasa a ser un menú desplegable).

```mermaid
flowchart LR
    A[Acceso] --> B[Panel principal]
    B --> C[Mi bitácora]
    B --> D[Nueva planificación]
    C --> D
    D --> E[Se guarda en PostgreSQL<br/>y se consulta de nuevo]
    E --> C
```

| Pantalla | Qué muestra, con datos reales |
|---|---|
| Acceso | Panel de marca y formulario de usuario y contraseña. Un error de credenciales no dice cuál de los dos falló |
| Panel principal | Saludo, indicadores (registradas, pendientes, en progreso, completadas) y lista de actividades de la fecha elegida, calendario del mes y progreso de completadas |
| Mi bitácora | Estado de la bitácora con sus tres fechas por separado (laboral, registro y modificación), actividades planificadas y selector de fecha. Si no existe, lo indica y permite abrirla |
| Nueva planificación | Título, fecha, estado inicial (siempre pendiente) y descripción |

Capturas reales con datos ficticios. Los indicadores y la lista salen de lo que el servidor guarda para la fecha elegida:

![Pantalla de acceso](docs/evidencia/01-acceso.jpg)

![Panel principal con una actividad persistida](docs/evidencia/02-panel-principal.jpg)

![Nueva planificación](docs/evidencia/03-nueva-planificacion.jpg)

![Mi bitácora tras guardar la actividad](docs/evidencia/04-mi-bitacora.jpg)

Tableta y móvil (el móvil con su menú desplegable):

![Tableta](docs/evidencia/05-tableta.jpg)

![Móvil](docs/evidencia/06-movil.jpg)

![Móvil con el menú abierto](docs/evidencia/07-movil-menu.jpg)

**Diferencias respecto al prototipo.** Se aplicaron porque el prototipo usaba datos simulados o elementos que no existen todavía:

- Los iconos son Material, no los glifos Unicode del prototipo, que en Flutter Web se dibujan como cuadrados vacíos si falta la fuente.
- Los indicadores y el progreso se calculan sobre la jornada elegida, no sobre un «historial»: la API devuelve una fecha por consulta. El calendario no marca los días con actividad por el mismo motivo; marca el día elegido y el de hoy, y sus flechas cambian de mes.
- La barra lateral muestra solo el rol («Colaborador»), no el equipo, porque la API de sesión no lo devuelve.
- Se omiten el aviso «Prototipo visual», el texto de vista conceptual y los valores precargados del acceso.
- El botón de notificaciones aparece deshabilitado con una explicación, porque no hay notificaciones.
- «Mi bitácora» añade lo que ya es real: estado, tres fechas y apertura de la bitácora.
- En móvil, las acciones del formulario de planificación se apilan a ancho completo.
- Las tipografías se cargan desde Google Fonts al abrir la aplicación, como hacía el prototipo. Es una petición externa de solo fuentes, sin datos de las bitácoras; servirlas desde el propio origen queda como mejora.

No hay vídeo. El resto del recorrido previsto (avances, resumen, cierre, supervisión) se describe en los criterios de aceptación y en los [tickets](docs/backlog/tickets/indice.md).

### **1.4. Instrucciones de instalación:**

**Requisitos.** Git, PostgreSQL 16 o superior (probado con 18.4), [uv](https://docs.astral.sh/uv/) (descarga Python 3.13 por su cuenta, así que hace falta conexión a Internet), Flutter 3.35.3 con Dart 3.9.2 y un navegador moderno. Probado en Windows 11 con Git Bash.

**Convenciones de este apartado.**

- Las órdenes están escritas para **Bash** (en Windows, Git Bash). En PowerShell no sirven `&&` ni la barra invertida `\` de continuación de línea: escribir cada orden en una sola línea y por separado.
- **Cada bloque parte de la raíz del repositorio** y termina de vuelta en ella (`cd ..`).
- En Windows el instalador de PostgreSQL **no añade `psql` al `PATH`**. O se añade la carpeta `bin` (por ejemplo `C:\Program Files\PostgreSQL\18\bin`) al `PATH`, o se invoca con la ruta completa.

**0. Obtener el código.** La rama de la Entrega 2 es `feature/entrega-2-eq`:

```bash
git clone https://github.com/marlonbossa09/AI4Devs-finalproject.git
cd AI4Devs-finalproject
git switch feature/entrega-2-eq
```

**1. Roles y bases de datos.** El script crea dos roles con privilegios mínimos (`smartwork_owner` para las migraciones y `smartwork_app` para la API, sin DDL) y dos bases separadas (`smartwork_dev` y `smartwork_test`). No contiene secretos: las contraseñas se pasan como variables. Se ejecuta una vez como superusuario; `psql` pide su contraseña de forma interactiva. Si PostgreSQL no escucha en el puerto 5432, cambiar el valor de `-p`.

**Elegir contraseñas que solo usen letras, números y `-`, `_`, `.` o `~`.** Irán dentro de una URL en el paso 2: un `@`, `/`, `:` o `%` la rompe, salvo que se escriba codificado (`@` → `%40`). El síntoma de una contraseña mal codificada es que la API arranca pero `/health/ready` responde 503.

```bash
psql -h 127.0.0.1 -p 5432 -U postgres -d postgres \
     -v owner_password='ELEGIR-UNA' -v app_password='ELEGIR-OTRA' \
     -f backend/scripts/provision_db.sql
```

**1 bis. Rol de provisión (M1-T2 y M1-T3).** La provisión administrativa usa su propio rol de PostgreSQL de privilegios mínimos, distinto del propietario y de la API. Lo crea quien administra el servidor, **antes de migrar** (las migraciones 0009 y 0010 fallan con un mensaje claro si no existe). El script `backend/scripts/provision_rol_de_provision.sql` **solo prepara la base de pruebas local `smartwork_test`**: rechaza cualquier otra base (en particular `smartwork_app`) y no modifica un rol que ya exista. **La contraseña no se pasa como argumento ni se escribe en ningún archivo**: `psql` la pide sin eco (`\password`), la cifra en el cliente y envía solo el verificador. En PowerShell, con la ruta de `psql` de la instalación:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 127.0.0.1 -p 5432 -U postgres -d postgres `
    -v base=smartwork_test -f backend\scripts\provision_rol_de_provision.sql
```

`psql` pide primero la contraseña del superusuario y después, dos veces, la del rol nuevo. Si el rol ya existe, el script no lo toca ni le cambia la contraseña; si se interrumpe antes de fijarla, `\password smartwork_provision` desde una sesión de superusuario la establece. Después se añade a `backend/.env` `TEST_PROVISION_DATABASE_URL` (ver `.env.example`). **Preparar con este rol una base distinta de `smartwork_test` (desarrollo o uso real) no está cubierto por este script y requiere un procedimiento aparte, autorizado expresamente**; hasta entonces la CLI de provisión solo se ha ejecutado contra bases desechables y de pruebas.

**2. Configuración.** Copiar `backend/.env.example` a `backend/.env` (no se versiona) y editarlo:

```bash
cp backend/.env.example backend/.env
```

- Sustituir `CAMBIAR` por las contraseñas elegidas: la de `smartwork_app` en `DATABASE_URL` y `TEST_DATABASE_URL`, y la de `smartwork_owner` en `MIGRATIONS_DATABASE_URL` y `TEST_MIGRATIONS_DATABASE_URL`.
- Sustituir también `CAMBIAR` en `PROVISION_DATABASE_URL` y `TEST_PROVISION_DATABASE_URL` por la contraseña del rol de provisión.
- Si PostgreSQL no usa el puerto 5432, cambiarlo en esas URL.
- No tocar los nombres de las bases: la de pruebas debe llamarse exactamente `smartwork_test` (ver más abajo).
- **`AUTH_PEPPER` (obligatorio desde M1-T7).** Es un secreto NUEVO e independiente (mínimo 32 caracteres) con el que se calculan los HMAC de los identificadores de control de intentos. No se versiona y no debe coincidir con ningún otro secreto. Sin él, la API no arranca y la CLI de provisión se niega (fallo cerrado). Generar uno propio, por ejemplo con `python -c "import secrets; print(secrets.token_urlsafe(48))"`, y pegarlo en `backend/.env`. Cambiarlo solo reinicia las esperas en curso.
- **`CODE_PEPPER` (M1-T8).** Segundo secreto, INDEPENDIENTE de `AUTH_PEPPER` (no puede ser el mismo valor), no versionado y de al menos 32 caracteres, con el que se calcula el HMAC con el que solo se guardan los códigos de primer acceso y recuperación. **Obligatorio para arrancar la API** desde M1-T8.3 (emisión y canje de códigos): sin él, la API se niega a arrancar. `CODE_VALIDITY_MINUTES` (10 por defecto) fija la vigencia de un código.
- **`TRUSTED_PROXIES` (DT-07).** Vacío por defecto: el origen de una petición es la dirección de la conexión y `X-Forwarded-For` se ignora. Solo si hay un proxy inverso o un balanceador delante se indican sus direcciones o redes (separadas por comas).

Los parámetros marcados «local» (longitudes máximas de texto, ventana de idempotencia, mínimo de contraseña) son valores de desarrollo configurables: **no son reglas del producto**. La duración de la sesión (24 horas y 1 hora de inactividad) y los valores del control de intentos fallidos (cinco intentos libres, esperas de 30 s a 1 hora, límites por origen de 30 en 5 minutos y 200 en 1 hora, retención técnica de eventos de 30 días) son decisiones aprobadas el 2026-11-17 (ADR-002, A9 y A11), también configurables; si `backend/.env` conserva los valores antiguos de sesión (30 y 480 minutos), prevalecen sobre los nuevos por defecto.

**3. Backend: dependencias, migraciones y datos ficticios.**

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run python -m scripts.seed_dev
cd ..
```

**Migración 0006.** Concede a la API permisos de actualización **solo por columnas** (`actividad.estado_actual`, y `bitacora.resumen`, `modificada_en`, `estado` y `cerrada_en`), necesarios para avances, resumen, cierre y reapertura. `alembic upgrade head` la aplica. En una base que ya existía antes hay que aplicarla, con el rol propietario, antes de usar esas operaciones; `smartwork_app` ya la tiene aplicada.

**Migración 0007.** Concede a la API permiso de actualización **solo por las cuatro columnas de la marca de error** de `actividad` (`registrada_por_error`, `motivo_error`, `marcada_por`, `marcada_en`), y añade restricciones de coherencia: la marca vigente lleva siempre motivo, autora y momento (y sin marca no queda ninguno); una marca vigente no se reescribe; no se marca una actividad con avances en jornadas posteriores a su origen; y una actividad marcada no admite avances ni continuaciones planificadas. No crea tablas ni columnas, y la API sigue sin permiso de borrado. `smartwork_app` ya la tiene aplicada.

**Migración 0008.** Añade `avance.modificado_en` (el momento de la última corrección; igual al del registro mientras no se corrija) y concede a la API permiso de actualización **solo por cuatro columnas** de `avance` (`estado`, `descripcion`, `motivo_bloqueo` y `modificado_en`), sin permiso de borrado. La base garantiza además que el identificador, la actividad, la bitácora (y con ella la fecha laboral), el momento de registro y la condición de reactivación son inmutables; que el motivo de bloqueo solo existe con el estado Bloqueada; que `modificado_en` solo avanza con un cambio de contenido; y que no se corrige un avance de una actividad con marca de error vigente. `smartwork_app` ya la tiene aplicada.

La semilla crea una organización, un equipo y tres personas ficticias (`supervisor.demo`, `colaborador1.demo` y `colaborador2.demo`). Sus contraseñas se generan al ejecutarla y **se muestran una sola vez**: hay que anotarlas en ese momento, porque no se guardan ni se versionan. La semilla se niega a ejecutarse fuera de un servidor local, contra una base que no termine en `_dev` o `_test`, o si la base ya tiene datos.

**4. Cliente web.** Los archivos generados (`*.g.dart`) están versionados, así que no hace falta ejecutar `build_runner`:

```bash
cd frontend
flutter pub get
flutter build web --release
cd ..
```

Para regenerarlos tras cambiar modelos o proveedores: `dart run build_runner build --delete-conflicting-outputs`.

**5. Arrancar.** FastAPI sirve la API y el cliente compilado en el mismo origen (como pide [ADR-002](docs/arquitectura/adr/ADR-002-autenticacion-y-acceso.md)). La orden no termina: deja el servidor en marcha en esa terminal.

```bash
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**6. Probar el flujo principal.**

1. Comprobar el servidor: <http://localhost:8000/health> debe responder `{"status":"ok"}` y <http://localhost:8000/health/ready> debe confirmar la base de datos.
2. Abrir <http://localhost:8000> e iniciar sesión con `colaborador1.demo` y la contraseña que mostró la semilla.
3. En **Panel principal** pulsar **Nueva planificación**, escribir un título y **Guardar planificación**.
4. La aplicación lleva a **Mi bitácora**, que muestra la actividad guardada. Recargar la página: la sesión y la actividad siguen ahí, porque están en PostgreSQL.
5. Cerrar sesión e iniciar con `supervisor.demo`: no ve la bitácora del colaborador (cada persona solo consulta la suya).
6. Con `colaborador1.demo`, en **Mi bitácora**: **+ Registrar avance** sobre la actividad (estado y descripción; **Bloqueada** exige motivo), **Actividad no planificada**, **Escribir resumen** y, en **Actividades**, **Ver detalle** (planificación original, continuaciones y avances por separado).
7. **Planificar continuación** desde el detalle o la tarjeta de la actividad: elige una fecha posterior a hoy. No crea otra actividad ni cambia su estado.
8. Con un resumen con texto y una actividad creada o continuada en la jornada, **Cerrar jornada** (pide confirmación). La jornada queda marcada como cerrada y no ofrece registrar avances; el formulario de planificación avisa si se elige una fecha cerrada. **Reabrir jornada** pide un motivo obligatorio y deja constancia en la auditoría.

La documentación interactiva de la API (`/docs`) solo existe en desarrollo (`APP_ENV=development`). Si tras recompilar el cliente el navegador sigue mostrando una versión antigua, es la caché del *service worker* de Flutter: borrar los datos del sitio desde las herramientas de desarrollo del navegador (Application → Storage → Clear site data).

**Una base con otro nombre (opcional).** Si ya existe una base, por ejemplo `smartwork_app`, se puede usar sin renombrarla ni cambiar su propietario. Como superusuario, conectado a la base `postgres` (omitir un `CREATE ROLE` si ese rol ya existe):

```sql
CREATE ROLE smartwork_owner LOGIN PASSWORD 'ELEGIR-UNA'  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE smartwork_app   LOGIN PASSWORD 'ELEGIR-OTRA' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
GRANT CONNECT ON DATABASE smartwork_app TO smartwork_owner, smartwork_app;
\connect smartwork_app
CREATE EXTENSION IF NOT EXISTS btree_gist;
GRANT USAGE, CREATE ON SCHEMA public TO smartwork_owner;
GRANT USAGE ON SCHEMA public TO smartwork_app;
```

Después, en `backend/.env` apuntar `DATABASE_URL` y `MIGRATIONS_DATABASE_URL` a esa base. La semilla se niega a escribir en una base cuyo nombre no termine en `_dev` o `_test`, salvo que se autorice **por su nombre exacto en esa ejecución**: `SMARTWORK_SEED_DATABASE=smartwork_app uv run python -m scripts.seed_dev` (en PowerShell: `$env:SMARTWORK_SEED_DATABASE='smartwork_app'` y luego la orden).

**Cuentas locales de prueba (opcional).** `backend/scripts/crear_cuentas.py` crea personas con su identidad y su pertenencia a un equipo, de forma idempotente y sin borrar ni modificar nada existente. Es genérico y no contiene datos personales: lee las cuentas de `backend/.local/cuentas.json` y la contraseña de `backend/.local/contrasena`. La carpeta `backend/.local/` no existe al clonar y git la ignora; hay que crearla.

1. Crear `backend/.local/cuentas.json`. Los roles posibles son `colaborador` y `supervisor` (no existe un rol de administrador), y un equipo admite un solo supervisor. La organización puede ser una existente (la de la semilla se llama «Organización Demo») o nueva, en cuyo caso hace falta `zona_horaria`:

   ```json
   {
     "organizacion": "Organización Demo",
     "zona_horaria": "America/Bogota",
     "equipo": "Equipo de prueba",
     "cuentas": [
       {"nombre": "Ana Supervisora", "usuario": "ana@example.test", "rol": "supervisor"},
       {"nombre": "Beto Colaborador", "usuario": "beto@example.test", "rol": "colaborador"}
     ]
   }
   ```

2. Crear `backend/.local/contrasena` con un editor: una sola línea con la contraseña inicial, de al menos 10 caracteres (parámetro `PASSWORD_MIN_LENGTH`, ADR-002). No puede ir en `cuentas.json`, que la rechaza. Se guarda con Argon2id y no se imprime ni se registra. También se admite la variable `SMARTWORK_CUENTAS_PASSWORD` o, en una terminal, se pide sin eco.
3. Ejecutar, con la base y el puerto **exactos** de `backend/.env` (el script comprueba con el propio servidor que son los indicados, que el servidor es local y que el rol no es administrador). `--simular` valida todo y deshace la transacción:

   ```bash
   cd backend
   uv run python -m scripts.crear_cuentas --base smartwork_dev --puerto 5432 --simular
   uv run python -m scripts.crear_cuentas --base smartwork_dev --puerto 5432 --archivo-contrasena .local/contrasena
   cd ..
   ```

**Pruebas.** Necesitan `TEST_DATABASE_URL` y `TEST_MIGRATIONS_DATABASE_URL` de `backend/.env` apuntando a `smartwork_test`; si no, abortan antes de tocar nada.

```bash
cd backend
uv run pytest
cd ../frontend
flutter test
flutter analyze
cd ..
```

**La base de pruebas es aparte y debe llamarse exactamente `smartwork_test`.** Las pruebas son destructivas (vacían tablas y revierten migraciones), así que nunca se apuntan a la base de desarrollo ni a una base compartida: ver la sección 2.6.

---

## 2. Arquitectura del Sistema

### **2.1. Diagrama de arquitectura:**

```mermaid
flowchart TB
  subgraph CLI["Cliente"]
    WEB["Flutter Web"]
  end
  subgraph SRV["Backend: monolito modular, FastAPI"]
    API["Interfaz HTTP y validación"]
    subgraph MOD["Módulos"]
      M1["M1 Acceso, usuarios y equipos"]
      M2["M2 Bitácoras y actividades"]
      M3["M3 Seguimiento y auditoría"]
      M4["M4 Consulta y supervisión"]
      M5["M5 Informes"]
    end
    AUT["Política única de autorización histórica"]
    AUD["Auditoría de solo anexado"]
    PIA["Interfaz de IA"]
  end
  DB[("PostgreSQL")]
  IA["Servicio de IA<br/>proveedor pendiente"]

  WEB -->|"HTTPS, cookie de sesión"| API
  API --> MOD
  MOD --> AUT
  MOD --> AUD
  MOD --> DB
  M5 --> PIA
  PIA -.->|"datos autorizados<br/>y seudonimizados"| IA
```

**Patrón y justificación.** Monolito modular con un módulo por funcionalidad, una única política de autorización en el backend y la IA detrás de una interfaz propia. Se eligió porque el producto necesita operaciones atómicas (guardar un cambio, recalcular el estado y auditar a la vez), una sola fuente de verdad para la autorización histórica y bajo coste operativo para un equipo pequeño. La IA y la identificación se integran detrás de interfaces para no acoplar el producto a un proveedor. Detalle y alternativas: [ADR-001](docs/arquitectura/adr/ADR-001-stack-tecnologico.md) y [arquitectura general](docs/arquitectura/arquitectura-general.md).

### **2.2. Descripción de componentes principales:**

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| Cliente web | Flutter Web | Presentación; no decide autorizaciones |
| Interfaz HTTP | FastAPI (Python) | Validación, errores comunes, prefijo `/api/v1` |
| Módulos M1 a M5 | FastAPI (Python) | Casos de uso de cada funcionalidad |
| Autorización histórica | Backend | Decide quién ve qué según el equipo de la persona en la fecha laboral del registro |
| Auditoría | Backend y PostgreSQL | Entrada única por operación, atómica con el cambio; no se modifica ni se borra |
| Interfaz de IA | Backend | Genera la narrativa de los informes sin acoplarse a un proveedor |
| Persistencia | PostgreSQL | Datos del dominio, identidad, sesiones y auditoría |

### **2.3. Descripción de alto nivel del proyecto y estructura de ficheros**

```text
.
├── readme.md  prompts.md  CLAUDE.md
├── docs/                        Especificación (alcance, PRD, historias, ADR, modelo, API, tickets)
│   └── evidencia/               Capturas de la aplicación en ejecución
├── backend/                     FastAPI + SQLAlchemy 2.0 + Alembic (monolito modular)
│   ├── app/
│   │   ├── main.py              Aplicación, prefijo /api/v1, errores y servicio del cliente
│   │   ├── config.py            Parámetros configurables (nada fijado en el código)
│   │   ├── db.py  errores.py  salud.py   Salud y disponibilidad (/health, /health/ready)
│   │   ├── seguridad/           Argon2id, sesiones y token CSRF, verificación del origen
│   │   ├── compartido/          Política de acceso, auditoría, idempotencia, fechas, dependencias
│   │   └── modulos/
│   │       ├── acceso/          M1-01a/b/c: iniciar, cerrar y consultar la sesión
│   │       └── bitacoras/       M2-01a/b y M2-03: consultar, abrir y planificar
│   ├── migrations/versions/     0001 a 0005 (SQL escrito a mano)
│   ├── scripts/                 provision.py (provisión oficial), provision_db.sql, provision_rol_de_provision.sql,
│   │                            seed_dev.py y crear_cuentas.py (solo desarrollo), verificar_datos.py
│   └── tests/                   Integración sobre PostgreSQL real y extremo a extremo
└── frontend/                    Flutter Web, Riverpod y Dio
    └── lib/
        ├── config/              Configuración (URL de la API)
        ├── core/                network, errors, utils, theme, layout (barra lateral y superior) y widgets reutilizables
        └── features/
            ├── auth/            data (models, remote, repository), domain, presentation (login)
            └── logbook/         data, domain, presentation (providers, pages: dashboard, logbook, planning)
```

El frontend sigue una arquitectura limpia por funcionalidad: `presentation` depende de `domain`, `data` implementa el contrato de `domain`, y `domain` no importa Flutter ni Dio. El código y los identificadores del frontend están en inglés; los campos JSON conservan los nombres en español de los contratos mediante su mapeo. El backend conserva el vocabulario del modelo de datos (tablas, columnas y códigos de error en español) para mantener la trazabilidad con la especificación.

### **2.4. Infraestructura y despliegue**

El despliegue **no está decidido** (decisión DT-07). Las condiciones que el diseño ya impone son un único origen para la aplicación y la API detrás de un proxy inverso, HTTPS en todo el tráfico y un reloj sincronizado en el servidor:

```mermaid
flowchart LR
    N["Navegador"] -->|HTTPS| P["Proxy inverso<br/>un solo origen"]
    P -->|"/ (estáticos)"| F["Flutter Web"]
    P -->|"/api/v1"| B["Backend FastAPI"]
    B --> D[("PostgreSQL")]
    B -.->|"pendiente de decidir"| I["Servicio de IA"]
```

No se ha realizado ningún despliegue. En local, FastAPI sirve el cliente compilado y la API desde un único origen, que es la condición que el diseño exige al proxy inverso.

### **2.5. Seguridad**

**Implementado y comprobado en la Entrega 2:**

- **Contraseñas con Argon2id** (19 MiB, 2 iteraciones, paralelismo 1, configurables). Solo se guarda el hash; ninguna tabla contiene la contraseña en claro (comprobado recorriendo todas las tablas).
- **Sesiones revocables en el servidor**, guardadas en PostgreSQL. La cookie lleva un secreto aleatorio de 256 bits y la base solo guarda su hash SHA-256. Caduca tras 1 hora de inactividad y a las 24 horas de duración absoluta (configurables). Cerrar la sesión la revoca en el servidor, aunque se conserve la cookie.
- **Cookie `__Host-`** con `Secure`, `HttpOnly`, `SameSite=Strict` y sin `Domain`. Se comprobó en Chrome real que la acepta en `localhost` y que JavaScript no puede leerla.
- **CSRF:** token en una cabecera propia, derivado con HMAC del secreto de la sesión, más verificación del `Origin` (o `Referer`). Una petición que modifica sin token o desde otro origen se rechaza sin cambiar nada. En Chrome real, una petición entre sitios llegó sin cookie y las peticiones CORS previas fueron rechazadas.
- **Protección frente a intentos fallidos de autenticación (M1-T7):** cinco intentos libres y, después, esperas de 30 s que se duplican (1, 2, 4, 8, 16 y 32 min) hasta 1 hora, por identificador normalizado y origen; respuesta 429 `DEMASIADAS_SOLICITUDES` con `Retry-After`, también con la contraseña correcta mientras dura la espera y sin distinguir una cuenta que existe de otra que no; el intento se reserva de forma atómica ANTES de calcular Argon2 (sin transacción ni bloqueo abiertos durante el hash), solo una autenticación completa (contraseña correcta, acceso habilitado y pertenencia vigente) reinicia el contador, un contador se olvida a las 24 horas, y límites por origen de 30 intentos fallidos en 5 minutos y 200 en 1 hora. Todo caduca solo: no hay bloqueos permanentes. Los identificadores y orígenes de control se guardan solo como HMAC (`AUTH_PEPPER`) y los eventos técnicos de autenticación (sin secretos, de solo anexado, retención inicial de 30 días) están separados de la auditoría. La persona operadora de la CLI tiene la misma curva con un contador propio y nunca se deshabilita. **No implementado:** el tope agregado de 100 fallos por cuenta con deshabilitación de la contraseña (a revisar con la recuperación segura, M1-T8): un ataque distribuido desde muchos orígenes no lo frena el contador por cuenta y origen.
- **Errores uniformes:** un identificador inexistente y una contraseña incorrecta dan la misma respuesta, con un coste de verificación comparable; un recurso inexistente y uno ajeno son indistinguibles.
- **Orden de evaluación** de las convenciones (identidad, acceso, formato, permiso, reglas) en una política de acceso única.
- **Privilegios mínimos en la base de datos:** la API no puede crear objetos, no borra nada, no edita planificaciones, y solo inserta y lee en la auditoría. La **auditoría es de solo anexado**: ni la aplicación ni el propietario pueden actualizarla o borrarla.
- **Provisión por CLI del servidor, sin endpoints HTTP administrativos (M1-T2 a M1-T4):** cada orden exige identificarse como persona operadora con credencial propia (solo se guarda su hash Argon2id; nunca va como argumento ni se imprime) y se ejecuta con un rol de PostgreSQL de privilegios mínimos distinto del propietario y de la API, que no puede tocar bitácoras ni nada de M2 o M3 ni modificar la auditoría. La CLI se niega a trabajar con otro rol. Una orden rechazada no deja altas parciales. El traslado y el cambio de rol (`registrar-traslado`) validan la línea temporal completa de cada persona y de cada equipo, aplican un relevo de supervisor como una sola operación atómica, conservan intactas las pertenencias anteriores y se protegen además en la base con un disparador diferido solo para el rol de provisión. `finalizar-pertenencia` y `cancelar-operacion-programada` finalizan pertenencias y cancelan o sustituyen operaciones que todavía no han surtido efecto: solo se toca lo programado (el rol de provisión solo puede borrar un intervalo que no ha empezado y la base lo impide para el resto), el relevo de un supervisor es una sola operación atómica y la planificación posterior a una finalización se conserva. `desactivar-acceso` desactiva de inmediato el acceso de una persona (motivo obligatorio) y revoca todas sus sesiones en la misma transacción, sin tocar pertenencias ni registros; si deja a un equipo sin supervisión efectiva lo advierte en su resultado y en la auditoría, sin asignar sustitutos. El rol de provisión escribe solo las columnas `persona.acceso_desactivado_en` y `sesion.revocada_en` y no lee contraseñas ni secretos de sesión. `seed_dev.py` y `crear_cuentas.py` son herramientas de desarrollo, no la provisión oficial. **Pendiente:** limitación de intentos de la credencial de la persona operadora (A9, A11).
- **Idempotencia** de las operaciones que crean registros (planificación, continuación, avance, actividad no planificada, cierre y reapertura) mediante `Idempotency-Key`; un reintento con la misma clave no duplica nada. Las escrituras de una jornada pasada, y cada cierre y reapertura, se auditan en la misma transacción.
- **Concurrencia:** las escrituras sobre una actividad o una bitácora se serializan con bloqueos de fila (`SELECT … FOR UPDATE`), de modo que un cierre simultáneo no deja entrar contenido en una jornada ya cerrada y los avances simultáneos dejan un estado actual coherente con la secuencia. Hay pruebas de ambos casos.
- **Datos de prueba protegidos:** la semilla se niega fuera de un servidor local y de una base `_dev` o `_test`; las pruebas abortan si no usan una base `_test`; no hay ninguna suplantación de identidad ni cabecera de elusión de la autenticación.
- Sin secretos en el repositorio: `backend/.env` está ignorado y solo se versiona `.env.example`.

**Limitaciones que hay que resolver antes de un despliegue en AWS ECS** (el despliegue no está hecho ni probado allí):

1. **Cabeceras de proxy y origen de las peticiones (DT-07).** El control de intentos usa la dirección de la conexión como origen y solo acepta `X-Forwarded-For` de un proxy expresamente configurado en `TRUSTED_PROXIES` (o con `--forwarded-allow-ips` limitado al balanceador en uvicorn, nunca `*`). Sin esa configuración, detrás de un balanceador todas las personas compartirían origen y la protección degeneraría en la de solo cuenta. La comprobación de `Origin` compara el esquema de la petición con el del `Origin`. Detrás de un balanceador que termina TLS, uvicorn ve `http` y **rechazaría toda escritura** (400) salvo que se arranque con `--proxy-headers` y un `--forwarded-allow-ips` limitado al balanceador, y que el proxy conserve `Host`. Sin comprobar.
2. **HTTPS obligatorio.** La cookie `__Host-` es `Secure`: sin HTTPS no se establece la sesión.
3. **Credenciales y roles.** Hoy salen de `backend/.env`. En ECS deben venir de un gestor de secretos, con dos identidades distintas: `smartwork_owner` solo para migraciones (una tarea aparte antes del despliegue) y `smartwork_app` sin DDL para la API.
4. **Migraciones.** La 0006, la 0007 y la 0008 deben estar aplicadas en las bases existentes (en `smartwork_app` lo están). Las migraciones se aplican antes de actualizar las tareas.
5. **Conexiones.** El tamaño del *pool* por tarea multiplicado por el número de tareas debe caber en las conexiones máximas de PostgreSQL. No se ha medido.
6. **Alta de usuarios.** No hay provisión ni códigos de primer acceso: las personas de prueba las crea la semilla o un script local. No se pueden dar de alta usuarios reales.
7. **Intentos fallidos del inicio de sesión: implementado salvo el tope agregado de 100** (ADR-002 A9, M1-T7). Falta decidir con la recuperación segura (M1-T8) la deshabilitación de la contraseña a los 100 fallos; sin ella, los ataques distribuidos desde muchos orígenes no los frena el contador por cuenta y origen, y un origen IPv6 puede rotar entre las direcciones de su prefijo. Los eventos técnicos de autenticación solo se purgan con la orden `purgar-eventos-autenticacion` (retención inicial de 30 días): no hay planificador, hay que programarla en el despliegue (PA-06 general sigue pendiente).
8. **Datos de idempotencia.** Una clave caducada se trata como nueva, pero las filas no se purgan: no hay tarea de limpieza.
9. **Auditoría.** La retención (PA-06) no está decidida y no hay copias de seguridad definidas; la auditoría es de solo anexado.
10. **Observabilidad.** Hay un identificador de correlación en los errores, pero no se ha revisado que ningún registro incluya contenido de bitácoras, ni se ha definido la recogida de registros y métricas.
11. **Origen del cliente.** FastAPI sirve el cliente compilado en el mismo origen. Servirlo desde otro sitio (S3, CDN) exige replantear el origen, la cookie y el CSRF.
12. **Métodos HTTP no admitidos.** Responden `405 METODO_NO_PERMITIDO` con la cabecera `Allow` (PA-30, aprobado el 2026-11-11 e implementado en M1-T0). El 400 para solicitudes inválidas se mantiene y el rechazo de CSRF y de origen (400) queda provisionalmente como estaba.
13. **Aprovisionamiento de la base existente.** El esquema de `smartwork_app` coincide con las migraciones 0001 a 0008, salvo dos permisos del esquema `public` heredados del aprovisionamiento manual (`GRANT ALL … TO smartwork_owner` y el `USAGE` de PUBLIC no revocado). Sin efecto funcional; debe uniformarse con el procedimiento de `scripts/provision_db.sql` al preparar un entorno nuevo.
14. **Verificación de seguridad.** No se ha hecho una prueba de penetración ni una auditoría de dependencias. Las pruebas de interfaz se hicieron a mano en Chrome; no hay pruebas automáticas en navegador ni se probaron otros navegadores.

**Diseñado y todavía no implementado:** códigos de un solo uso para el primer acceso y la recuperación (M1-T8), la reactivación controlada de un acceso desactivado, el tope agregado de 100 fallos con deshabilitación de la contraseña (ADR-002 A9: diferido el 2026-11-17, a revisar con la recuperación segura) y la IA con datos mínimos ([ADR-003](docs/arquitectura/adr/ADR-003-integracion-de-ia.md)). La desactivación del acceso (M1-T6) y la limitación de intentos fallidos, salvo ese tope (M1-T7), ya están implementadas.

### **2.6. Tests**

Resultado de la última ejecución, con las dos suites completas. Las de backend usan PostgreSQL real; las de Flutter usan repositorios en memoria que imitan al servidor, por lo que **no sustituyen** a la integración real (ver la [matriz](docs/evidencia/matriz-trazabilidad-m2-m3.md)):

| Suite | Resultado | Qué cubre |
|---|---|---|
| Backend (`pytest`) | **2804 superadas y 1 omitida a propósito (regresión completa del cierre de M1, M1-T9)** (suite completa, sobre `smartwork_test` de un clúster PostgreSQL desechable) | Esquema y restricciones de la base de datos, autenticación, CSRF y origen, M2 completo (consulta, apertura, resumen, planificación, continuación, avances, actividades no planificadas, detalle y listado), cierre y reapertura, reactivación (M3-04), marca de error y su reversión (M3-05 y M3-06), corrección de avances (M3-03), consulta de la auditoría (M3-07), secuencia de avances, concurrencia, idempotencia, auditoría, atomicidad, extremo a extremo, salud y aislamiento de las propias pruebas |
| Frontend (`flutter test`) | **654 superadas y `flutter analyze` sin incidencias** | Modelos, cliente HTTP, reglas puras (avances, continuación, cierre, reactivación, marca de error, corrección, secuencia y presentación de la auditoría), pantallas con repositorios falsos y diseño responsive (escritorio, tableta y móvil, con la fuente real para detectar desbordamientos) |
| Frontend (`flutter analyze`) | Sin incidencias | Análisis estático |

Puntos que las pruebas comprueban de verdad:

- **Restricciones de la base de datos con intentos reales:** solapes de pertenencias, dos supervisores a la vez, título vacío, avance bloqueado sin motivo, y que el rol de la API no pueda borrar ni alterar la auditoría.
- **Concurrencia:** ocho aperturas simultáneas de la misma fecha dejan una sola bitácora; seis peticiones con la misma clave de idempotencia crean una sola actividad.
- **Atomicidad:** si falla la entrada de auditoría, no queda ni la actividad, ni la bitácora, ni la clave.
- **Extremo a extremo:** un servidor real en otro proceso recorre inicio de sesión, consulta, apertura, planificación y consulta, se **reinicia**, y comprueba que la sesión y los datos persisten y que un reintento no duplica.
- **Verificación integral de M2 y del cierre (T9):** sobre una instalación desechable (FastAPI y PostgreSQL reales), un recorrido de 12 puntos —sesión, apertura, planificación, avances, actividad no planificada, detalle y listado, continuación, resumen, cierre, reapertura con auditoría, persistencia tras **reiniciar FastAPI** y rechazos de acceso— más concurrencia (8 peticiones iguales, 8 avances simultáneos) y consistencia del estado. Informe en [docs/evidencia/verificacion-integral-m2.md](docs/evidencia/verificacion-integral-m2.md).
- **Verificación integral de M3 (T14, 2026-11-11):** sobre una base nueva creada con `alembic upgrade head` desde cero (0001 a 0008) y servida por FastAPI real, un recorrido de 12 pasos —planificar, avances, completar, reactivar, nuevos avances, corregir, marcar por error, revertir, cerrar, reabrir con motivo, consultar la auditoría y rechazar lo no autorizado— más idempotencia (misma clave: mismo resultado; otra petición con la misma clave: rechazada), concurrencia real (8 reactivaciones simultáneas: una sola efectiva; 6 correcciones simultáneas: encadenadas en la auditoría; 5 peticiones con la misma clave: un solo avance; la carrera marcar-contra-cerrar repetida 15 veces no dejó nunca una jornada cerrada sin actividad válida) y consistencia histórica contra PostgreSQL. En Chrome (escritorio 1400 px y móvil 400 px), conducido por texto visible con un guion de trabajo ajeno al repositorio, la interfaz reactivó, corrigió, marcó, revirtió, cerró y reabrió, y se comprobó en la base que constaban exactamente las seis entradas de auditoría esperadas.
- **Mutaciones:** en cada ticket se rompió el código a propósito (reglas de cierre, bloqueos, auditoría, protección de texto sin guardar, claves de idempotencia) y las pruebas fallaron; salvo mutaciones equivalentes anotadas, ninguna sobrevivió.
- **Las pruebas detectan fallos:** se rompió el código a propósito en tres puntos (auditoría, idempotencia y conflicto de apertura) y las pruebas fallaron; restaurado, vuelven a pasar.
- **Aislamiento de las pruebas:** solo pueden tocar la base `smartwork_test`, en un servidor local, con un rol que no sea administrador y distinta de la de desarrollo. Se comprueba antes de importar la aplicación, al abrir la sesión (el servidor confirma `current_database()`, el rol y el puerto) y antes de cada limpieza; si algo no cuadra, se aborta sin ejecutar nada. 24 pruebas lo verifican, entre ellas el rechazo de `smartwork_app`, de otras bases del servicio (también las que terminan en `_test`), de servidores remotos y del puerto 5433. Una ejecución con la configuración de pruebas apuntada a propósito a `smartwork_app` abortó antes de tocarla, y tras la suite completa `smartwork_app` conservaba exactamente sus datos y su versión de migración.
- **Verificación manual en Chrome real** del flujo completo, de las cookies, el CSRF y el origen, y de la persistencia tras recargar y reiniciar.

**No hay prueba automatizada de la interfaz en un navegador dentro del repositorio** (por ejemplo, `integration_test` con `chromedriver`): no se instaló esa herramienta. El recorrido en el navegador se comprobó en Chrome (a mano y, en T14, con un guion de trabajo ajeno al repositorio) (escritorio y móvil emulado), con capturas, durante cada ticket y en T9. Antes de la Entrega 2 se comprobó la documentación con scripts de trabajo ajenos al repositorio (301 criterios con formato estricto y 35 contratos con trazabilidad completa).

---

## 3. Modelo de Datos

### **3.1. Diagrama del modelo de datos:**

Nueve entidades funcionales. Las estructuras técnicas de identidad, sesiones, códigos, operadores e idempotencia se describen aparte (sección 3.10 del [modelo](docs/modelo-datos/modelo-datos.md)).

```mermaid
erDiagram
    PERSONA ||--o| IDENTIDAD : "tiene"
    PERSONA ||--o{ CLAVE_IDEMPOTENCIA : "origina"
    IDENTIDAD ||--o{ SESION : "abre"
    IDENTIDAD ||--o{ CODIGO_UNICO : "recibe"
    OPERADOR {
        string id PK
        string identificador
        string hash_credencial
        string estado
        datetime revocado_en
    }
    IDENTIDAD {
        string id PK
        string persona_id FK
        string identificador_acceso
        string hash_contrasena
    }
    SESION {
        string id PK
        string identidad_id FK
        datetime caduca_absoluta_en
        datetime revocada_en
    }
    CODIGO_UNICO {
        string id PK
        string identidad_id FK
        string finalidad
        datetime caduca_en
        datetime usado_en
    }
    CLAVE_IDEMPOTENCIA {
        string id PK
        string persona_id FK
        string clave
        string huella
        datetime caduca_en
    }
```

### **3.2. Descripción de entidades principales:**

| Entidad | Qué representa | Claves y relaciones principales |
|---|---|---|
| `ORGANIZACION` | La organización y su zona horaria única | 1 a N con `EQUIPO` |
| `EQUIPO` | Un equipo; «operativo» se deduce de sus pertenencias | N a 1 con `ORGANIZACION`; 1 a N con `PERTENENCIA` |
| `PERSONA` | Quien registra o consulta; sin credenciales; `acceso_desactivado_en` | 1 a N con `PERTENENCIA`, `BITACORA` y `ACTIVIDAD` |
| `PERTENENCIA` | Historial de equipo y rol por intervalo semiabierto de fechas laborales | Sin solapes; el equipo de un registro se deduce de ella |
| `BITACORA` | La jornada de una persona en una fecha laboral; única por persona y fecha | 1 a N con `ACTIVIDAD`, `PLANIFICACION` y `AVANCE` |
| `ACTIVIDAD` | Unidad de trabajo con propietaria inmutable, título obligatorio y `estado_actual` derivado | 1 a N con `PLANIFICACION` y `AVANCE` |
| `PLANIFICACION` | Lo previsto (original o continuación); no es un avance y no se edita | N a 1 con `ACTIVIDAD` y `BITACORA` |
| `AVANCE` | Registro de ejecución con estado histórico; ordenado por fecha laboral, momento e identificador | N a 1 con `ACTIVIDAD` y `BITACORA` |
| `AUDITORIA` | Entrada única por operación, de solo anexado | Referencia al registro afectado por tipo e identificador |

Atributos, tipos conceptuales, restricciones y las 39 reglas de integridad: [modelo de datos](docs/modelo-datos/modelo-datos.md).

---

## 4. Especificación de la API

La especificación completa son 35 contratos (propuestos): [docs/api/](docs/api/indice.md). **Implementados en la Entrega 2:** M1-01a, M1-01b, M1-01c, **M2-01a a M2-08 (todo M2)**, **M3-01**, **M3-02**, **M3-04**, **M3-03**, **M3-05**, **M3-06** y **M3-07** (solo la consulta de la persona propietaria). No implementados: el resto de M1, M4 y M5.

| Operación | Método y ruta |
|---|---|
| M1-01a/b/c | `POST /sesion` · `POST /sesion/cierre` · `GET /sesion` |
| M2-01a / M2-01b | `GET /mi/bitacoras/{fecha}` · `POST /mi/bitacoras` |
| M2-02 | `PUT /mi/bitacoras/{fecha}/resumen` |
| M2-03 | `POST /mi/bitacoras/{fecha}/planificaciones` |
| M2-04 | `POST /mi/actividades/{id}/continuaciones-planificadas` |
| M2-05 | `POST /mi/actividades/{id}/avances` |
| M2-06 | `POST /mi/actividades-no-planificadas` |
| M2-07 / M2-08 | `GET /mi/actividades/{id}` · `GET /mi/actividades` |
| M3-01 / M3-02 | `POST /mi/bitacoras/{fecha}/cierre` · `POST /mi/bitacoras/{fecha}/reapertura` |
| M3-04 | `POST /mi/actividades/{id}/reactivacion` |
| M3-03 | `PATCH /mi/avances/{id}` |
| M3-05 | `POST /mi/actividades/{id}/marca-error` |
| M3-06 | `POST /mi/actividades/{id}/marca-error/reversion` |
| M3-07 | `GET /auditoria?tipo_objeto=&objeto_id=` |

Las rutas son relativas a `/api/v1`. Toda operación que crea registros, y el cierre y la reapertura, exigen la cabecera `Idempotency-Key`. Los listados devuelven `{"elementos": [...], "siguiente": ...}`; las escrituras devuelven un objeto con nombre (`{"bitacora": …}`, `{"actividad": …, "avance": …, "bitacora_creada": …}`). Extracto de tres operaciones principales en formato OpenAPI:

```yaml
openapi: 3.0.3
info:
  title: SMARTWORK API (extracto)
  version: 0.5-propuesto
servers:
  - url: /api/v1
paths:
  /mi/bitacoras:
    post:
      summary: Abrir mi bitácora de una fecha laboral (M2-01b)
      description: Idempotente. Si la bitácora ya existe, devuelve la misma sin modificarla.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [fecha_laboral]
              properties:
                fecha_laboral: {type: string, format: date, example: "2026-11-09"}
      responses:
        "201": {description: Bitácora creada (creada true)}
        "200": {description: Bitácora existente, sin cambios (creada false)}
        "422": {description: FECHA_NO_CUBIERTA, la fecha no está cubierta por una pertenencia de la persona}
        "403": {description: ACCESO_DESACTIVADO o SIN_PERTENENCIA_VIGENTE}
  /mi/actividades/{actividad_id}/avances:
    post:
      summary: Registrar un avance sobre una actividad propia (M2-05)
      parameters:
        - {name: actividad_id, in: path, required: true, schema: {type: string}}
        - {name: Idempotency-Key, in: header, required: true, schema: {type: string}}
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [fecha_laboral, estado, descripcion]
              properties:
                fecha_laboral: {type: string, format: date}
                estado: {type: string, enum: [Pendiente, En progreso, Bloqueada, Completada]}
                descripcion: {type: string, description: No vacía}
                motivo_bloqueo: {type: string, description: Obligatorio si el estado es Bloqueada}
      responses:
        "201": {description: Avance creado y actividad con su estado_actual recalculado}
        "409": {description: ACTIVIDAD_COMPLETADA o BITACORA_CERRADA}
        "422": {description: ESTADO_INVALIDO, MOTIVO_BLOQUEO_OBLIGATORIO, DESCRIPCION_OBLIGATORIA o FECHA_FUTURA_NO_PERMITIDA}
        "404": {description: RECURSO_NO_DISPONIBLE, indistinguible para actividad inexistente o ajena}
  /equipo/supervision:
    get:
      summary: Vista de supervisión del equipo en un período (M4-03)
      description: Solo supervisor con acceso efectivo. El corte es el último día del período.
      parameters:
        - {name: desde, in: query, required: true, schema: {type: string, format: date}}
        - {name: hasta, in: query, required: true, schema: {type: string, format: date}}
        - {name: limite, in: query, schema: {type: integer}}
        - {name: continuar_desde, in: query, schema: {type: string}}
      responses:
        "200":
          description: Actividades autorizadas con su estado al corte
          content:
            application/json:
              schema:
                type: object
                properties:
                  periodo: {type: object}
                  corte: {type: string, format: date}
                  totales_por_estado: {type: object}
                  elementos: {type: array, items: {type: object}}
                  siguiente: {type: string, nullable: true}
        "403": {description: OPERACION_NO_PERMITIDA para un colaborador}
```

Ejemplo de petición a `POST /api/v1/mi/actividades/{actividad_id}/avances` (datos ficticios): `{"fecha_laboral": "2026-11-09", "estado": "En progreso", "descripcion": "Revisión de los requisitos del módulo de acceso"}`.

### Salud y disponibilidad

Dos comprobaciones de infraestructura, en la raíz (sin `/api/v1`) y fuera de los contratos de negocio. No requieren autenticación, devuelven JSON mínimo y nunca incluyen credenciales, cadenas de conexión, nombres de servidor, datos de personas ni mensajes de error de la base de datos (ante un fallo solo se registra el tipo de excepción).

| Endpoint | Para qué sirve | Respuesta |
|---|---|---|
| `GET /health` | **Vivacidad:** el proceso de FastAPI atiende peticiones. No usa la base de datos | `200` `{"status": "ok"}` |
| `GET /health/ready` | **Disponibilidad:** ejecuta `SELECT 1` en PostgreSQL | `200` `{"status": "ok", "checks": {"database": "ok"}}`, o `503` `{"status": "unavailable", "checks": {"database": "unavailable"}}` |

La espera máxima a PostgreSQL la fija `DB_CONNECT_TIMEOUT_SECONDS` (3 s por defecto), de modo que una base caída responde 503 en pocos segundos en vez de colgarse. Las respuestas llevan `Cache-Control: no-store`.

Diseñados para AWS ECS (el despliegue no está hecho ni probado allí). Separar las dos comprobaciones evita que una caída de PostgreSQL haga que el orquestador reinicie en bucle contenedores que no tienen la culpa:

- **Comprobación de salud del contenedor:** `/health`, por ejemplo `curl -f http://localhost:8000/health` (la imagen necesitaría `curl` o un equivalente).
- **Comprobación del grupo de destino del balanceador:** `/health/ready`. Un 503 saca la tarea de la rotación sin matarla. Conviene que su tiempo de espera sea mayor que `DB_CONNECT_TIMEOUT_SECONDS`, y dar un periodo de gracia al arrancar.


---

## 5. Historias de Usuario

33 historias con criterios DADO / CUANDO / ENTONCES, trazadas a reglas de negocio y requisitos: [índice](docs/backlog/indice.md). Tres de las principales:

**HU-2.4 — Registrar avances conservando el estado histórico**

> Como colaborador, quiero que cada avance conserve el estado que tenía mi actividad en ese momento, para que el historial de la actividad no cambie cuando cambia su estado actual.

- **Reglas y requisitos:** RN-08, RN-17; RF-08, RF-40.
- **Criterios de aceptación (selección):**
  - **CA-45** (positivo): DADO una actividad mía CUANDO registro un avance en una jornada ENTONCES el avance conserva el estado que tenía la actividad en ese momento.
  - **CA-46** (positivo): DADO una actividad con avances anteriores CUANDO su estado actual cambia ENTONCES los avances anteriores siguen mostrando el estado que tenían.
  - **CA-47** (límite): DADO cualquier actividad CUANDO se consulta su estado ENTONCES es uno de estos cuatro: Pendiente, En progreso, Bloqueada o Completada.
  - **CA-48** (negativo): DADO una actividad CUANDO intento asignarle un valor que no es uno de los cuatro estados ENTONCES no se acepta.
- **Historia completa:** [HU-2.4](docs/backlog/M2-bitacoras-laborales-hibridas/HU-2.4-registrar-avances-conservando-el-estado-historico.md)

**HU-3.3 — Cerrar mi jornada**

> Como colaborador, quiero cerrar manualmente mi jornada, para dejarla consolidada sin perder el seguimiento de lo no terminado.

- **Reglas y requisitos:** RN-10, RN-21, RN-22, RN-46, RN-23, RN-109; RF-17, RF-18, RF-19, RF-44, RF-68, RF-119.
- **Criterios de aceptación (selección):**
  - **CA-90** (positivo): DADO una jornada con al menos una actividad creada en ella y un resumen con texto CUANDO la cierro ENTONCES queda cerrada.
  - **CA-92** (negativo): DADO una jornada sin ninguna actividad creada ni continuada CUANDO intento cerrarla ENTONCES no se permite.
  - **CA-93** (negativo): DADO una jornada con el resumen vacío CUANDO intento cerrarla ENTONCES no se permite.
  - **CA-97** (negativo): DADO una jornada con fecha laboral posterior a la actual CUANDO intento cerrarla ENTONCES no se permite.
- **Historia completa:** [HU-3.3](docs/backlog/M3-seguimiento-de-actividades-y-auditoria/HU-3.3-cerrar-mi-jornada.md)

**HU-4.3 — Supervisar mi equipo en un período**

> Como supervisor, quiero una vista consolidada de mi equipo para un período, para saber qué está pendiente, en progreso, bloqueado y completado.

- **Reglas y requisitos:** RN-13, RN-47, RN-48, RN-60, RN-36, RN-23, RN-75, RN-84, RN-85, RN-88, RN-89, RN-101, RN-105; RF-27, RF-69, RF-70, RF-45, RF-78, RF-25, RF-83, RF-94, RF-95, RF-98, RF-99, RF-111, RF-115.
- **Criterios de aceptación (selección):**
  - **CA-137** (positivo): DADO un supervisor CUANDO selecciona un período ENTONCES ve las actividades de su equipo clasificadas en Pendiente, En progreso, Bloqueada y Completada.
  - **CA-141** (negativo): DADO una actividad del equipo completada antes del período y sin avances en él CUANDO el supervisor consulta la vista de ese período ENTONCES no aparece en la vista.
  - **CA-146** (permisos): DADO un supervisor CUANDO consulta la vista ENTONCES solo incluye actividades de su equipo y no de otros equipos.
  - **CA-218** (positivo): DADO el supervisor de U y una actividad pendiente de P, iniciada en T y sin registros en U CUANDO consulta la vista ENTONCES ve una referencia mínima con el propietario, la indicación de que se inició en otro equipo y su estado actual.
- **Historia completa:** [HU-4.3](docs/backlog/M4-consulta-historica-y-supervision/HU-4.3-supervisar-mi-equipo-en-un-periodo.md)

---

## 6. Tickets de Trabajo

34 tickets documentales (base de datos, backend y frontend), con un flujo principal de extremo a extremo: [índice de tickets](docs/backlog/tickets/indice.md). Tres de ellos:

**BE-08 — Avances, secuencia y estado actual**
- **Prioridad:** P0 · **Capa:** Backend
- **Objetivo:** Registrar avances manteniendo una secuencia válida y el estado actual correcto.
- **Historias y criterios:** HU-2.4, HU-2.5, HU-2.8, HU-2.9 (CA-45 a CA-52, CA-66 a CA-80, CA-185, CA-186), HU-3.8 (CA-190, CA-203 a CA-208).
- **Contratos y documentos:** M2-05; modelo, secciones 8 y 9 (IR-09 a IR-12, DM-01, DM-02).
- **Descripción técnica:** Orden total por fecha laboral, momento de registro e identificador; validación de la secuencia (IR-11) para altas retroactivas, mirando solo el avance anterior al punto de inserción (PA-27); recálculo de `estado_actual` en la misma transacción; serialización por actividad; solo se exige abierta la bitácora de la fecha del avance.
- **Dependencias:** BE-07, DB-03.
- **Terminado cuando:**
  - Un avance retroactivo anterior a una finalización se acepta sin reactivar y no altera el estado de uno posterior.
  - Un avance tras una finalización sin reactivación se rechaza.
  - Dos registros simultáneos sobre una actividad dejan un estado actual coherente con la secuencia (comprobación DM-02).

**FE-05 — Actividades: planificar, registrar avances, listar y detalle**
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

**DB-03 — Bitácoras, actividades, planificaciones y avances**
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

---

## 7. Pull Requests

Todavía no hay pull requests. El trabajo de la Entrega 1 está en `feature/entrega-1-eq` y el de la Entrega 2 en `feature/entrega-2-eq`, creada desde la anterior sin modificarla.

---

## 8. Alcance de las siguientes entregas

| Entrega | Contenido |
|---|---|
| **Entrega 1** | Documentación técnica: alcance, requisitos, historias y criterios, arquitectura y decisiones, modelo de datos, contratos de la API, tickets, README y registro del uso de IA |
| **Entrega 2 (esta)** | Flutter Web, FastAPI y PostgreSQL conectados con **M2 completo**, el **cierre y la reapertura de la jornada** (M3-01 y M3-02) la **reactivación de actividades completadas** (M3-04) la **marca de error y su reversión** (M3-05 y M3-06) la **corrección auditada de avances** (M3-03) y la **consulta del historial de auditoría** (M3-07, solo de los propios registros), con persistencia, auditoría, idempotencia y pruebas de concurrencia |
| **Posteriores (previstas)** | M4 (consulta de equipo, histórico y supervisión, incluida la consulta de la auditoría por quien supervisa), M5 (informes con IA, una vez decidido el proveedor), provisión y códigos de acceso, despliegue y pruebas de seguridad |

**Estado por módulo.**

| Módulo | Implementado | Pendiente |
|---|---|---|
| **M1** | Inicio y cierre de sesión, consulta de la sesión, pertenencias (modelo y restricciones), la política interna de visibilidad histórica («equipo en una fecha», M1-T1; sin endpoints: la usará M4) y la provisión inicial de equipos y personas por la CLI del servidor, con personas operadoras y rol de PostgreSQL propios (M1-02a y M1-02b, M1-T2) y el traslado, el cambio de rol, la finalización de pertenencias y la cancelación o sustitución de operaciones programadas por esa misma CLI (M1-05 a M1-07, M1-T3 y M1-T4), verificados de extremo a extremo con un traslado oficial (CA-212 a CA-214, M1-T5: provisión por la CLI, API de M2 y M3 y cliente Flutter, con el reloj de la aplicación de prueba) y la desactivación del acceso por la CLI (M1-08, M1-T6) y la protección frente a intentos fallidos de autenticación (esperas progresivas por cuenta y origen, 429 con `Retry-After`, límites por origen, eventos técnicos y la misma curva para la persona operadora; M1-T7); el **primer acceso funciona por API** (M1-T8.1 a T8.3: modelo de códigos de un solo uso, generación segura, política de contraseñas, la orden administrativa `emitir-codigo-primer-acceso`, con el código mostrado una vez y solo en una terminal interactiva, y `POST /api/v1/acceso/primer-acceso`, que establece la contraseña sin abrir sesión) **y tiene pantalla Flutter desde M1-T8.5**; **la recuperación también funciona por API** (M1-T8.4): `emitir-codigo-recuperacion`, con verificación de identidad estructurada y declarada, y `POST /api/v1/acceso/recuperacion`, que cambia la contraseña y revoca todas las sesiones sin iniciar sesión ni reactivar accesos desactivados; **ambas tienen pantalla Flutter desde M1-T8.5**, enlazada desde el inicio de sesión: piden usuario, código, contraseña nueva y confirmación, muestran la espera del 429, no crean sesión ni guardan nada y no permiten pedir un código (la recuperación sigue siendo administrativa) | **M1-T8.6:** la orden `purgar-codigos` (con la migración 0017), la comprobación de contraseñas comprometidas con **Pwned Passwords de Have I Been Pwned** consultado en local por rangos SHA-1 (sin enviar contraseñas a servicios externos; el conjunto, unos 81 GB, no se incluye en el repositorio, **no está instalado en el entorno de desarrollo y allí la comprobación está inactiva**; efectiva solo con el conjunto instalado en el despliegue, ver `docs/operacion/pwned-passwords.md`) y una revisión de seguridad focalizada que corrigió un defecto real (los errores de la base ya no registran los parámetros de las sentencias). **M1-T9: M1 cerrado técnicamente** (65 criterios: 48 implementados y probados, 15 parciales, 2 bloqueados por otro módulo (M4 o M5), 0 pendientes y 0 fuera de alcance; 13 contratos implementados y probados y M1-10 fuera de alcance aprobado; matriz en [docs/evidencia/matriz-trazabilidad-m1.md](docs/evidencia/matriz-trazabilidad-m1.md)). Pendiente para producción: instalar Pwned Passwords en el despliegue (**la comprobación de contraseñas comprometidas no está activa hasta entonces**; actualización propuesta trimestral), proxies de confianza, programar las purgas, control de dos personas, identificadores explícitos del enlace histórico de auditoría, roles, permisos y secretos del despliegue, reactivación del acceso, tope agregado de 100 fallos con deshabilitación de la contraseña |
| **M2** | Todo: M2-01a a M2-08 | Nada del alcance de M2. Criterios que dependen de otros módulos: ver la matriz |
| **M3** | M3-01 cerrar, M3-02 reabrir la jornada, M3-03 corregir un avance, M3-04 reactivar una actividad completada, M3-05 marcar por error, M3-06 revertir la marca y M3-07 consultar la auditoría, **esta última solo de los propios registros** (parcial) | Dependen de **M4**: la consulta de la auditoría por quien supervisa (CA-111, RA-10) y el paso del 404 provisional al 403 según visibilidad. Dependen de **M1**: CA-212 a CA-214 (traslado de equipo). Provisional: el origen laboral de una actividad (PA-28) |
| **M4** | Nada | Consulta de bitácoras de compañeros, histórico y supervisión; de ello depende pasar del 404 provisional al 403 según visibilidad |
| **M5** | Nada | Informes individuales y consolidados con IA (el proveedor sigue sin decidir) |

Las prioridades y dependencias están en el [índice de tickets](docs/backlog/tickets/indice.md).

---

## 9. Decisiones y limitaciones técnicas pendientes

| Pendiente | Efecto | Dónde se documenta |
|---|---|---|
| **Proveedor de IA, modelo, región, retención y marco legal** (PA-09). AWS Bedrock es el candidato prioritario y la API directa de Anthropic, la alternativa | La integración interna de M5; los contratos públicos no dependen de él | [ADR-003](docs/arquitectura/adr/ADR-003-integracion-de-ia.md) |
| **Mecanismo operativo de la provisión** y valores de sesión, códigos y contraseñas (PA-12) | Órdenes de M1; medio de entrega de códigos y verificación de identidad | [ADR-002](docs/arquitectura/adr/ADR-002-autenticacion-y-acceso.md) |
| Reactivación administrativa del acceso | Falta una regla de negocio | ADR-002, sección 11 |
| Despliegue y observabilidad (DT-07); estrategia de pruebas (DT-08) | No hay entorno ni pruebas definidos | [Arquitectura general](docs/arquitectura/arquitectura-general.md) |
| Retención de la auditoría (PA-06); objetivos de rendimiento y volumen (PA-13); métricas de éxito (PA-11) | Valores de parámetros configurables | [Alcance](docs/producto/alcance-mvp.md), sección 6.3 |
| Reincorporación de personas (PA-24); ajustes históricos de pertenencia (PA-25) | Fuera del MVP | Alcance |
| **Rechazo de CSRF y de origen** (PA-30): provisionalmente 400, como estaba. El método HTTP no admitido ya responde 405 con `Allow` (M1-T0) | Solo la forma de la respuesta de error; ninguna regla de negocio | [Convenciones](docs/api/convenciones.md), [Alcance](docs/producto/alcance-mvp.md) sección 6.3 |

**Límites de la Entrega 2.** Están implementadas M1-01a/b/c, M2-01a a M2-08, M3-01, M3-02, M3-03, M3-04, M3-05, M3-06 y M3-07. La consulta de la auditoría es solo de la persona propietaria del registro: no hay consulta por quien supervisa (depende de M4), supervisión, consulta de compañeros ni informes con IA. No hay provisión: las personas ficticias las crea la semilla de desarrollo, que inserta directamente en la base y por eso no deja entradas de auditoría de provisión. No hay despliegue ni prueba automatizada de la interfaz en un navegador. Por tanto, algunos criterios de aceptación solo se cumplen en parte o están bloqueados por otro módulo: ver la [matriz de trazabilidad](docs/evidencia/matriz-trazabilidad-m2-m3.md).

**Decisiones de implementación que no están en los contratos** (técnicas, sin cambiar ningún requisito):

- **M1-01c** (consultar la sesión) estaba como propuesta; la persona responsable la aprobó para que el cliente reciba el rol y la fecha actual del servidor.
- **Limitación de intentos fallidos del inicio de sesión:** el contrato la pide, pero sus parámetros están pendientes (ADR-002 A9). No está implementada.
- **El token CSRF no se almacena:** se deriva con HMAC del secreto de la sesión, porque M1-01c debe poder devolverlo. ADR-002 describía guardar su hash.
- **Rechazo por CSRF u origen:** el catálogo de errores no tiene un código para ello; se responde `SOLICITUD_INVALIDA` (400) con el motivo en `detalles`.
- **La planificación no renueva `modificada_en`** de la bitácora: el contrato M2-03 no lo dice (M2-02 sí lo dice para el resumen). Tampoco lo renuevan el cierre ni la reapertura: no modifican el contenido (aprobado).
- **`avance.modificado_en`** existe desde la migración 0008 (M3-03): es el momento de la última corrección y coincide con el del registro mientras el avance no se corrija.
- **Decisiones aprobadas durante la implementación de M2 y M3:** el formato de respuesta `{"bitacora": …}` en el cierre y la reapertura; `bitacora_creada` en la respuesta de M2-04; varias continuaciones de una actividad en la misma fecha si son operaciones distintas; los instantes de la auditoría en UTC; un resumen omitido o nulo equivale a vacío (D-03); el 404 provisional para todo recurso ajeno hasta que exista M4.
- **Decididas el 2026-11-09:** IR-11 y CA-78 se armonizan (una inserción retroactiva se incorpora sin tocar los avances posteriores y el estado actual sale del orden laboral completo, PA-27); el envoltorio del listado de M2-08 es `{"elementos": …, "siguiente": …}`; un avance con fecha anterior a la jornada de origen de la actividad se sigue aceptando **de forma provisional**, vinculado a definir el origen laboral de las actividades en M3 (PA-28).
- **PA-29 (resuelta):** una corrección de un avance (M3-03) no debe introducir violaciones de secuencia nuevas; los pares preexistentes que admitió un retroactivo no la rechazan por sí solos. Detalle en la [matriz](docs/evidencia/matriz-trazabilidad-m2-m3.md#4-diferencias-y-decisiones-señaladas).
- **Política de contraseñas:** mínimo de **10 caracteres** (ADR-002, A8), decidido por la persona responsable. Se aparta a propósito de los 15 que recomienda NIST SP 800-63B-4, una referencia y no una obligación para SMARTWORK; el riesgo y sus mitigaciones constan en ADR-002 (Argon2id y almacenamiento solo del hash; la limitación de intentos fallidos todavía no está implementada). Hoy solo la aplica el script de cuentas, porque los flujos que fijan contraseñas (primer acceso y recuperación) no están implementados; el inicio de sesión no impone mínimo.
- **Valores locales** (zona horaria `America/Bogota` de la semilla, duración de sesión, longitudes máximas de texto, ventana de idempotencia): configurables y sin valor de requisito.
- **Pertenencias de la semilla:** empiezan 60 días atrás para poder demostrar jornadas pasadas; IR-30 lo impide por la vía ordinaria pero el modelo permite representar períodos históricos.

Flutter Web conserva riesgos conocidos de accesibilidad, carga inicial y pruebas. Todo contenido marcado `[PROPUESTO]` no es un requisito hasta que la persona responsable lo apruebe.

## Mapa de la documentación

| Documento | Contenido |
|---|---|
| [docs/producto/alcance-mvp.md](docs/producto/alcance-mvp.md) | Alcance del MVP y registro de decisiones |
| [docs/producto/prd.md](docs/producto/prd.md) | Requisitos funcionales y no funcionales, trazabilidad y matriz de permisos |
| [docs/backlog/indice.md](docs/backlog/indice.md) | 33 historias y 301 criterios de aceptación |
| [docs/backlog/tickets/indice.md](docs/backlog/tickets/indice.md) | Tickets de implementación y flujo principal |
| [docs/arquitectura/arquitectura-general.md](docs/arquitectura/arquitectura-general.md) | Arquitectura, riesgos y decisiones técnicas |
| [docs/arquitectura/adr/](docs/arquitectura/adr/) | ADR-001 (stack), ADR-002 (autenticación), ADR-003 (IA) |
| [docs/modelo-datos/modelo-datos.md](docs/modelo-datos/modelo-datos.md) | Modelo de datos y reglas de integridad |
| [docs/api/indice.md](docs/api/indice.md) | Contratos de la API |
| [docs/evidencia/](docs/evidencia/) | Capturas de la aplicación en ejecución |
| [docs/evidencia/matriz-trazabilidad-m2-m3.md](docs/evidencia/matriz-trazabilidad-m2-m3.md) | Matriz contrato → criterio → componente → prueba → estado, y diferencias señaladas |
| [docs/evidencia/verificacion-integral-m2.md](docs/evidencia/verificacion-integral-m2.md) | Informe de la verificación integral de M2 y del cierre |
| [backend/](backend/) y [frontend/](frontend/) | Código de la Entrega 2 |
| [prompts.md](prompts.md) | Uso de IA en el desarrollo |
