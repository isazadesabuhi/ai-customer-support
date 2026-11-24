# Local development setup

Run each app in its own terminal from the indicated directory. The commands below are developer setup and verification instructions. See the [progress tracker](../tasks/progress.md) for the commands actually executed and their results.

## Prerequisites

| Tool | Project baseline |
| --- | --- |
| Node.js | 24 LTS, version 24.22.3 or a later 24.x patch |
| npm | 11.x |
| Python | 3.12–3.14. Prefer the latest Python 3.14 patch for a fresh installation. |
| Docker | A running Docker Engine with the Docker Compose plugin. On Windows, start Docker Desktop in Linux container mode. |
| Git | A maintained Git release |

Next.js 16 supports Node.js 24 LTS. Vitest, Vite, and jsdom also support this line. Django 5.2 LTS and Django REST Framework support the selected Python series. [Node.js releases](https://nodejs.org/en/about/previous-releases) · [Next.js installation](https://nextjs.org/docs/app/getting-started/installation) · [Django Python compatibility](https://docs.djangoproject.com/en/5.2/faq/install/) · [DRF 3.18.3 metadata](https://pypi.org/project/djangorestframework/3.18.3/)

Check `node --version`, `npm --version` (`npm.cmd --version` in PowerShell), and `python --version` (`python3 --version` where applicable).

| Area | Initial pins |
| --- | --- |
| Frontend | Next.js 16.4.6, React 19.3.1, Tailwind CSS 4.3.3, TypeScript 5.9.3 |
| Frontend checks | ESLint 9.39.5, Prettier 3.8.1, Vitest 4.1.12, Vite 8.3.8, React Testing Library 16.3.2, jsdom 29.1.1 |
| Backend | Django 5.2.19, Django REST Framework 3.18.3, Psycopg 3.3.6 with binary wheels |
| Database | PostgreSQL 17.12 official Docker image |
| Backend checks | Ruff 0.16.7, Pytest 9.1.1, pytest-django 4.14.0 |

The [frontend manifest](../../frontend/package.json) pins direct dependencies and the [npm lockfile](../../frontend/package-lock.json) records the resolved graph. The [runtime requirements](../../backend/requirements/base.txt) and [development requirements](../../backend/requirements/dev.txt) pin Python packages and their transitive dependencies. Platform markers select Windows-only dependencies.

## Windows PowerShell

Start Docker Desktop and wait until its engine is running. From the repository root, create the local environment file once.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Open `.env` in your editor and set two different development-only values for `POSTGRES_PASSWORD` and `POSTGRES_ADMIN_PASSWORD`. Use unquoted hexadecimal values so the same file works with the shell commands below. The file is ignored by Git. Compose loads the root `.env` for interpolation, and the service receives the variables mapped in `compose.yaml`. Shell variables with the same names take precedence. [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) · [Compose variable interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)

```powershell
docker compose config --quiet
docker compose up -d --wait db
docker compose ps
```

`config --quiet` validates without printing resolved credentials. An image is a versioned package containing PostgreSQL and its runtime. Compose starts a container from that image, attaches a default project network and persistent volume, and publishes the database through the host loopback interface. Startup means the container process exists. Readiness means `pg_isready` can reach the server accepting connections. Django's query also verifies the app role and its password.

Load only the Django database variables into the current PowerShell process. The admin password is used by Compose to initialize PostgreSQL.

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^(POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD|DB_HOST|DB_PORT)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}
Set-Location backend
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements/dev.txt
$env:DJANGO_ENV = 'development'
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py check_database
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Using the virtual environment's executable directly works with PowerShell execution policies that restrict activation scripts. If a database command fails, check the [troubleshooting guide](troubleshooting.md#postgresql-and-docker-compose) before proceeding.

Open a separate PowerShell terminal with Node.js 24 LTS and npm 11 on `PATH`. From the repository root, install the frontend and start Next.js.

```powershell
Set-Location frontend
node --version
npm.cmd --version
npm.cmd ci
npm.cmd run dev -- --hostname 127.0.0.1
```

