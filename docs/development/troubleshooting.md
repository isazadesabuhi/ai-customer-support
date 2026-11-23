# Troubleshooting local setup

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
| Django root returns 404 or reports pending migrations | Both are expected at this foundation stage. See [API status](../api/endpoints.md) and [setup](setup.md). |

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
