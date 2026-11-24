@echo off
setlocal
title AI Customer Support - Frontend
pushd "%~dp0frontend" || exit /b 1

where.exe /q npm.cmd
if errorlevel 1 (
  echo Node.js and npm must be on PATH. See docs\development\setup.md.
  goto failed
)

if not exist "node_modules\.bin\next.cmd" (
  echo Run npm.cmd ci in frontend before starting Next.js.
  goto failed
)

echo Frontend: http://localhost:3000/
call npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
if errorlevel 1 goto failed
popd
exit /b 0

:failed
popd
pause
exit /b 1
