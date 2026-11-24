# Architecture overview

The monorepo holds two independently runnable applications. Next.js serves the foundation page. Django REST Framework serves a session authentication API and a role-protected conversation and message API. Compose defines the PostgreSQL service. See the [API reference](../api/endpoints.md), [authentication architecture](authentication.md), [support data model](data-model.md), and [progress tracker](../tasks/progress.md).

Solid edges show application components and their configured database connection. Dashed edges show planned request flow.

```mermaid
flowchart TD
    Frontend["Next.js frontend"]
    Backend["Django REST Framework"]
    Accounts["Accounts API and Django sessions"]
    API["Conversation and message API"]
    Support["Support models and migrations"]
    Database["PostgreSQL 17"]
    AI["AI services (planned)"]
    Provider["LLM provider (planned)"]
    Frontend -.-> Backend
    Backend --> Accounts
    Backend --> API
    API -->|"Session and permissions"| Accounts
    Accounts --> Database
    API --> Support
    Support --> Database
    Backend -.-> AI
    AI -.-> Provider
```

Keeping the two applications in one Git repository lets a future change to an API contract include the server, client, tests, and documentation in one review. See the [initial architecture decisions](../decisions/README.md).
