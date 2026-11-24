import json
from subprocess import CompletedProcess

import pytest

import start_dev


@pytest.mark.parametrize("compose_exit", [0, 1])
def test_stopped_database_starts_compose_before_django(
    monkeypatch, tmp_path, compose_exit
):
    (tmp_path / ".env").touch()
    monkeypatch.setattr(start_dev, "ROOT", tmp_path)
    monkeypatch.setattr(start_dev.shutil, "which", lambda command: "docker.exe")

    def connection_refused(address, timeout):
        assert address == ("127.0.0.1", 5433)
        raise ConnectionRefusedError

    monkeypatch.setattr(start_dev.socket, "create_connection", connection_refused)
    config = {
        "services": {
            "db": {
                "environment": {
                    "POSTGRES_DB": "support_dev",
                    "APP_DB_USER": "support_role",
                    "APP_DB_PASSWORD": "test-app-password",
                    "POSTGRES_PASSWORD": "test-admin-password",
                },
                "ports": [{"host_ip": "127.0.0.1", "published": "5433"}],
            }
        }
    }
    calls = []

    def run(command, *, cwd, **kwargs):
        calls.append(command[2:])
        if command[:2] == ["docker.exe", "compose"]:
            assert cwd == tmp_path
            if command[2] == "config":
                assert kwargs["capture_output"]
                return CompletedProcess(command, 0, stdout=json.dumps(config).encode())
            return CompletedProcess(command, compose_exit)

        assert cwd == start_dev.BACKEND
        env = kwargs["env"]
        assert env["DJANGO_ENV"] == "development"
        assert env["DJANGO_SETTINGS_MODULE"] == "config.settings"
        assert env["POSTGRES_USER"] == "support_role"
        assert env["POSTGRES_PASSWORD"] == "test-app-password"
        assert env["DB_PORT"] == "5433"
        return CompletedProcess(command, 0)

    monkeypatch.setattr(start_dev.subprocess, "run", run)

    assert start_dev.main() == compose_exit
    assert calls[:2] == [
        ["config", "--format", "json"],
        ["up", "-d", "--wait", "--wait-timeout", "60", "db"],
    ]
    django_commands = [["check_database"], ["runserver", "127.0.0.1:8000"]]
    assert calls[2:] == (django_commands if compose_exit == 0 else [])
