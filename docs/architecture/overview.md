# Architecture overview

The monorepo holds two independently runnable applications. Next.js serves the foundation page. Django REST Framework serves the staff-only conversation and message API using the `support` data layer. Compose defines the PostgreSQL service. See the [API reference](../api/endpoints.md), [support data model](data-model.md), and [progress tracker](../tasks/progress.md).

Solid edges show application components and their configured database connection. Dashed edges show planned request flow.

```mermaid
flowchart TD
    Frontend["Next.js frontend"]
    Backend["Django REST Framework"]
    API["Staff-only conversation and message API"]
    Support["Support models and migrations"]
    Database["PostgreSQL 17"]
    AI["AI services (planned)"]
    Provider["LLM provider (planned)"]
    Frontend -.-> Backend
    Backend --> API
    API --> Support
    Support --> Database
    Backend -.-> AI
    AI -.-> Provider
```

Keeping the two applications in one Git repository lets a future change to an API contract include the server, client, tests, and documentation in one review. See the [initial architecture decisions](../decisions/README.md).
