@echo off
setlocal
cd /d "%~dp0"
echo.
echo  Skills-First Hiring - starting (with NVIDIA graphics card)...
echo.
docker info >nul 2>&1
if errorlevel 1 (
  echo  Docker Desktop is not running.
  echo  Open Docker Desktop, wait until it shows "Engine running", then run start.bat again.
  echo.
  pause
  exit /b 1
)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
if errorlevel 1 (
  echo.
  echo  Something went wrong. See SETUP-WINDOWS.md, section 9 "If something goes wrong".
  echo  No NVIDIA graphics card? Use start-cpu.bat instead.
  echo.
  pause
  exit /b 1
)
echo.
echo  Started. Opening http://localhost:8080 in your browser...
echo  First start only: the AI model (about 4.7 GB) downloads in the background.
echo  Watch the status in the top right corner of the page until it says "AI ready".
echo.
start "" http://localhost:8080
pause
