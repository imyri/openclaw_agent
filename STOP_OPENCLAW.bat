@echo off
setlocal
title OpenClaw Stopper

cd /d "%~dp0"

echo Stopping OpenClaw containers...
docker compose down

if errorlevel 1 (
  echo.
  echo Failed to stop containers. Check Docker Desktop status.
  echo.
  pause
  exit /b 1
)

echo OpenClaw stopped.
exit /b 0

