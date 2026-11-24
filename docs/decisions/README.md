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
