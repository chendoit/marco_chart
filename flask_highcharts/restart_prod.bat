@echo off
echo === Stopping production Flask (port 5002) ===
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5002.*LISTENING"') do (
    echo Killing PID %%a
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul

echo === Starting production Flask ===
cd /d "%~dp0"
set FLASK_ENV=production
start "" /min "..\venv\Scripts\python.exe" main.py
timeout /t 3 /nobreak >nul

echo === Verifying ===
curl.exe -s -o nul -w "HTTP %%{http_code}" http://localhost:5002/
echo.
echo Done.
