#!/bin/sh
# Se ejecuta UNA vez, al crear el volumen de PostgreSQL. Crea los tres roles de privilegios mínimos y la base independiente de la demostración, como
# backend/scripts/provision_db.sql y provision_rol_de_provision.sql, pero con una sola base. Las contraseñas llegan por variables de entorno del contenedor
# y por variables de psql (nunca en una sentencia en claro ni en un argumento de proceso).
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v owner_pw="$SMARTWORK_OWNER_PASSWORD" -v app_pw="$SMARTWORK_APP_PASSWORD" -v prov_pw="$SMARTWORK_PROVISION_PASSWORD" -v db="$SMARTWORK_DB" <<'SQL'
CREATE ROLE smartwork_owner LOGIN PASSWORD :'owner_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE smartwork_app LOGIN PASSWORD :'app_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE smartwork_provision LOGIN PASSWORD :'prov_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE DATABASE :"db" OWNER smartwork_owner;
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO smartwork_app, smartwork_provision;
\connect :"db"
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO smartwork_app, smartwork_provision;
SQL
