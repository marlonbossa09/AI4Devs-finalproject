-- Aprovisionamiento de las bases de datos locales de SMARTWORK (desarrollo y pruebas).
--
-- Se ejecuta UNA vez, como superusuario del servidor PostgreSQL local, y no contiene secretos:
-- las contraseñas se pasan como variables de psql. Ejemplo (psql pide la contraseña del
-- superusuario de forma interactiva; no se escribe en ningún archivo):
--
--   psql -h 127.0.0.1 -U postgres -d postgres \
--        -v owner_password='...' -v app_password='...' \
--        -f backend/scripts/provision_db.sql
--
-- Roles (privilegios mínimos):
--   smartwork_owner  Propietario del esquema. Solo lo usan las migraciones y la semilla de
--                    desarrollo. No es superusuario.
--   smartwork_app    Rol de la aplicación. Sin DDL. Los permisos sobre cada tabla los concede
--                    la migración correspondiente, uno a uno (por ejemplo, solo INSERT y
--                    SELECT sobre la auditoría).
--
-- Se crean dos bases separadas: smartwork_dev (desarrollo) y smartwork_test (pruebas).

\set ON_ERROR_STOP on

CREATE ROLE smartwork_owner LOGIN PASSWORD :'owner_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE smartwork_app LOGIN PASSWORD :'app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

CREATE DATABASE smartwork_dev OWNER smartwork_owner;
CREATE DATABASE smartwork_test OWNER smartwork_owner;

REVOKE ALL ON DATABASE smartwork_dev FROM PUBLIC;
REVOKE ALL ON DATABASE smartwork_test FROM PUBLIC;
GRANT CONNECT ON DATABASE smartwork_dev TO smartwork_app;
GRANT CONNECT ON DATABASE smartwork_test TO smartwork_app;

\connect smartwork_dev
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO smartwork_app;

\connect smartwork_test
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO smartwork_app;
