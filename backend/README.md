# Backend

The Django project lives in `config/` and connects to local PostgreSQL through Psycopg. Django REST Framework serves staff-only conversation and message routes under `/api/`. A request to `/` returns 404. See the [API reference](../docs/api/endpoints.md).

The `support/` app owns customer-support models, migrations, API code, and PostgreSQL model and API tests. See the [support data model](../docs/architecture/data-model.md).

Use Python 3.12–3.14. The [setup guide](../docs/development/setup.md) covers the virtual environment, Docker Compose, database credentials, migrations, server startup, and local API inspection. The [testing guide](../docs/development/testing.md) documents the database-free and opt-in PostgreSQL test suites.
