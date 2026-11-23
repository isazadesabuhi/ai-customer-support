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
