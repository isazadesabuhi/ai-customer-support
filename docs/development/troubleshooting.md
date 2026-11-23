# Troubleshooting local setup

| Symptom | Action |
| --- | --- |
| PowerShell blocks `Activate.ps1` | From `backend/`, run `.\.venv\Scripts\python.exe` directly for pip, Django, and Pytest. Use `.\.venv\Scripts\ruff.exe` for Ruff. |
| PowerShell blocks `npm.ps1` | Run `npm.cmd` with the same arguments. |
| Python or Node.js has the wrong version | Compare `python --version` and `node --version` to the [prerequisites](setup.md#prerequisites). Use `Get-Command python,node` in PowerShell or `command -v python3 node` in a POSIX shell to find the active paths. Create a new virtual environment with the intended interpreter if necessary. |
| Django, Ruff, or Pytest is missing | Install `requirements/dev.txt` using the virtual environment's Python and run `python -m pip check`. |
| Next.js or its tooling is missing | Run `npm ci` (or `npm.cmd ci`) in `frontend/`. Registry access or a cache with all locked packages is required. |
| Port 3000 or 8000 is busy | Start Next.js with `npm run dev -- --hostname 127.0.0.1 --port 3001` or Django with `python manage.py runserver 127.0.0.1:8001`. |
| Django ignores environment values | Set process variables in the terminal that starts Django, then restart it. Use `true` or `false` for `DJANGO_DEBUG` and separate allowed hostnames with commas. |
| Django root returns 404 or reports pending migrations | Both are expected at this foundation stage. See [API status](../api/endpoints.md) and [setup](setup.md). |
