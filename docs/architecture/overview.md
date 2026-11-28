# Architecture overview

The monorepo holds two independently runnable applications. Next.js serves the foundation page. Django REST Framework serves a session authentication API and a role-protected conversation and message API. Compose defines the PostgreSQL service. See the [API reference](../api/endpoints.md), [authentication architecture](authentication.md), [support data model](data-model.md), and [progress tracker](../tasks/progress.md).

Solid edges show implemented connections. Dashed edges show planned request flow.

```mermaid
flowchart TD
    Frontend["Next.js frontend"]
    Backend["Django REST Framework"]
    Accounts["Accounts API and Django sessions"]
    API["Conversation and message API"]
    Support["Support models and migrations"]
    Database["PostgreSQL 17"]
    AI["Response generation and orchestration (planned)"]
    Classifier["Customer message classifier"]
    Classify["Opt-in classification management command"]
    Analyzer["Sentiment and urgency analyzer"]
    Analyze["Opt-in analysis management command"]
    Validation["Shared structured-output validation"]
    LLM["LLM client and OpenAI adapter"]
    Check["Opt-in LLM management command"]
    Provider["OpenAI Responses API"]
    Frontend -.-> Backend
    Backend --> Accounts
    Backend --> API
    API -->|"Session and permissions"| Accounts
    Accounts --> Database
    API --> Support
    Support --> Database
    Backend -.-> AI
    AI -.-> LLM
    Classify --> Classifier
    Classifier --> LLM
    Classifier --> Validation
    Analyze --> Analyzer
    Analyzer --> LLM
    Analyzer --> Validation
    Check --> LLM
    LLM --> Provider
```

Keeping the two applications in one Git repository lets a future change to an API contract include the server, client, tests, and documentation in one review. See the [initial architecture decisions](../decisions/README.md).

The classifier and the sentiment and urgency analyzer use the same LLM client and validation layer and have independent management commands. See the [LLM integration architecture](llm-integration.md), [structured-output validation](structured-output-validation.md), [classification architecture](message-classification.md), and [sentiment and urgency architecture](sentiment-urgency.md).
