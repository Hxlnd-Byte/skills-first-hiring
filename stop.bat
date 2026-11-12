@echo off
cd /d "%~dp0"
echo  Stopping Skills-First Hiring. Your data is kept.
docker compose down
echo  Stopped.
pause
