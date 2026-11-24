# Testing

Small automated checks catch configuration and rendering regressions before a developer has to run both apps. Formatting checks keep layout consistent, linting flags problematic patterns, and type checking validates TypeScript contracts. Tests exercise behavior.

| Scope | Command | Coverage |
| --- | --- | --- |
| Frontend | `npm run test:run` | Vitest renders the landing page with React Testing Library and jsdom and verifies its level-one heading. |
| Backend database-free | `python -m pytest -m "not postgres"` | Tests environment parsing, signing keys, CSRF bootstrap, CORS, the connectivity command with a mocked cursor, and Django smoke checks. |
| PostgreSQL integration | `python -m pytest -m postgres --ds=config.postgres_test_settings` | Runs model and constraint tests, conversation and message APIs, and authentication, roles, and session security checks. |

Run each command from its app directory. Use `npm.cmd` and `.\.venv\Scripts\python.exe` in Windows PowerShell. Use `npm run test` for interactive frontend watch mode.

The frontend and database-free suites run without services or database credentials. Plain `python -m pytest` uses a dummy database backend and skips the marked PostgreSQL tests. Run `ruff check .` and `ruff format --check .` alongside the backend tests.

The integration command requires a healthy local Compose database and the variables from the [setup guide](setup.md#windows-powershell). The dedicated settings require IPv4 loopback and reserve `test_ai_customer_support`. Django uses the server's `postgres` maintenance database to create the test database, applies framework migrations to the test database, and drops the test database after a normal run. The local non-superuser role has `CREATEDB` for this lifecycle. Development tables remain outside the test database, which keeps tests repeatable and protects working data.

Support model tests live in `support/tests/`. Run that directory with the same `--ds=config.postgres_test_settings` option to focus on the support app. Validation tests call `full_clean()`. Constraint tests write invalid data directly through the ORM and expect `IntegrityError`. They use an inner `transaction.atomic()` savepoint so a rejected write can roll back without breaking the test's connection. Test fixtures are isolated per test.

## Conversation and message API tests

From `backend/` with the virtual environment and local PostgreSQL settings loaded, run the full PostgreSQL suite above. Add `-k test_api` to select the API tests.

The tests use DRF's `APIClient` to send requests through URL routing, permission checks, serializers, and PostgreSQL. Most payload and query tests use `force_authenticate` to focus on API behavior. Role-matrix tests use sessions for support roles, ordinary staff, and superusers. A regression case verifies that Basic credentials are rejected.

The suite tests the response field lists, pagination limits and ordering, status filters, rejected writes, and parent conversation isolation. Permission tests compare denied responses for existing, missing, and malformed UUIDs. The query tests assert upper bounds with several records, so a per-row lookup would fail the test without requiring an exact query count. See the [API reference](../api/endpoints.md).

## Authentication security tests

Add `accounts/tests` to the PostgreSQL command to focus on authentication. The test database fixtures provision groups and generate test-only accounts. `APIClient(enforce_csrf_checks=True)` exercises real Django login with CSRF cookies and headers, then verifies session rotation, permission revocation, expiry, logout, and replay rejection. Forced authentication skips credentials, cookies, and CSRF, so it fits serializer tests where those concerns have separate coverage.

The `test_live_session.py` check uses a Django loopback server and an HTTP client with a cookie jar. It runs login, profile and conversation reads, a write with and without CSRF, logout, and stale-cookie rejection against the isolated PostgreSQL database. Database-free tests cover allowed and rejected origins and environment defaults. PostgreSQL tests verify the actual cookie flags. See the [authentication architecture](../architecture/authentication.md).

Future tests should mock external API requests at the service boundary and exercise both successful and failed responses. Add Playwright for end-to-end flows once the frontend and API communicate.
