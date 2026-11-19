# SMARTWORK — Demostración en Amazon EC2 con Docker Compose

| Campo | Contenido |
|---|---|
| **Naturaleza** | Guía operativa del despliegue de demostración. No define requisitos ni modifica decisiones del producto |
| **Fecha** | 2026-11-19 |
| **Alcance** | Una instancia EC2 existente (Amazon Linux 2023, 2 vCPU, ~900 MB de RAM, disco EBS de 8 GB) con PostgreSQL, FastAPI y Caddy en contenedores. **Sin** RDS, Kubernetes, ECS, Terraform ni CI/CD. Datos ficticios. Informes con **OpenRouter (modelos gratuitos)** activados solo en esta demostración (sección 7) |
| **Estado** | Publicado con HTTPS válido en **https://54-210-163-251.sslip.io** (Let's Encrypt, renovación automática por Caddy). El túnel SSH sigue disponible como acceso privado |

## 1. Qué se despliega

| Contenedor | Imagen | Función |
|---|---|---|
| `smartwork-db` | `postgres:17-alpine` | Base `smartwork_demo` con tres roles de privilegios mínimos (propietario, aplicación y provisión). Volumen persistente `smartwork_pgdata` en el disco EBS. **El puerto 5432 no se publica** |
| `smartwork-backend` | `smartwork-backend:demo` (`backend/Dockerfile`) | FastAPI detrás del proxy; el puerto 8000 **no se publica** |
| `smartwork-caddy` | `caddy:2-alpine` | Sirve el cliente Flutter Web compilado, hace de proxy de `/api` y `/health` y, cuando se active, gestiona el HTTPS. Bloquea `/docs` y `/openapi.json` |

Archivos en el repositorio: `backend/Dockerfile`, `backend/.dockerignore`, `deploy/docker-compose.yml`, `deploy/Caddyfile`, `deploy/initdb/01-roles-y-base.sh`, `deploy/publico/dominio.caddy.example` y `deploy/.env.server.example`. En la instancia viven en `/opt/smartwork`.

**Configuración.** `/opt/smartwork/.env` es exclusivo del servidor (permisos 600, no versionado) y se generó con contraseñas y peppers aleatorios; no se copió el `.env` de desarrollo. Se respetan sesión, CSRF y `Origin`: la cookie sigue siendo `__Host-` con `Secure`, `HttpOnly` y `SameSite=Strict`. `APP_ENV=development` es el único entorno que admite el producto. Los informes están **desactivados por defecto** en el repositorio (`INFORME_HABILITADO=false`); en el `.env` del servidor se activan con `INFORME_GENERADOR=openrouter` (sección 7).

## 2. Estado verificado (2026-11-19)

- PostgreSQL `healthy`; migraciones hasta **0018** (`alembic current`).
- `/health/ready` responde con la base de datos en `ok`.
- El cliente Flutter Web se sirve y abre en el navegador; el inicio de sesión con una cuenta ficticia funciona.
- Crear una actividad y consultarla en la lista y en la bitácora funciona; sin token CSRF la escritura se rechaza.
- Además, la gestión del equipo por el supervisor (crear un colaborador, emitir su código de primer acceso y finalizar su pertenencia) funciona con los roles del despliegue.

Las pruebas se hicieron por el túnel SSH. No se ejecutaron las suites completas de backend ni de Flutter.

## 3. Acceso por túnel SSH (vigente)

Desde el equipo local (Windows, Git Bash o PowerShell), con la clave `smartwork.pem` guardada **fuera del repositorio** (por ejemplo en `~/.ssh/`; `*.pem` está en `.gitignore`):

```bash
ssh -i ~/.ssh/smartwork.pem -N -L 18080:127.0.0.1:8080 ec2-user@ec2-54-210-163-251.compute-1.amazonaws.com
```

y abrir <http://localhost:18080/>. El navegador trata `localhost` como un contexto seguro, así que la cookie `Secure` funciona sin relajar ningún control. Las cuentas ficticias y sus contraseñas están en `/opt/smartwork/credenciales-demo.txt` (solo las lee el propietario): `supervisor.demo`, `colaborador1.demo` y `colaborador2.demo`.

## 4. Iniciar, detener y mantener

En la instancia (`ssh -i ~/.ssh/smartwork.pem ec2-user@ec2-54-210-163-251.compute-1.amazonaws.com`, luego `cd /opt/smartwork`):

