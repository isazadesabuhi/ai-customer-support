# Implementation progress

## Overview

- Overall progress is 0 of 40 tasks completed.
- Current phase is Phase 1 — Foundation.
- Current task is TASK-002 — Configure Django and PostgreSQL.

## Task activity

| Category | Tasks |
| --- | --- |
| Completed | None |
| In progress | None |
| Partially completed | TASK-001 and TASK-002 |
| Blocked | TASK-002 live database verification and TASK-001 Node.js 24 verification and fresh registry audit |

## TASK-002 verification

Compose defines PostgreSQL 17.12 with a loopback port, a named volume, and a readiness check. Django uses validated PostgreSQL settings and provides `check_database`. PostgreSQL integration tests are opt-in and use a reserved test database.

| Check | Command | Result |
| --- | --- | --- |
| Compose configuration | `docker compose config --quiet`, `docker compose config --format json` | Passed. Verified the service, image, named volume, health check, role mapping, and default and custom loopback ports. A missing password was rejected. |
| Container startup and status | `docker compose up -d --wait db`, `docker compose ps` under an isolated Compose project name | Failed because the Docker Engine named pipe was unavailable. Container health and readiness remain unverified. |
| Bootstrap shell script | Git Bash `bash -n docker/postgres/10-create-app-role.sh` | Passed syntax validation. SQL execution awaits a running container. |
| Django checks | `.venv/Scripts/python.exe manage.py check` | Passed with PostgreSQL settings. Missing password and invalid port cases produced configuration errors. |
| Database connection | `.venv/Scripts/python.exe manage.py check_database` | Against an unused loopback port, returned exit 1 and a sanitized connection error. Successful connection and wrong-password behavior await PostgreSQL. |
| Migrations and persistence | `manage.py migrate`, `manage.py showmigrations`, Compose stop/start | Pending a running service. |
| Backend tests | `.venv/Scripts/python.exe -m pytest` | 32 passed, including 19 database configuration cases, 2 connectivity command cases, and 11 existing cases. The PostgreSQL integration test was skipped. |
| Backend quality | `.venv/Scripts/ruff.exe check .`, `.venv/Scripts/ruff.exe format --check .` | Passed. |
| Dependencies | `.venv/Scripts/python.exe -m pip check` and Psycopg/Django backend imports | Passed using the cached Psycopg 3.3.6 binary wheels. |
| Frontend regression | `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run test:run`, `npm.cmd run build` | Passed on Node.js 25.2.1. Vitest passed 1 test. |

Docker CLI 29.6.2 and Compose 5.3.1 were available. Both the default and Docker Desktop Linux engine pipes were absent after attempting to start Desktop. A healthy service is needed to verify the bootstrap role, successful queries, framework migrations, the PostgreSQL integration test, and persistence after stop/start.

## TASK-001 verification

Reverified on 2026-11-23 using Windows, the existing Python 3.12.10 virtual environment, Node.js 25.2.1, and npm 11.6.4. Frontend checks ran on Node.js 25.2.1. The required Node.js 24 LTS runtime was unavailable in this session.

| Check | Command | Result |
| --- | --- | --- |
| Frontend install | `npm ci` | Successful in the developer's local run, with 456 packages installed. Used that installation for the checks below. |
| Frontend lint | `npm.cmd run lint` | Passed with zero warnings after naming the PostCSS configuration export. |
| Frontend types | `npm.cmd run typecheck` | Passed. |
| Frontend formatting | `npm.cmd run format:check` | Passed. |
| Frontend smoke test | `npm.cmd run test:run` | 1 passed. |
| Frontend production build | `npm.cmd run build` | Passed. The Turbopack root warning was absent. |
| Frontend development server | `node frontend/node_modules/next/dist/bin/next dev frontend --hostname 127.0.0.1 --port 3010` | Started from the repository root and returned HTTP 200 at `/` with the expected H1. The Turbopack root warning was absent. |
| Django system check | `.venv/Scripts/python.exe manage.py check` | Passed in local development without a supplied key. |
| Ruff lint | `.venv/Scripts/ruff.exe check .` | Passed. |
| Ruff formatting | `.venv/Scripts/ruff.exe format --check .` | Passed for 11 files. |
| Backend tests | `.venv/Scripts/python.exe -m pytest` | All 11 passed, including 8 signing-key cases. |

App commands run from their respective directories except for the development-server command shown from the repository root. The frontend lockfile retained the same SHA-256 hash.

## Frontend dependency audit

`npm audit --json` could not reach npm's advisory endpoint in this session (`EACCES`). The saved successful registry response from this project's local `npm audit`, npm's advisory cache, and `npm ls` identify one underlying advisory across seven moderate development-dependency entries. [GHSA-g3hv-75wg-m249 / CVE-2026-118764](https://github.com/advisories/GHSA-g3hv-75wg-m249)

All paths start at `eslint-config-next@16.4.6`. The TypeScript ESLint packages are locked at `8.64.0`. The paths below show where each reported package reaches the affected copy of minimatch.

| Reported package | Dependency path after `eslint-config-next` |
| --- | --- |
| `minimatch@10.2.6` | `typescript-eslint → typescript-estree → minimatch` |
| `@typescript-eslint/typescript-estree` | `typescript-eslint → typescript-estree → minimatch` |
| `@typescript-eslint/parser` | `typescript-eslint → parser → typescript-estree → minimatch` |
| `@typescript-eslint/utils` | `typescript-eslint → utils → typescript-estree → minimatch` |
| `@typescript-eslint/type-utils` | `typescript-eslint → eslint-plugin → type-utils → typescript-estree → minimatch` |
| `@typescript-eslint/eslint-plugin` | `typescript-eslint → eslint-plugin → type-utils → typescript-estree → minimatch` |
| `typescript-eslint` | `typescript-eslint → typescript-estree → minimatch` |

Minimatch `11.0.1` is the first patched release. TypeScript ESLint `8.73.0` adopts `minimatch@^11.0.1` and fits the Next.js lint config's existing `^8.56.0` range. Updating the TypeScript ESLint packages together is a same-major remediation. Forcing minimatch 11 into the old parser's `^10.2.2` range would cross a major-version boundary outside its declared compatibility. The candidate release was checked against package metadata. Its installation and audit still need verification. [TypeScript ESLint 8.73.0 parser dependency](https://github.com/typescript-eslint/typescript-eslint/blob/v8.73.0/packages/typescript-estree/package.json)

## TASK-001 known issues

- Repeat the frontend install and verification on Node.js 24 LTS and run a fresh registry audit. See the [Windows recovery steps](../development/troubleshooting.md#windows-npm-install-recovery).
- ESLint 9.39.5 is end of life. ESLint 10 is supported by ESLint upstream, but the installed import, React, and JSX accessibility plugins declare peers only through ESLint 9. Move to ESLint 10 with a Next.js lint configuration whose plugin peers support it, then verify a clean install and lint on Node.js 24. [ESLint version support](https://eslint.org/version-support/) · [ESLint 10 migration guide](https://eslint.org/docs/latest/use/migrate-to-10.0.0)

## Next planned task

TASK-003 — Design Customer Support Data Models will introduce the models for customers, conversations, messages, AI analysis, and draft responses. See the [canonical roadmap](roadmap.md).
