# Implementation progress

## Overview

- Overall progress is 7 of 40 tasks completed.
- Current phase is Phase 2 — LLM Fundamentals.
- Latest completed task is TASK-009 — Implement Customer Sentiment and Urgency Analysis.
- TASK-010 implementation is in place. PostgreSQL verification is pending.

## Task activity

| Category | Tasks |
| --- | --- |
| Completed | TASK-003 through TASK-009 |
| In progress | None |
| Partially completed | TASK-001, TASK-002, and TASK-010 |
| Blocked | TASK-002 Docker health and persistence verification, TASK-001 Node.js 24 verification and fresh registry audit |

## TASK-010 verification

Classification and sentiment/urgency now use shared bounded JSON parsing, field-set checks, exact enum validation, printable text checks, and sanitized internal errors. Each service retains its prompt, result schema, and public errors. See the [structured-output architecture](../architecture/structured-output-validation.md).

| Check | Command | Result |
| --- | --- | --- |
| Django system check | `python manage.py check` | Passed. |
| Database connectivity | `python manage.py check_database` | Failed. Docker's engine pipe was unavailable after startup attempts and PostgreSQL on port 5433 did not respond. |
| Model and migration synchronization | `python manage.py makemigrations --check --dry-run` | No changes detected with development and test settings. The development database history check timed out. |
| Shared checks and service compatibility | `python -m pytest ai/tests -k structured` | 80 passed, 291 deselected. |
| All AI regressions | `python -m pytest ai/tests` | 371 passed, including 91 classification cases and 113 sentiment/urgency cases. |
| Database-free regression | `python -m pytest` | 466 passed, 267 PostgreSQL cases skipped as expected. |
| PostgreSQL regression | `python -m pytest -m postgres --ds=config.postgres_test_settings` | Execution blocked by connectivity. Collection-only mode selected 267 tests and deselected 466. |
| Backend quality and dependencies | `ruff check .`, `ruff format --check .`, `python -m pip check` | Passed. |
| Frontend regression | `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run test:run`, `npm.cmd run build` | Passed on Node.js 25.2.1, including 1 Vitest test. |

Verified on 2026-11-28. The remaining completion gate is a successful PostgreSQL regression run. Automated coverage used mocks and incurred no provider calls. The decoder now rejects non-finite numbers, responses over 16,384 characters, and nesting beyond 32 container levels.

## TASK-009 verification

`SentimentUrgencyAnalyzer` sends one role-separated `LLMClient` request and returns independent sentiment and urgency labels, two concise explanations, and available provider metadata. The `sentiment-urgency-v1` prompt and strict parser use the existing domain enums. See the [analysis architecture](../architecture/sentiment-urgency.md).

| Check | Command | Result |
| --- | --- | --- |
| Django system check | `python manage.py check` | Passed with LLM configuration unset. |
| PostgreSQL connectivity | `python manage.py check_database` | Failed because the local PostgreSQL service was unavailable. Docker's engine pipe was missing after a startup attempt. |
| Migration synchronization | `python manage.py makemigrations --check --dry-run` | No changes detected with development and test settings. The development database history check timed out. |
| Offline analysis command | `python manage.py analyze_sentiment --text "I need my replacement before tomorrow."` | Passed with LLM configuration unset. Input was validated and zero provider requests were sent. |
| AI suite | `python -m pytest ai/tests` | 291 passed, including 113 new analysis cases and 178 existing AI cases. |
| Database-free regression | `python -m pytest` | 386 passed, 267 PostgreSQL cases skipped. |
| PostgreSQL regression | `python -m pytest -m postgres --ds=config.postgres_test_settings` | The collection-only check selected 267 tests and deselected 386. Execution was blocked by the local database connection preflight. |
| Backend quality and dependencies | `ruff check .`, `ruff format --check .`, `python -m pip check` | Passed. |
| Frontend regression | `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run test:run`, `npm.cmd run build` | Passed on Node.js 25.2.1, including 1 Vitest test. |
| Live analysis | `python manage.py analyze_sentiment --text "I need my replacement before tomorrow." --live` | Unverified. Billable request authorization was not provided. The command passed mocked tests. |

