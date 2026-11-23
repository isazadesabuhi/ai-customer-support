# Local development setup

Run each app in its own terminal from the indicated directory. The commands below are developer setup and verification instructions. See the [progress tracker](../tasks/progress.md) for the commands actually executed and their results.

## Prerequisites

| Tool | Project baseline |
| --- | --- |
| Node.js | 24 LTS, version 24.22.3 or a later 24.x patch |
| npm | 11.x |
| Python | 3.12–3.14. Prefer the latest Python 3.14 patch for a fresh installation. |
| Git | A maintained Git release |

Next.js 16 supports Node.js 24 LTS. Vitest, Vite, and jsdom also support this line. Django 5.2 LTS and Django REST Framework support the selected Python series. [Node.js releases](https://nodejs.org/en/about/previous-releases) · [Next.js installation](https://nextjs.org/docs/app/getting-started/installation) · [Django Python compatibility](https://docs.djangoproject.com/en/5.2/faq/install/) · [DRF 3.18.3 metadata](https://pypi.org/project/djangorestframework/3.18.3/)

Check `node --version`, `npm --version` (`npm.cmd --version` in PowerShell), and `python --version` (`python3 --version` where applicable).

| Area | Initial pins |
| --- | --- |
| Frontend | Next.js 16.4.6, React 19.3.1, Tailwind CSS 4.3.3, TypeScript 5.9.3 |
| Frontend checks | ESLint 9.39.5, Prettier 3.8.1, Vitest 4.1.12, Vite 8.3.8, React Testing Library 16.3.2, jsdom 29.1.1 |
| Backend | Django 5.2.19, Django REST Framework 3.18.3 |
| Backend checks | Ruff 0.16.7, Pytest 9.1.1, pytest-django 4.14.0 |

The [frontend manifest](../../frontend/package.json) pins direct dependencies and the [npm lockfile](../../frontend/package-lock.json) records the resolved graph. The [runtime requirements](../../backend/requirements/base.txt) and [development requirements](../../backend/requirements/dev.txt) pin Python packages and their transitive dependencies. Platform markers select Windows-only dependencies.

## Windows PowerShell

From the repository root, set up and start Django.

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements/dev.txt
$env:DJANGO_ENV = 'development'
python manage.py runserver 127.0.0.1:8000
```

If activation is restricted, use `.\.venv\Scripts\python.exe` in place of `python`. The [troubleshooting guide](troubleshooting.md) lists direct paths for the other tools.

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

From the repository root, set up and start Django.

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/dev.txt
export DJANGO_ENV=development
python manage.py runserver 127.0.0.1:8000
```

In a separate terminal from the repository root, start Next.js.

```sh
cd frontend
npm ci
npm run dev -- --hostname 127.0.0.1
```

Open `http://127.0.0.1:3000/` for the foundation page. Django listens at `http://127.0.0.1:8000/`, where a 404 confirms the empty URL configuration. Django may report pending built-in migrations. You can run the foundation checks and verify the root response before applying them.

## Local configuration

Set Django configuration in the shell that starts Django. Opt in to local development with `DJANGO_ENV=development` to use a generated signing key.

| Variable | Default | Use |
| --- | --- | --- |
| `DJANGO_ENV` | Unset | The value `development` enables the local signing-key fallback. |
| `DJANGO_DEBUG` | `false` | Set to `true` for detailed local errors when running on loopback. |
| `DJANGO_SECRET_KEY` | Required outside local development | Supply a private, non-empty signing key. In local development, a missing or blank value generates a per-process key. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma-separated hostnames or IPs without ports. |

The [backend environment example](../../backend/.env.example) lists the supported keys. Supply values through the process environment, such as `$env:DJANGO_DEBUG = 'true'` in PowerShell or `export DJANGO_DEBUG=true` in a POSIX shell. The foundation page runs with defaults. Next.js can read local `.env.local` files when frontend configuration is added. Use `NEXT_PUBLIC_` only for values intended to be visible in the browser.

Pytest loads dedicated test settings with a test-only signing key. Run it from `backend/` without setting a runtime key.

## Verify the setup

In `frontend/`, run `npm run lint`, `npm run typecheck`, `npm run format:check`, `npm run test:run`, and `npm run build`. Use `npm.cmd` in Windows PowerShell. Use `npm run format` when you intend to rewrite files.

In `backend/` with the virtual environment active, run `python manage.py check` in the local development shell configured above, or supply an explicit `DJANGO_SECRET_KEY`. Run `ruff check .`, `ruff format --check .`, and `python -m pytest`. Use `ruff check --fix .` to apply safe lint fixes and sort imports and `ruff format .` to apply formatting.

Use `npm ci` for a clean frontend install and a fresh virtual environment for a clean backend install. When updating dependencies, keep direct and transitive pins in sync, run `python -m pip check`, and verify the checks again.
