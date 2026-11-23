# Frontend architecture

Next.js owns the support-agent interface. The App Router maps `src/app/page.tsx` to `/`. The root layout sets document metadata and imports the Tailwind stylesheet. TypeScript checks component props and module contracts before runtime.

| Path | Purpose |
| --- | --- |
| `src/app/` | Route entry points, layouts, and app-wide styles |
| `src/components/` | Shared UI once a second route or component needs it |
| `src/lib/` | Shared utilities and future API client code |
| `src/test/` | Component tests and test setup |
| `public/` | Static assets when the UI needs them |

Use `@/` for imports across `src/`. Keep route-specific components near their route and promote reusable UI to `src/components/`. Use Server Components by default and introduce Client Components where interaction requires client-side state or browser APIs.

Later, the frontend will consume Django REST endpoints over HTTP using JSON. Authentication and authorization decisions will be documented with the relevant tasks.