The table records the initial verification on 2026-11-26. The developer subsequently reported 267 PostgreSQL tests passed after Docker was restored on port 5433, with one non-blocking pytest cache permission warning. They reported 386 database-free tests and 113 new sentiment/urgency tests passed, with no migration changes detected. That follow-up completes TASK-009. Live accuracy and injection resistance remain evaluation work.

## TASK-008 verification

`CustomerMessageClassifier` uses the existing `LLMClient` and `classification-v1` prompt to return one of seven support categories from one message body. It strictly validates the JSON response and preserves provider metadata and errors. The command validates inputs locally by default. See the [classification architecture](../architecture/message-classification.md).

| Check | Command | Result |
| --- | --- | --- |
| Django system, PostgreSQL, and migration checks | `python manage.py check`, `python manage.py check_database`, `python manage.py makemigrations --check --dry-run` | Passed with LLM configuration unset. No migration changes detected. |
| Local classification command | `python manage.py classify_message --text "Where is my order?"` | Passed. Validated the input and sent zero requests. |
| AI suite | `python -m pytest ai/tests` | 178 passed. Includes 91 classification and 87 existing LLM cases. |
| Database-free regression | `python -m pytest` | 273 passed, 267 skipped. |
| PostgreSQL regression | `python -m pytest -m postgres --ds=config.postgres_test_settings` | 267 passed, 273 deselected. Verified isolated database teardown. |
| Backend quality and dependencies | `ruff check .`, `ruff format --check .`, `python -m pip check` | Passed. |
| Frontend regression | `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run test:run`, `npm.cmd run build` | Passed on Node.js 25.2.1, including 1 Vitest test. |
| Live classification | `python manage.py classify_message --text "Where is my order?" --live` | Unverified. Billable request authorization was not provided. The command passed mocked tests. |

Verified on 2026-11-25. Mocked cases cover the seven categories, role isolation, multilingual and overlapping requests, parse failures, and provider errors. Live accuracy and prompt-injection resistance remain unverified. The current classifier considers a single message and may need additional context for ambiguous cases.

## TASK-007 verification

The `ai` package contains a synchronous provider-independent text client, the OpenAI Responses adapter, a reusable fake, and the `check_llm` management command. The adapter normalizes text, model, usage, and request ID metadata. It applies configurable HTTP timeouts and one bounded retry policy. See the [LLM integration architecture](../architecture/llm-integration.md).

| Check | Command | Result |
| --- | --- | --- |
| Django, PostgreSQL, and migration checks | `python manage.py check`, `python manage.py check_database`, `python manage.py makemigrations --check --dry-run` | Passed with the LLM key and model unset. No migration changes detected. |
| Local LLM configuration | `python manage.py check_llm` | Correctly refused a missing key. Passed with test-only configuration and confirmed zero requests. |
| Database-free suite | `python -m pytest` | 182 passed, 267 skipped. Includes 87 LLM tests. Provider tests use the real SDK with mocked HTTP transport. |
| PostgreSQL regressions | `python -m pytest -m postgres --ds=config.postgres_test_settings` | 267 passed, 182 deselected. Verified isolated database teardown. |
| Backend quality and dependencies | `ruff check .`, `ruff format --check .`, `python -m pip check` | Passed. OpenAI SDK 2.53.0 installed from a cached wheel verified against PyPI's SHA-256. |
| Frontend regressions | `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run test:run`, `npm.cmd run build` | Passed on Node.js 25.2.1, including 1 Vitest test. |
| Paid live check | `python manage.py check_llm --live` | Unverified. Billable request authorization was not provided. The command passed mocked tests. |

Verified on 2026-11-25. The model is explicit per environment. Project access, live performance, and usage remain unverified. The adapter accepts text and uses model-default sampling. Retried generation may incur extra charges, and the live command uses zero retries. Earlier task statuses were preserved.

## TASK-006 verification

