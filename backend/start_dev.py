"""Start the local Django server from the Windows launcher."""

import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent


def main():
    docker = shutil.which("docker")
    if not docker or not (ROOT / ".env").is_file():
        print(
            "Install Docker Desktop and configure the root .env first.", file=sys.stderr
        )
        return 1

    compose = [docker, "compose"]
    config = subprocess.run(
        [*compose, "config", "--format", "json"], cwd=ROOT, capture_output=True
    )
    if config.returncode:
        print(
            "Check the root .env and run docker compose config --quiet.",
            file=sys.stderr,
        )
        return 1

    database = json.loads(config.stdout)["services"]["db"]
    variables = database["environment"]
    port = database["ports"][0]
    host = port["host_ip"]
    if host != "127.0.0.1":
        print("Expected the Compose database port on 127.0.0.1.", file=sys.stderr)
        return 1

    env = {
        **os.environ,
        "DJANGO_ENV": "development",
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "POSTGRES_DB": variables["POSTGRES_DB"],
        "POSTGRES_USER": variables["APP_DB_USER"],
        "POSTGRES_PASSWORD": variables["APP_DB_PASSWORD"],
        "DB_HOST": host,
        "DB_PORT": str(port["published"]),
    }
    try:
        with socket.create_connection((host, int(env["DB_PORT"])), timeout=2):
            pass
    except OSError:
        print("Starting the local PostgreSQL service...", flush=True)
        started = subprocess.run(
            [*compose, "up", "-d", "--wait", "--wait-timeout", "60", "db"], cwd=ROOT
        )
        if started.returncode:
            print(
                "Start Docker Desktop and check the database service.", file=sys.stderr
            )
            return started.returncode

    manage = [sys.executable, "manage.py"]
    checked = subprocess.run([*manage, "check_database"], cwd=BACKEND, env=env)
    if checked.returncode:
        return checked.returncode

    print("Backend API check: http://localhost:8000/api/auth/csrf/", flush=True)
    return subprocess.run(
        [*manage, "runserver", "127.0.0.1:8000"], cwd=BACKEND, env=env
    ).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
