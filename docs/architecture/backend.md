# Backend architecture

`manage.py` runs Django commands. The `config/` package holds settings, URL configuration, and ASGI and WSGI entry points. Django REST Framework is registered in `INSTALLED_APPS`. Future feature apps will use DRF for request validation, HTTP responses, and API policy. The initial URL configuration is empty.

Runtime settings read process-level environment variables. Debug output defaults to off and allowed hosts default to loopback. Setting `DJANGO_ENV=development` allows a per-process signing key. Other runtime environments require an explicit, non-empty `DJANGO_SECRET_KEY`. SQLite is temporary for the foundation. PostgreSQL configuration belongs to TASK-002.

Future Django apps should group models and API code by business domain. Views should validate and authorize requests, call services for business operations, and translate outcomes into responses. Keep provider calls and response validation in dedicated AI services once introduced.

Pytest loads `config.test_settings` with pytest-django. The module shares the framework configuration and supplies a test-only signing key. Keep framework smoke tests in `backend/tests/` and request a database fixture only when a test exercises persistence.
