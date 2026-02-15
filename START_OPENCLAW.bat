@echo off
setlocal
title OpenClaw Starter

cd /d "%~dp0"

echo ==========================================
echo   OpenClaw One-Click Starter
echo ==========================================
echo.

if not exist ".env" (
  if exist ".env.example" (
    echo [.env] not found. Creating it from .env.example ...
    copy ".env.example" ".env" >nul
    echo Created .env. Please fill your API keys and run this file again.
  ) else (
    echo ERROR: .env and .env.example are both missing.
  )
  echo.
  pause
  exit /b 1
)

where docker >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker is not installed or not in PATH.
  echo Install Docker Desktop first, then run this file again.
  echo.
  pause
  exit /b 1
)

echo Checking Docker engine...
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker engine is not ready. Trying to start Docker Desktop...
  if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  )
  call :wait_for_docker
  if errorlevel 1 goto docker_not_ready
)

:docker_ready
echo Docker is ready.
echo Starting OpenClaw containers...
docker compose up -d --build
if errorlevel 1 (
  echo.
  echo ERROR: Failed to start containers.
  echo Run this command in terminal for details:
  echo   docker compose logs --tail=200 backend worker frontend database ollama-brain
  echo.
  pause
  exit /b 1
)

echo.
echo Current container status:
docker compose ps

echo.
echo Opening dashboard in browser...
start "" "http://localhost:3000"

echo.
echo OpenClaw started successfully.
echo.
exit /b 0

:docker_not_ready
echo.
echo ERROR: Docker engine did not become ready in time.
echo Start Docker Desktop manually, wait until it says Running, then run this file again.
echo.
pause
exit /b 1

:wait_for_docker
echo Waiting for Docker to become ready (up to 2 minutes)...
set /a WAIT_SECS=0
:wait_loop
docker info >nul 2>&1
if not errorlevel 1 exit /b 0
timeout /t 4 /nobreak >nul
set /a WAIT_SECS+=4
if %WAIT_SECS% GEQ 120 exit /b 1
goto wait_loop
