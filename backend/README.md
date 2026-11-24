# Backend

The Django project lives in `config/` and connects to local PostgreSQL through Psycopg. Django REST Framework is installed. The URL configuration is empty, so an HTTP request to `/` returns 404.

The `support/` app owns customer-support models, migrations, and PostgreSQL model tests. See the [support data model](../docs/architecture/data-model.md).

Use Python 3.12–3.14. The [setup guide](../docs/development/setup.md) covers the virtual environment, Docker Compose, database credentials, framework migrations, and server startup. The [testing guide](../docs/development/testing.md) documents the database-free tests and opt-in PostgreSQL integration test.
