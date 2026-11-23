# AI Customer Support Assistant

This project is a production-oriented portfolio application for learning practical LLM engineering. The planned workspace will help support agents understand incoming messages and review AI-assisted draft responses before approving them. Human review is central to the workflow. The foundation keeps the UI, API, and future AI services in defined modules so each can evolve independently.

## Current status

The frontend defines a foundation landing page. The backend loads Django and Django REST Framework with local SQLite settings and an empty URL configuration. See the [progress tracker](docs/tasks/progress.md) for verified checks.

| Area | In the repository | Planned |
| --- | --- | --- |
| Frontend | Next.js App Router, React, TypeScript, Tailwind CSS, ESLint, Prettier, Vitest, React Testing Library | Agent inbox, draft review, Playwright |
| Backend | Python, Django, Django REST Framework, Ruff, Pytest, pytest-django configuration | PostgreSQL, support APIs, authentication |
| AI | Workflow documentation | OpenAI Python SDK, Pydantic validation, evaluations |

## Repository

- `frontend/` contains the Next.js app and component tests.
- `backend/` contains the Django project configuration, Python requirements, and framework smoke tests.
- `docs/` contains architecture, development, API, AI, and project records.

## Getting started

Follow the [local setup guide](docs/development/setup.md) to install dependencies, start both servers, and run the checks.

## Roadmap and documentation

See the [canonical roadmap](docs/tasks/roadmap.md) and [documentation index](docs/README.md).

## Security

Keep credentials in local process variables or ignored environment files. Version only the example files and keep secrets out of browser-exposed configuration.

## License

The project uses the [MIT License](LICENSE).
