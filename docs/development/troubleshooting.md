# Troubleshooting local setup

## LLM configuration and provider errors

Run `python manage.py check_llm` first to check the backend process environment locally. Use the backend virtual environment and load Django's normal local settings. See the [configuration guide](setup.md#configure-the-optional-llm-client).

| Symptom | What to check |
| --- | --- |
| Missing key or model | Set `OPENAI_API_KEY` and `OPENAI_MODEL` in the shell that runs Django. Enter the key at a masked prompt. |
| Credentials or access denied | Confirm the key is valid for the intended API project and that the project can use the model. |
| Request or model rejected | Check the exact model identifier, Responses API support, and output-token limits. Omit `temperature` with this adapter. |
| Rate limit or unavailable quota | Inspect the API project's rate limits and billing. Wait for the indicated limit to reset before trying again. |
| Timeout | Check service availability and network conditions. Adjust `LLM_TIMEOUT_SECONDS` within its documented bounds when needed. A timeout can occur after the provider receives the request. |
| Connection failure | Check DNS, firewall rules, proxy configuration, and TLS trust for `api.openai.com`. |
| Empty or incomplete output | Check that the model supports text generation and that its output budget allows both reasoning and visible text. Use a short input for the live check. |
| Usage missing | Treat the token counts as unknown. A completed text response can still be usable. |
| Unexpected SDK failure | Verify the pinned dependencies with `python -m pip check`. If reporting the failure, share the error category and model and keep credentials and prompt text private. |

## Message classification failures

| Symptom | What to check |
| --- | --- |
| Local check validated input without printing a category | The default command checks input. Use `--live` only when you have opted into a potentially billable request. |
| Live command reports missing configuration | Load `OPENAI_API_KEY` and `OPENAI_MODEL` in the command's backend shell and run `check_llm` locally. |
| Unsupported category or malformed JSON | The classifier rejected the response. Check the model and prompt version with a fictional test case. The parser requires two exact keys and one allowed category. |
| Empty or incomplete output | The adapter can reject a response before classification parsing. Check the output budget for reasoning plus a short JSON object. |
| Result is `other` | The message may lack a recognizable intent in isolation. Review the wording and available conversation context manually. |
| Unsupported model setting | Use a model supported by the configured client, omit `temperature`, and keep the classifier's output limit within the backend setting. |
| Provider rate limit or timeout | The underlying client handles eligible retries. Review the rate-limit or timeout guidance above before any new invocation. |

