# Architecture decision records

Use these fields for future records.

- **Title** describes the decision.
- **Status** records whether the decision is proposed, accepted, or superseded.
- **Context** names the problem and constraints.
- **Decision** records the chosen approach.
- **Alternatives Considered** notes the choices evaluated.
- **Consequences** describes tradeoffs and follow-up work.
- **Date** records the decision date.

## ADR-001 · Use a monorepo

- **Status** Accepted
- **Context** A support workflow will eventually span the UI, API, and documentation.
- **Decision** Keep frontend, backend, and documentation in one Git repository.
- **Alternatives Considered** Independent repositories with a shared contract package.
- **Consequences** Related changes can be reviewed together. Build and dependency commands still run in each app directory.
- **Date** 2026-11-23

## ADR-002 · Separate Next.js and Django processes

- **Status** Accepted
- **Context** The UI and future backend have distinct framework and runtime requirements.
- **Decision** Use Next.js for UI rendering and Django REST Framework for the future HTTP API.
- **Alternatives Considered** Django templates for the UI or a single Next.js application with server routes.
- **Consequences** Each app keeps framework-native tooling. API contracts, authentication, and integration testing will need explicit coordination when the apps connect.
- **Date** 2026-11-23

## ADR-003 · Use npm and pip

- **Status** Accepted
- **Context** The initial team needs standard, reproducible installs on Windows and Unix-like systems.
- **Decision** Use npm with a frontend lockfile and pip with separately pinned runtime and development requirements.
- **Alternatives Considered** pnpm for the frontend and a Python locking tool such as uv or pip-tools.
- **Consequences** A small toolchain is easy to learn. Updating Python dependencies requires reviewing transitive pins and checking the resolved environment.
- **Date** 2026-11-23

## ADR-004 · Run local PostgreSQL with Docker Compose

- **Status** Accepted
- **Context** Django needs a relational database for future support data and a reproducible environment on Windows and Unix-like systems.
- **Decision** Pin the official PostgreSQL 17.12 image and use synchronous Psycopg 3 binary wheels. Compose manages the database and persistent volume. Django and Next.js run on the host. The app connects through a loopback port as a separate non-superuser role. Opt-in PostgreSQL tests use a reserved test database and Django's test database lifecycle.
- **Alternatives Considered** A manually installed PostgreSQL service, an all-container application stack, and retaining SQLite for development.
- **Consequences** A pinned image and named volume make startup and restart predictable. The host workflow keeps the existing virtual environment and frontend tooling. Database integration requires a Docker engine, and the local application role needs `CREATEDB` for pytest-django. Database-free tests remain available without the service.
- **Date** 2026-11-23

## ADR-005 · Model the support conversation lifecycle

- **Status** Accepted
- **Context** The support domain needs stable identifiers, consistent customer identity, message-level AI records, and reliable review metadata.
- **Decision** Generate UUIDs in Python for the five support models. Validate normalized customer email and enforce case-insensitive uniqueness with a PostgreSQL expression index. Protect referenced customers and reviewers. Cascade conversation and message deletion to their owned records. Give each message one current analysis and multiple drafts. Enforce draft status and review metadata together with a database check.
- **Alternatives Considered** Sequential IDs, case-sensitive email uniqueness, one analysis history table, and nulling reviewer references on deletion.
- **Consequences** UUIDs work before insertion and cost more index space than integer IDs. Email case variants map to one customer. Protecting references can require deliberate data-retention decisions later. The single current analysis simplifies lookups. An analysis history would need a schema change. Drafts retain separate attempts and review metadata.
- **Date** 2026-11-24

## ADR-006 · Expose conversation and message APIs to staff

- **Status** Accepted
- **Context** Support staff need a small HTTP surface for conversations and messages before formal authentication and authorization are introduced.
- **Decision** Use DRF generic list, create, and retrieve views with explicit routes. Nest messages under the parent conversation UUID and check parent permissions. Give read serializers explicit public fields and restrict each create serializer to its documented inputs. Reuse model validation before insertion. Limit the API to authenticated staff using the existing authentication schemes. Paginate both lists with a default of 20 and a maximum of 100 and validate requested pages and sizes.
- **Alternatives Considered** A router with a full model ViewSet, a flat message collection, and cursor pagination.
- **Consequences** Explicit routes expose five operations and keep parent access visible in the request path. Strict input validation exposes client mistakes as 400 responses. Page numbers give clients totals and navigation links, with the usual possibility of rows shifting between pages as records are added. ADR-007 supersedes the interim staff gate.
- **Date** 2026-11-24

## ADR-007 · Use Django sessions and explicit support roles

- **Status** Accepted
- **Context** Support data needs browser authentication and operation-specific authorization before the frontend adds its login flow.
- **Decision** Keep Django's existing User model and PostgreSQL-backed sessions. Use HttpOnly, SameSite Lax cookies, with Secure enabled outside local development. Bootstrap a masked CSRF token in JSON and protect anonymous login with Django's CSRF middleware. Manage Support Agent and Support Manager through Django Groups and the four support model permissions. `is_staff` stays an administrative flag. Active superusers have an explicit access rule.
- **Alternatives Considered** JWTs with a refresh flow, a custom role model, and a migration that creates groups alongside model permissions.
- **Consequences** Django supplies server-side session invalidation and password hashing. Adding a login or write flow requires a cookie jar and CSRF header. A post-migration management command provisions exact grants when Django's model permissions are available. Same-site HTTPS deployment can use equivalent cookies and an explicit cross-origin allowlist where needed. The process-local login limit needs a shared layer for multi-worker deployments.
- **Date** 2026-11-24

## ADR-008 · Seed fictional support data with an explicit inventory

- **Status** Accepted
- **Context** Development and API demos need repeatable timelines with realistic fictional support cases.
- **Decision** Derive UUID5 IDs from explicit customer and scenario keys and per-scenario message positions. Seed only missing rows and verify existing rows against the full inventory. Gate previews and writes to configured loopback development and the isolated PostgreSQL test database. Cleanup requires `--clear`, compares every owned row, and checks relationships before deleting inside a transaction. Store intended scenario characteristics in source so analysis and drafts remain available for separately verified AI work.
- **Alternatives Considered** JSON fixtures with fixed IDs, email suffix matching, and a database ownership flag.
- **Consequences** IDs and timestamps stay reproducible without a schema change. Cleanup can refuse ordinary edits or new child records. Changes to a published inventory require care with local databases seeded by the older version. See the [sample data reference](../development/sample-data.md).
- **Date** 2026-11-24

## ADR-009 · Use a synchronous provider adapter for LLM text requests

- **Status** Accepted
- **Context** Planned AI features need a shared text client with explicit failure, usage, and cost behavior.
- **Decision** Use the official OpenAI Python SDK and Responses API behind a typed `LLMClient` protocol. Keep configuration lazy, require an explicit model, and return normalized results and sanitized errors. Use one bounded retry layer, with SDK retries disabled. Inject deterministic clients into tests and use mocked HTTP transport to verify the SDK interaction. Keep the real smoke check opt-in with zero retries and a small output cap.
- **Alternatives Considered** Raw HTTP, an agent framework, and relying on the SDK default retry policy. Raw HTTP would duplicate request and response handling. The current scope is one text request, and the project needs explicit control of rate-limit waits and retry counts.
- **Consequences** Application services can use the protocol independently of provider objects. The adapter owns role mapping, timeout policy, and output normalization. A timed-out call can still be billable, so retries remain bounded. See the [LLM integration architecture](../architecture/llm-integration.md).
- **Date** 2026-11-25
