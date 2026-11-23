# Testing

Small automated checks catch configuration and rendering regressions before a developer has to run both apps. Formatting checks keep layout consistent, linting flags problematic patterns, and type checking validates TypeScript contracts. Tests exercise behavior.

| Scope | Command | Coverage |
| --- | --- | --- |
| Frontend | `npm run test:run` | Vitest renders the landing page with React Testing Library and jsdom and verifies its level-one heading. |
| Backend | `python -m pytest` | pytest-django loads the project, verifies DRF registration and Django checks, and confirms an HTTP 404 at the empty root route. |

Run each command from its app directory. Use `npm.cmd` in Windows PowerShell and the activated Python virtual environment for backend checks. Use `npm run test` for interactive frontend watch mode. Neither suite needs a running development server or external credentials.

Future tests should mock external API requests at the service boundary and exercise both successful and failed responses. Use integration tests to verify persistence and API contracts as those layers arrive. Add Playwright for end-to-end flows once the frontend and API communicate.
