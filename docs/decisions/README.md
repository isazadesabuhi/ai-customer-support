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

## ADR-010 · Classify one support message with validated JSON

- **Status** Accepted
- **Context** The backend needs one label from the existing support taxonomy for the intent of one customer message.
- **Decision** Use the seven model category keys and prioritize the requested action or immediate obstacle. Put versioned instructions in a `developer` message and customer text in a `user` message. Request one JSON object, validate its exact shape, and return a typed result. Preserve `other` for a valid unclear or out-of-scope intent. Report invalid output as an error and leave retries for transient failures to the existing client. Keep the classification service free of queries and persistence.
- **Alternatives Considered** Plain-text labels, provider-specific structured output, treating parse failures as `other`, and sending repair attempts automatically.
- **Consequences** Classification behavior can be tested with deterministic clients independently of provider and database availability. Format failures stay visible. Production accuracy and injection resistance still need evaluation. Automatic repair could hide defects and add paid requests. See the [classification architecture](../architecture/message-classification.md).
- **Date** 2026-11-25

## ADR-011 · Analyze sentiment and urgency independently in one request

- **Status** Accepted
- **Context** The way someone describes an issue and the consequences of waiting answer different support questions, even when both can be assessed from the same message.
- **Decision** Use the existing model enums and a versioned prompt with separate evidence criteria for sentiment and urgency. Send one request through `LLMClient`. Validate the four exact JSON fields and return an advisory result. Report format and label errors directly, keeping `neutral` and `normal` as valid analysis decisions. Keep the analyzer independent of classification, persistence, and orchestration.
- **Alternatives Considered** Two separate requests for tone and urgency, an inferred priority based on sentiment, schema repair requests, and combining these outputs with intent classification now.
- **Consequences** One call avoids sending the same text twice and retains the existing provider retry limits. Independent fields can express polite deadlines and non-urgent frustration. Structured validity is checked locally, and model accuracy and injection resistance remain evaluation work. See the [sentiment and urgency architecture](../architecture/sentiment-urgency.md).
- **Date** 2026-11-26

## ADR-012 · Share structured-output checks across AI services

- **Status** Accepted
- **Context** Classification and sentiment/urgency duplicated JSON decoding, duplicate detection, exact field checks, enums, and explanation validation.
- **Decision** Use the standard JSON decoder with hooks for duplicate keys and non-finite numbers, plus fixed size and depth limits. Reuse helpers for object shape, exact choices, and printable text. Keep each service's fields and business rules in its own schema. Translate shared failures into existing public errors to preserve caller contracts.
- **Alternatives Considered** A general schema framework, automatic correction, and provider-specific schema enforcement. The current object contracts need a small provider-independent boundary. Automatic correction can hide bad outputs and require additional model calls.
- **Consequences** Duplicate keys fail before a later value can overwrite an earlier one. Invalid results remain visible, and both services can evolve their domain rules independently. Existing fake clients and provider adapters still use the same interface. See the [structured-output architecture](../architecture/structured-output-validation.md).
- **Date** 2026-11-28

## ADR-013 · Generate structured drafts for human review

- **Status** Accepted
- **Context** Support agents need suggested replies to a single message. The application may have no verified order, policy, or account information for that message.
- **Decision** Add a standalone generator that accepts controlled language and tone settings and explicitly supplied facts. Keep the fixed, versioned policy in the developer role and encode the facts and customer text as data in the user role. Ask for clarification or suggest a human check when evidence is missing. Validate the exact JSON schema and the consistency of missing-information fields before returning an in-memory result with mandatory review.
- **Alternatives Considered** Free-form output, unrestricted style instructions, automatic policy retrieval, persisting every generated draft, and additional model-based evaluation in the same request.
- **Consequences** Callers can test drafting independently and reviewers decide whether a reply is fit for delivery. This generation step has no persistence or delivery integration. The initial English and French settings and three tones keep the supported contract small. TASK-012 will add explicit safety and quality evaluation. See the [draft generation architecture](../architecture/draft-generation.md).
- **Date** 2026-11-28