If `npm.cmd ci` reports a registry or cache error, use the [Windows npm recovery steps](troubleshooting.md#windows-npm-install-recovery).

## macOS and Linux

Start Docker Desktop or Docker Engine. From the repository root, copy `.env.example` to `.env` once and set the two passwords as described above. Source only your own trusted local file.

```sh
docker compose config --quiet
docker compose up -d --wait db
docker compose ps
set -a
. ./.env
set +a
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/dev.txt
export DJANGO_ENV=development
python manage.py check
python manage.py check_database
python manage.py migrate
python manage.py showmigrations
python manage.py runserver 127.0.0.1:8000
```

In a separate terminal from the repository root, start Next.js.

```sh
cd frontend
npm ci
npm run dev -- --hostname 127.0.0.1
```

Open `http://127.0.0.1:3000/` for the foundation page. Django listens at `http://127.0.0.1:8000/`, where a 404 is expected with the empty URL configuration.

## Stop and restart PostgreSQL

Stop Django, then run `docker compose stop db` from the repository root. `docker compose up -d --wait db` starts it again with the same `postgres_data` volume. To verify persistence, run `showmigrations` before and after the stop/start cycle. The same migration entries should remain checked. Deleting the volume permanently removes the local database and its migration history. Keep the volume during routine shutdown.

## Local configuration

Set Django configuration in the shell that starts Django. Opt in to local development with `DJANGO_ENV=development` to use a generated signing key.

| Variable | Default | Use |
| --- | --- | --- |
| `POSTGRES_DB` | Required | Application database name. The example uses `ai_customer_support`. System databases and `test_ai_customer_support` are reserved. |
| `POSTGRES_USER` | Required | Local non-superuser application role. The example uses `ai_support_dev`. |
| `POSTGRES_PASSWORD` | Required | Private local password for the app role. |
| `POSTGRES_ADMIN_PASSWORD` | Required by Compose | Separate private password for the local bootstrap superuser. Django uses the app role. |
| `DB_HOST` | `127.0.0.1` | Django database host. PostgreSQL integration tests require this loopback address. |
| `DB_PORT` | `5432` | Host port used by Compose and Django. Valid values are 1–65535. |
| `DJANGO_ENV` | Unset | The value `development` enables the local signing-key fallback. |
| `DJANGO_DEBUG` | `false` | Set to `true` for detailed local errors when running on loopback. |
| `DJANGO_SECRET_KEY` | Required outside local development | Supply a private, non-empty signing key. In local development, a missing or blank value generates a per-process key. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma-separated hostnames or IPs without ports. |

The [root environment example](../../.env.example) lists database variables. The [backend environment example](../../backend/.env.example) covers Django-specific settings. Django reads the process environment. The frontend foundation page runs with defaults. Use `NEXT_PUBLIC_` only for values intended to be visible in the browser.

Pytest defaults to database-free test settings with a test-only signing key. With PostgreSQL ready and the database variables loaded, run `python -m pytest -m postgres --ds=config.postgres_test_settings` from `backend/` to verify the isolated test database. Use the virtual environment's executable on Windows. See the [testing guide](testing.md).

## Verify the setup

In `frontend/`, run `npm run lint`, `npm run typecheck`, `npm run format:check`, `npm run test:run`, and `npm run build`. Use `npm.cmd` in Windows PowerShell. Use `npm run format` when you intend to rewrite files.

In `backend/` with the virtual environment active, run `python manage.py check` in the configured development shell. Run `ruff check .`, `ruff format --check .`, and `python -m pytest`. Use `ruff check --fix .` to apply safe lint fixes and sort imports and `ruff format .` to apply formatting.

Use `npm ci` for a clean frontend install and a fresh virtual environment for a clean backend install. When updating dependencies, keep direct and transitive pins in sync, run `python -m pip check`, and verify the checks again.

## Support migrations

Start the local PostgreSQL service and load the existing database variables using the steps above. In `backend/`, generate a migration only when you change the models. The initial support migration is already included in `support/migrations/`.

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations support
.\.venv\Scripts\python.exe manage.py migrate --plan
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py showmigrations support
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Review the generated operations and migration plan before applying changes. `showmigrations` reads the PostgreSQL migration history. A checked `0001_initial` entry indicates that the schema is applied. The dry run detects model changes that still need a migration. Use the equivalent virtual environment's `python` on macOS or Linux.
