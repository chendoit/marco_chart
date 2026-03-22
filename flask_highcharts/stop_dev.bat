@echo off
echo === Stopping dev Flask (port 6002) ===
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":6002.*LISTENING"') do (
    echo Killing PID %%a
    taskkill /F /PID %%a 2>nul
)
echo Done.
