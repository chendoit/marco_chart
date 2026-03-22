@echo off
echo === Stopping dev Flask (port 6002) ===
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":6002.*LISTENING"') do (
    echo Killing PID %%a
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul

echo === Starting dev Flask ===
cd /d "%~dp0"
set FLASK_ENV=development
start "" /min "..\venv\Scripts\python.exe" main.py
timeout /t 3 /nobreak >nul

echo === Verifying ===
curl.exe -s -o nul -w "HTTP %%{http_code}" http://localhost:6002/
echo.
echo Done.
