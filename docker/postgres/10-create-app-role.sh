#!/bin/sh
(
  set -eu

  case "$POSTGRES_DB" in
    postgres|template0|template1|test_ai_customer_support)
      printf '%s\n' 'POSTGRES_DB must be an application database name.' >&2
      exit 1
      ;;
  esac

  psql --no-psqlrc --no-password --set=ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv app_user APP_DB_USER
\getenv app_database POSTGRES_DB
CREATE ROLE :"app_user" LOGIN NOSUPERUSER CREATEDB NOCREATEROLE NOREPLICATION;
ALTER DATABASE :"app_database" OWNER TO :"app_user";
SQL

  # The image's initialization server uses a local Unix socket. psql encrypts the
  # password before sending it, so it does not appear in SQL statements or argv.
  printf '%s\n%s\n' "$APP_DB_PASSWORD" "$APP_DB_PASSWORD" |
    psql --no-psqlrc --no-password --set=ON_ERROR_STOP=1 \
      --username "$APP_DB_USER" --dbname "$POSTGRES_DB" --command='\password'
)
