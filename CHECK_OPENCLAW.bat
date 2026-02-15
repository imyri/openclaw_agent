@echo off
setlocal
title OpenClaw Health Check

cd /d "%~dp0"

echo ==========================================
echo   OpenClaw Quick Health Check
echo ==========================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker is not installed or not in PATH.
  echo.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker engine is not running.
  echo Start Docker Desktop first.
  echo.
  pause
  exit /b 1
)

echo [1/4] Container status
docker compose ps
echo.

echo [2/4] API health: /health/live
powershell -NoProfile -Command "try { (Invoke-WebRequest http://localhost:8000/health/live -UseBasicParsing -TimeoutSec 5).Content } catch { $_.Exception.Message }"
echo.

echo [3/4] API health: /health/ready
powershell -NoProfile -Command "try { (Invoke-WebRequest http://localhost:8000/health/ready -UseBasicParsing -TimeoutSec 5).Content } catch { $_.Exception.Message }"
echo.

echo [4/4] Recent backend + worker logs
docker compose logs --tail=40 backend worker
echo.

echo Check complete.
echo.
pause
exit /b 0