```bash
sudo docker compose up -d            # iniciar (los contenedores también arrancan solos tras un reinicio)
sudo docker compose stop             # detener sin borrar nada (los datos persisten en el volumen)
sudo docker compose ps               # estado
sudo docker compose logs -f backend  # registros
sudo docker compose run --rm migrate            # aplicar migraciones pendientes
sudo docker compose down             # quitar contenedores (el volumen se conserva)
```

`sudo docker compose down -v` **borra la base de datos**: no usarlo salvo para reiniciar la demostración desde cero.

**Actualizar la aplicación.** Compilar en local (`flutter build web --release` en `frontend/` y `docker build -t smartwork-backend:demo backend/`), subir `frontend/build/web` a `/opt/smartwork/web` y la imagen con `docker save smartwork-backend:demo | gzip | ssh … 'gunzip | sudo docker load'`, y ejecutar `sudo docker compose up -d` (y `run --rm migrate` si hay migraciones). Se compila en local porque la instancia tiene ~900 MB de RAM (se añadió 1 GB de swap).

## 5. Acceso público con HTTPS (vigente desde 2026-11-19)

- El grupo de seguridad permite SSH (22), HTTP (80) y HTTPS (443). El 80 solo sirve para emitir el certificado y redirigir (308) a HTTPS; PostgreSQL (5432) y FastAPI (8000) no están publicados.
- Let's Encrypt rechaza los nombres `ec2-*.compute-1.amazonaws.com`; se usa `54-210-163-251.sslip.io`, que resuelve a la IP. Está activado con `publico/dominio.caddy` (copia de `dominio.caddy.example`) y `SMARTWORK_DOMAIN` en `.env`. Un dominio propio sirve igual.
- La cookie de sesión es `__Host-`, `Secure`, `HttpOnly` y `SameSite=Strict`, y por eso la aplicación **solo funciona por HTTPS**: `http://54.210.163.251` a secas no permitiría iniciar sesión y no se relajó ningún control para que lo hiciera.
- **Reducir la exposición:** el SSH está abierto a `0.0.0.0/0`; conviene limitarlo a tu IP en el grupo de seguridad.

## 6. Respaldo, restauración y persistencia

```bash
cd /opt/smartwork
# Respaldo (formato comprimido de PostgreSQL), en /opt/smartwork/respaldos
sudo docker compose exec -T db pg_dump -U postgres -d smartwork_demo -Fc > respaldos/smartwork_demo_$(date +%Y%m%d%H%M).dump
# Restauración sobre la base existente (borra y recrea sus objetos)
sudo docker compose exec -T db pg_restore -U postgres -d smartwork_demo --clean --if-exists --no-owner < respaldos/ARCHIVO.dump
```

Los datos viven en el volumen `smartwork_pgdata` (disco EBS raíz de la instancia: no se creó ni formateó ningún volumen adicional). Recrear los contenedores (`up -d`) **no** los borra: se comprobó al recrear la base en esta actualización. Los registros de los contenedores rotan (10 MB × 3 archivos). Para eliminar todo, y solo si no hay datos que conservar: `sudo docker compose down -v`.

## 7. Informes con OpenRouter (solo demostración, solo datos ficticios)

En `/opt/smartwork/.env` (permisos 600, nunca versionado) están `INFORME_HABILITADO=true`, `INFORME_GENERADOR=openrouter`, la clave, el plazo y una lista de **tres** modelos gratuitos que OpenRouter prueba en orden (`particle-ai/particle-1:free`, `baidu/ernie-5.5-flash-preview:free` y `nvidia/nemotron-3.5-super-vl:free`). En las pruebas con datos ficticios los tres fueron aceptados por el validador 3 de 3 veces; `openrouter/free` (el modelo aleatorio) falló alguna vez. **Los datos del informe salen de la instancia hacia un tercero**: no usar datos reales (D-M5-08). La clave se pegó en una conversación: conviene revocarla y crear otra al terminar. **Los modelos gratuitos de OpenRouter tienen un límite de 50 peticiones al día por cuenta** (1000 si se compran 10 créditos) y cada informe del equipo gasta una petición por persona; con el límite agotado todos los informes fallan hasta el reinicio diario (00:00 UTC). Además hay límites por minuto compartidos. Si se agotan, la pantalla avisa de que el informe no pudo generarse y se puede reintentar. Para desactivarlo: borrar esas cinco líneas de `.env` y `sudo docker compose up -d`.

## 8. Límites

- Es una **demostración**: sin copias de seguridad, sin observabilidad y sin alta disponibilidad. Producción **no está habilitada**.
- Una sola instancia pequeña: puede ir lenta con varias personas usándola a la vez.
- Los informes dependen de un servicio gratuito de un tercero (cuotas, límites y disponibilidad variables): ver sección 7.