See the [classification architecture](../architecture/message-classification.md) and [local command](setup.md#exercise-message-classification).

## Sentiment and urgency analysis failures

| Symptom | What to check |
| --- | --- |
| Offline mode prints a validation result only | Offline mode validates the supplied message. A real prediction requires explicit `--live` opt-in. |
| Missing provider configuration or unsupported model | Load the backend key and model, run `check_llm` locally, and verify the model is available to the API project. |
| Empty or incomplete response | Check that the configured output limit can accommodate model reasoning and all four visible JSON fields. |
| Invalid JSON or unsupported sentiment or urgency | The response violated the analysis contract. Review the prompt version and model with a fictional example. A validation failure remains an error. |
| Provider rate limit or timeout | Check provider limits or network conditions. The client already retries eligible failures within its configured limits. |
| Ambiguous tone or timing | Review the message and any available conversation context manually. The analyzer sees one message body. |

See the [analysis contract](../architecture/sentiment-urgency.md) and [local command](setup.md#exercise-sentiment-and-urgency-analysis).

## Structured-output validation failures

| Symptom | What to check |
| --- | --- |
| Malformed object error | The response must be one complete JSON object. Check for invalid syntax, surrounding prose, Markdown fences, a scalar or array root, or an incomplete output budget. |
| Duplicate field | Each object can use a key once, including nested fields. Compare the expected field names against a fictional test case. |
| Unsupported enum | Check the exact lowercase label against the service's domain enum. Aliases and capitalization variants are rejected. |
| Missing or unexpected fields | Compare the response to the service contract. Each service requires an exact set of keys. |
| Excessive response size or nesting | The parser caps responses at 16,384 characters and 32 container levels. Keep the response within the selected service's field and length limits. |
| Invalid explanation | Use a nonblank printable string of up to 300 characters. Embedded line breaks, tabs, and controls are invalid. |

Use fictional fixtures to reproduce an error. Keep customer text, credentials, and full model output out of logs and shared reports. See the [validation architecture](../architecture/structured-output-validation.md).

## Draft generation

| Symptom | What to check |
| --- | --- |
| Missing API key or model | Offline validation can run immediately. For a live request, load the [optional LLM settings](setup.md#configure-the-optional-llm-client) in the backend shell. |
| Unsupported language or tone | Use `en` or `fr`, and `professional`, `friendly`, or `empathetic`. |
| Invalid context | Omit it when facts are unavailable. If supplied, use nonblank verified facts within 4,000 characters. |
| Missing draft text or invalid JSON | Check that the response is one JSON object with all three draft fields. The draft must be nonblank printable text on a single line, without markup. |
| Contradictory information fields | Set `needs_information` to a JSON Boolean. When it is true, the array must list at least one distinct needed detail. When false, the array must be empty. |
| Timeout, rate limit, or unexpected provider response | Check the configured model and the provider error category. The command uses the provider's bounded retries. Invalid response content fails without a repair request. |

Reproduce output failures with fictional fixtures. Check the [draft schema and limits](../architecture/draft-generation.md#output) and [local command](setup.md#exercise-draft-generation).

## Local tooling

| Symptom | Action |
| --- | --- |
| PowerShell blocks `Activate.ps1` | From `backend/`, run `.\.venv\Scripts\python.exe` directly for pip, Django, and Pytest. Use `.\.venv\Scripts\ruff.exe` for Ruff. |
| PowerShell blocks `npm.ps1` | Run `npm.cmd` with the same arguments. |
| Python or Node.js has the wrong version | Compare `python --version` and `node --version` to the [prerequisites](setup.md#prerequisites). Use `Get-Command python,node` in PowerShell or `command -v python3 node` in a POSIX shell to find the active paths. Create a new virtual environment with the intended interpreter if necessary. |
| Django, Ruff, or Pytest is missing | Install `requirements/dev.txt` using the virtual environment's Python and run `python -m pip check`. |
| Next.js or its tooling is missing | Run `npm ci` (or `npm.cmd ci`) in `frontend/`. See [Windows npm install recovery](#windows-npm-install-recovery) for registry and cache errors. |
| Turbopack reports multiple lockfiles | `frontend/next.config.ts` sets `turbopack.root` to the directory containing the config. If the warning reappears, confirm Next.js is loading that config for `frontend/`. Leave lockfiles in parent directories in place. [Turbopack root configuration](https://nextjs.org/docs/app/api-reference/config/next-config-js/turbopack#root-directory) |
| Port 3000 or 8000 is busy | Start Next.js with `npm run dev -- --hostname 127.0.0.1 --port 3001` or Django with `python manage.py runserver 127.0.0.1:8001`. |
| Django ignores environment values | Set process variables in the terminal that starts Django, then restart it. Use `true` or `false` for `DJANGO_DEBUG` and separate allowed hostnames with commas. |
| Django requests a non-empty `DJANGO_SECRET_KEY` | For local commands, set `$env:DJANGO_ENV = 'development'` in PowerShell or `export DJANGO_ENV=development` in a POSIX shell. In other environments, supply a private, non-empty `DJANGO_SECRET_KEY` through the process environment. |
| Django root returns 404 | Django serves its API under `/api/`. See the [API reference](../api/endpoints.md). |

## API authentication and browser requests

| Symptom | What to check |
| --- | --- |
| Login returns `400` | Check the username and password, confirm the account is active, and verify membership in `Support Agent` or `Support Manager`. The same error covers an unknown username, bad password, or ineligible account. |
| Login or a write returns `403` mentioning CSRF | GET `/api/auth/csrf/` with the same client and cookie jar. Send its `csrfToken` as `X-CSRFToken`. Get a new token after login because Django rotates the cookie secret. |
| A read returns `403` after login | Inspect `/api/auth/me/` using the same session. If the profile works, compare its grants with the operation in the API reference. A staff flag alone gives zero support grants. |
| Session cookie is missing from a browser request | Use `credentials: "include"` for a credentialed cross-origin request. Verify the response set a cookie and that the browser can send it under the configured Secure and SameSite policies. Local HTTP requires `DJANGO_ENV=development`. |
| CORS preflight or browser response access fails | Check the frontend's exact scheme, hostname, and port against `DJANGO_FRONTEND_ORIGINS`, then restart Django after any environment change. Use a comma-separated list of origins without paths. |
| Cookies and CSRF work in PowerShell but fail in the browser | Use `localhost` in both browser URLs. `127.0.0.1` changes the cookie host and site. The default policy expects `http://localhost:3000` and `http://localhost:8000`. |
| A previously working session returns `403` | Sign in again after session expiry or logout. Account deactivation, password changes, and role removal can also revoke access. A backend restart can invalidate sessions when development uses a generated signing key. |

See the [local session walkthrough](setup.md#inspect-the-api-locally) and the [API reference](../api/endpoints.md).

## PostgreSQL and Docker Compose

Run Compose commands from the repository root and Django commands from `backend/`.

| Symptom | Action |
| --- | --- |
| Docker Engine is unreachable | Start Docker Desktop in Linux container mode on Windows, or start Docker Engine on Linux. Run `docker version` and look for its Server section. |
| Port 5432 is occupied | Set `DB_PORT=55432` in the ignored root `.env`, reload the Django variables, and run `docker compose up -d --wait db`. PostgreSQL still listens on port 5432 inside the container. |
| The container is unhealthy | Check `docker compose ps` and `docker compose logs --tail 100 db` locally. Inspect initialization errors and allow time for readiness. |
| Required variables are missing | Copy the root `.env.example` once, fill both passwords, and load the Django variables in the same shell that starts Django. Use `docker compose config --quiet` to check Compose interpolation. |
| Connection refused or timed out | Check service readiness and the host port with `docker compose ps`. Match Django's `DB_HOST` and `DB_PORT` to the published address. |
| Authentication fails | Verify the database name, app role, and password against the existing database, then retry `python manage.py check_database`. The health check only verifies server readiness. |
| Test database permission is denied | Use the Compose-provisioned role with `CREATEDB` and opt in with `--ds=config.postgres_test_settings`. Verify the loopback target and keep the reserved name for tests. |
| Migration fails or appears pending | Confirm connectivity, inspect `python manage.py showmigrations` and `python manage.py migrate --plan`, then correct the reported error and rerun `migrate`. |
| Changing passwords in `.env` has no effect | The image runs initialization only on an empty data directory. For an existing local volume, restore the matching values or use a PostgreSQL admin session and psql's `\password` prompt to rotate the app role's password, then update `.env` and reload the shell. Preserve the volume during troubleshooting. |

## Windows npm install recovery

Use a PowerShell terminal with approved HTTPS access to the public npm registry. Install or activate Node.js 24 LTS (24.22.3 or a later 24.x patch) with npm 11. Open a new terminal so it picks up any `PATH` changes. [Official Node.js downloads](https://nodejs.org/en/download)

From the repository root, check the active tools and registry connection.

```powershell
Set-Location frontend
Get-Command node,npm.cmd | Select-Object Name,Source
node --version
npm.cmd --version
npm.cmd config get registry
npm.cmd config get strict-ssl
npm.cmd ping --registry https://registry.npmjs.org/
```

Expect the public HTTPS registry and `strict-ssl` set to `true`. If the ping fails with `EACCES` or a connection error, use a terminal on a network with approved registry access. For a managed work network, use the proxy and certificate configuration approved by its administrator. If the error names a local cache path, retry with a writable cache such as `npm.cmd ci --cache (Join-Path $env:TEMP 'ai-customer-support-npm-cache')`. `ENOTCACHED` in offline mode means an archive is missing. A successful online install can populate the cache. [npm ping](https://docs.npmjs.com/cli/v11/commands/npm-ping/)

After the ping succeeds, install from the existing lockfile and run the checks.

```powershell
npm.cmd ci
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run format:check
npm.cmd run test:run
npm.cmd run build
npm.cmd run dev -- --hostname 127.0.0.1
```

Open `http://127.0.0.1:3000/` and verify that the heading reads **AI Customer Support Assistant**. `npm ci` uses the locked dependency versions and requires the manifest and lockfile to agree. Keep the existing lockfile when resolving connectivity or cache errors. [npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/)
