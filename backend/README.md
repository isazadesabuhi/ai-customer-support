# Backend

The Django project lives in `config/` and connects to local PostgreSQL through Psycopg. Django REST Framework serves session authentication and role-protected conversation and message routes under `/api/`. A request to `/` returns 404. See the [API reference](../docs/api/endpoints.md).

The `support/` app owns customer-support models, migrations, API code, and PostgreSQL model and API tests. See the [support data model](../docs/architecture/data-model.md).

Run `python manage.py seed_support_data --dry-run` to preview fictional tickets in a configured local development database. See the [sample data guide](../docs/development/sample-data.md) for seeding, inspection, and cleanup.

The `accounts/` app owns the login, logout, CSRF, and current-user endpoints. Run `python manage.py provision_support_roles` after `migrate` to synchronize the support groups. See the [authentication architecture](../docs/architecture/authentication.md).

The `ai/` package provides a synchronous text client and a Responses API adapter. Run `python manage.py check_llm` to validate optional environment configuration locally. See the [LLM integration guide](../docs/architecture/llm-integration.md).

`CustomerMessageClassifier` uses the client to classify a single message. Its management command validates input offline by default. See the [classification guide](../docs/architecture/message-classification.md).

`SentimentUrgencyAnalyzer` uses the same client to assess the expressed attitude and time sensitivity of a single message. Its `analyze_sentiment` command defaults to offline validation. See the [analysis guide](../docs/architecture/sentiment-urgency.md).

`CustomerResponseDraftGenerator` uses one customer message and optional supplied facts to suggest a reply for human review. Its `generate_draft` command defaults to offline validation. See the [draft generation guide](../docs/architecture/draft-generation.md).

`ai/structured_output/` provides the bounded JSON parser and common validators used by all three AI services. See the [structured-output validation guide](../docs/architecture/structured-output-validation.md).

Use Python 3.12–3.14. The [setup guide](../docs/development/setup.md) covers the virtual environment, Docker Compose, database credentials, migrations, server startup, and local API inspection. The [testing guide](../docs/development/testing.md) documents the database-free and opt-in PostgreSQL test suites.
