# Implementation progress

## Overview

- Overall progress is 2 of 40 tasks completed.
- Current phase is Phase 1 — Foundation.
- Latest completed task is TASK-004 — Implement Conversation REST APIs.

## Task activity

| Category | Tasks |
| --- | --- |
| Completed | TASK-003 and TASK-004 |
| In progress | None |
| Partially completed | TASK-001 and TASK-002 |
| Blocked | TASK-002 Docker health and persistence verification, TASK-001 Node.js 24 verification and fresh registry audit |

## TASK-004 verification

Five staff-only DRF operations list, create, and retrieve conversations and list and create their messages. The API uses explicit UUID lookups, validated status filters, stable page-number pagination, and strict JSON inputs. Nested routes authorize the parent and derive message ownership from the path. Agent messages are the only supported message creation operation. See the [API reference](../api/endpoints.md).

| Check | Command | Result |
| --- | --- | --- |
| Django system and database checks | `python manage.py check`, `python manage.py check_database` | Passed against the local PostgreSQL service. |
| Migration synchronization | `python manage.py makemigrations --check --dry-run` | Passed. No changes detected. |
| PostgreSQL API and regression suite | `python -m pytest -m postgres --ds=config.postgres_test_settings` | 174 passed. This includes 97 new API cases, 76 existing model cases, and 1 connectivity case. The reserved database was absent before and after the run. |
| Database-free regression suite | `python -m pytest` | 32 passed. The 174 PostgreSQL cases were skipped in this mode. |
| Backend quality and dependencies | `ruff check .`, `ruff format --check .`, `python -m pip check` | Passed. |
| Frontend regression | `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run test:run`, `npm.cmd run build` | Passed on Node.js 25.2.1. Vitest passed 1 test. |

Verified on 2026-11-24. The API uses the interim single-company policy. All authenticated staff can access support records. Formal authentication workflows and more specific authorization rules are planned for TASK-005. Earlier task statuses are recorded in the roadmap.

## TASK-003 verification

The `support` app defines Customer, Conversation, Message, AIAnalysis, and DraftResponse. The initial migration adds five tables, model constraints, and five explicit query indexes. See the [support data model](../architecture/data-model.md) for relationships, deletion behavior, and validation boundaries.

| Check | Command | Result |
| --- | --- | --- |
| Django system and database checks | `python manage.py check`, `python manage.py check_database` | Passed on local PostgreSQL. |
| Migration generation and review | `python manage.py makemigrations support` and review of `support/migrations/0001_initial.py` | Generated successfully. The migration contains only table creation, indexes, and constraints. |
| Model and migration synchronization | `python manage.py makemigrations --check --dry-run` | Passed against reachable PostgreSQL. No changes detected. |
| Development migration | `python manage.py migrate` and `python manage.py showmigrations support` | Applied `support.0001_initial`. Verified five tables, primary and foreign keys, named constraints, and query indexes. A second `migrate` had nothing to apply and existing migration history was preserved. |
| Database-free backend suite | `python -m pytest` | 32 passed. The 77 PostgreSQL cases were skipped in this mode. |
| PostgreSQL suite | `python -m pytest -m postgres --ds=config.postgres_test_settings` | 77 passed, including 76 support cases and the existing connectivity case. Verified test database teardown. |
| Backend quality and dependencies | `ruff check .`, `ruff format --check .`, `python -m pip check` | Passed. |
| Frontend regression | `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run test:run`, `npm.cmd run build` | Passed on Node.js 25.2.1. Vitest passed 1 test. |

Verified on 2026-11-24. Once PostgreSQL became reachable, all required TASK-003 checks passed. The development migration was additive. The only test change after the first PostgreSQL run was to check the pending-draft index predicate through PostgreSQL's catalog because Django's B-tree introspection omits that predicate. See the [migration guide](../development/setup.md#support-migrations) and [testing guide](../development/testing.md). Earlier task statuses are recorded in the roadmap.

The current schema holds one analysis per message. Email format, text length, and the analysis sender rule are checked at the model validation boundary. See the [support data model](../architecture/data-model.md#indexes-and-integrity).

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

TASK-005 — Implement Authentication and Authorization will introduce formal authentication workflows and permission rules. See the [canonical roadmap](roadmap.md).
