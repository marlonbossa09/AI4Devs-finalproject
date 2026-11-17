-- Rol de PostgreSQL de provisión, SOLO para preparar la base de pruebas local (M1-T2 y siguientes).
--
-- Lo ejecuta UNA vez quien administra el servidor local. Las migraciones conceden al rol de provisión permisos por tabla,
-- pero no pueden crear roles (el rol propietario no tiene CREATEROLE): hay que crear el rol ANTES de aplicar la migración 0009.
--
-- Garantías de este script:
--   * La contraseña NUNCA es un argumento de proceso ni se escribe en una sentencia SQL: la pide ``\password`` sin eco,
--     la cifra en el cliente (SCRAM) y envía solo el verificador. No hay -v ni PGPASSWORD con la contraseña del rol.
--   * Solo prepara ``smartwork_test``. Rechaza cualquier otra base (en particular ``smartwork_app``): ni se conecta a ella
--     ni le concede nada. Preparar otra base requiere un procedimiento distinto y autorizado expresamente.
--   * No modifica roles ni privilegios existentes: si el rol ya existe, no se altera (ni se le cambia la contraseña); solo se
--     verifica que no tenga privilegios de administración. Los permisos sobre las tablas los concede cada migración, uno a uno.
--   * No toca ningún otro rol, base, esquema ni objeto. El rol queda sin superusuario, sin crear bases ni roles, sin
--     replicación y sin saltarse la seguridad por filas.
--
-- Uso en Windows (PowerShell), como superusuario del servidor local; psql pide la contraseña de ese superusuario y después la
-- del rol nuevo (dos veces). Ajuste la ruta de psql a su instalación:
--
--   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 127.0.0.1 -U postgres -d postgres `
--       -v base=smartwork_test -f backend\scripts\provision_rol_de_provision.sql
--
-- Después, en backend/.env (archivo ignorado por Git): TEST_PROVISION_DATABASE_URL=postgresql+psycopg://smartwork_provision:<contraseña>@127.0.0.1:5432/smartwork_test
-- El nombre del rol debe coincidir con PROVISION_DB_ROLE (por defecto, smartwork_provision).
--
-- Si el servidor tiene log_statement en ddl o all, el registro del servidor contendrá el verificador SCRAM (no la contraseña).

\set ON_ERROR_STOP on

-- 1. Solo la base de pruebas local.
\if :{?base}
\else
  \echo 'Falta -v base=smartwork_test'
  DO $$ BEGIN RAISE EXCEPTION 'Falta la variable base'; END $$;
\endif
SELECT (:'base' = 'smartwork_test') AS base_permitida \gset
\if :base_permitida
\else
  DO $$ BEGIN RAISE EXCEPTION 'Este script solo prepara la base de pruebas smartwork_test'; END $$;
\endif

-- 2. El rol se crea solo si no existe. Sin contraseña en la sentencia; sin permisos de administración.
SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'smartwork_provision') AS rol_nuevo \gset
\if :rol_nuevo
  CREATE ROLE smartwork_provision LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  \password smartwork_provision
\endif

-- 3. Un rol ya existente no se altera, pero no se acepta si tiene privilegios de administración.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'smartwork_provision'
             AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)) THEN
    RAISE EXCEPTION 'El rol smartwork_provision existe con privilegios de administración: no se modifica; revíselo manualmente';
  END IF;
END $$;

-- 4. Único permiso de este script: conectar a la base de pruebas y usar su esquema. Nada sobre tablas.
GRANT CONNECT ON DATABASE :"base" TO smartwork_provision;
\connect :"base"
GRANT USAGE ON SCHEMA public TO smartwork_provision;
