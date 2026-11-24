@echo off
setlocal
title AI Customer Support - Backend

set "python=%~dp0backend\.venv\Scripts\python.exe"
if not exist "%python%" (
  echo Set up backend\.venv first. See docs\development\setup.md.
  goto failed
)

"%python%" "%~dp0backend\start_dev.py"
if errorlevel 1 goto failed
exit /b 0

:failed
pause
exit /b 1