The sample dataset adds 8 fictional customers, 18 conversations, and 53 messages across all seven scenario categories. `seed_support_data`, `--dry-run`, and `--clear` use a deterministic UUID inventory and an explicit local database guard. Cleanup verifies matching records and refuses unexpected children. See the [sample data reference](../development/sample-data.md).

| Check | Command | Result |
| --- | --- | --- |
| Django, PostgreSQL, and schema synchronization | `python manage.py check`, `python manage.py check_database`, `python manage.py makemigrations --check --dry-run` | Passed on local PostgreSQL. No migration changes detected. |
| Development preview and initial seed | `python manage.py seed_support_data --dry-run`, `python manage.py seed_support_data` | Preview and first seed each reported 8 customers, 18 conversations, and 53 messages. |
| Development repeat and cleanup preview | `python manage.py seed_support_data`, `python manage.py seed_support_data --clear --dry-run` | Second seed created zero rows and reused all 79. Cleanup preview identified all 79. Development sample rows remain available for exploration. |
| PostgreSQL suite | `python -m pytest -m postgres --ds=config.postgres_test_settings` | 267 passed, 95 deselected. Includes 24 new seed and API cases. Verified test database teardown. |
| Database-free suite | `python -m pytest` | 95 passed, 267 skipped. Includes 44 new inventory and environment cases. |
| Backend quality and dependencies | `ruff check .`, `ruff format --check .`, `python -m pip check` | Passed. |
| Frontend regression | `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run test:run`, `npm.cmd run build` | Passed on Node.js 25.2.1. Vitest passed 1 test. |

Verified on 2026-11-24. Destructive cleanup was verified only in the isolated PostgreSQL database. Keep the published dataset definitions stable for local databases seeded with this version. Development use assumes a local PostgreSQL server, including when its port is exposed by Docker.

## TASK-005 verification

Django sessions support CSRF bootstrap, username and password login, current-user profiles, and logout. The conversations and messages API checks support roles and operation-specific model permissions. Django groups are provisioned by `python manage.py provision_support_roles` after framework migrations. See the [authentication architecture](../architecture/authentication.md).

| Check | Command | Result |
| --- | --- | --- |
| Django and PostgreSQL | `python manage.py check`, `python manage.py check_database` | Passed against local PostgreSQL. |
| Migration state and role provisioning | `python manage.py makemigrations --check --dry-run`, `python manage.py showmigrations`, `python manage.py provision_support_roles` | Passed. Framework and support migrations were applied. The command configured both groups. No new schema migration was needed. |
| PostgreSQL authentication, API, and model suites | `python -m pytest -m postgres --ds=config.postgres_test_settings` | 243 passed, 49 deselected. Includes 41 account cases, 125 support API cases, 76 model cases, and 1 connection case. The reserved database was absent before and after the run. |
| Live HTTP authentication workflow | `accounts/tests/test_live_session.py` in the PostgreSQL suite | Passed using loopback Django and an HTTP cookie jar. Verified login, profile, conversation list, denied write without CSRF, valid write, logout, and old-session rejection. |
| Database-free regression suite | `python -m pytest` | 49 passed, 243 PostgreSQL tests skipped as expected. Includes 17 browser-policy and runtime settings cases. |
| Backend quality and dependencies | `ruff check .`, `ruff format --check .`, `python -m pip check` | Passed. |
| Frontend regression | `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run test:run`, `npm.cmd run build` | Passed on Node.js 25.2.1. Vitest passed 1 test. |

Verified on 2026-11-24. Role removal and individual permission revocation take effect on subsequent requests. The deployment assumptions are same-site HTTPS and backend-only session storage. The login-attempt throttle is process-local. Follow-up deployment controls include distributed rate limiting and trusted proxy integration. See the [authentication limits](../architecture/authentication.md#limits).

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

Verified on 2026-11-24 with the interim staff policy. TASK-005 subsequently replaced it with role and permission checks. Earlier task statuses are recorded in the roadmap.

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

After TASK-010 verification, TASK-011 — AI Draft Response Generation will reuse the LLM client, versioned prompts, structured-output validation, and existing support models where appropriate. See the [canonical roadmap](roadmap.md).
