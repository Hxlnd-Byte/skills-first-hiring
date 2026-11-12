@echo off
cd /d "%~dp0"
echo  Showing the latest messages from the app and the AI model. Press Ctrl+C to stop watching.
docker compose logs -f --tail 100
