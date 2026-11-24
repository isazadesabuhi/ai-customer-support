# AI Customer Support Assistant

This project is a production-oriented portfolio application for learning practical LLM engineering. The planned workspace will help support agents understand incoming messages and review AI-assisted draft responses before approving them. Human review is central to the workflow. The foundation keeps the UI, API, and future AI services in defined modules so each can evolve independently.

## Current status

The frontend defines a foundation landing page. The backend defines the support domain models and uses PostgreSQL through Django. Docker Compose defines the local database service. See the [support data model](docs/architecture/data-model.md) and [progress tracker](docs/tasks/progress.md).

| Area | In the repository | Planned |
| --- | --- | --- |
| Frontend | Next.js App Router, React, TypeScript, Tailwind CSS, ESLint, Prettier, Vitest, React Testing Library | Agent inbox, draft review, Playwright |
| Backend | Python, Django, Django REST Framework, PostgreSQL configuration, Ruff, Pytest, pytest-django | Support APIs, authentication |
| AI | Workflow documentation | OpenAI Python SDK, Pydantic validation, evaluations |

## Repository

- `frontend/` contains the Next.js app and component tests.
- `backend/` contains the Django project configuration, Python requirements, and framework smoke tests.
- `compose.yaml` and `docker/postgres/` define the local database service and app role.
- `docs/` contains architecture, development, API, AI, and project records.

## Getting started

Follow the [local setup guide](docs/development/setup.md) to install dependencies, start PostgreSQL and both applications, and run the checks.

## Roadmap and documentation

See the [canonical roadmap](docs/tasks/roadmap.md) and [documentation index](docs/README.md).

## Security

Keep credentials in local process variables or ignored environment files. Version only the example files and keep secrets out of browser-exposed configuration.

## License

The project uses the [MIT License](LICENSE).
