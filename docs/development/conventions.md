# Development conventions

- Use `snake_case` for Python modules, functions, and variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for settings and constants.
- Use `camelCase` for TypeScript functions and variables, `PascalCase` for component and type names, and Next.js route filenames such as `page.tsx` and `layout.tsx`.
- Use `@/` for TypeScript imports that cross folders under `src/`. Group Python imports by standard library, third-party, and local code. Ruff manages import sorting.
- Keep configuration in `backend/config/`. As business apps are added, let views handle HTTP and authorization, services handle business operations, and AI services handle provider interaction and output validation.
- Validate input at the boundary. Keep expected failures explicit, translate errors into actionable responses, and exclude credentials and customer data from logs.
- Use `UPPER_SNAKE_CASE` environment variables with an app-specific prefix. Commit examples with placeholders. Keep browser-visible Next.js variables free of credentials.
- Cover meaningful behavior and failure cases. Mock external service calls in ordinary automated tests.
- Use Prettier for frontend formatting and ESLint for code rules. TypeScript checks types independently. Ruff formats and lints Python with separate commands.
