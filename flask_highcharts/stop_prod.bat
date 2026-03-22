@echo off
echo === Stopping production Flask (port 5002) ===
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5002.*LISTENING"') do (
    echo Killing PID %%a
    taskkill /F /PID %%a 2>nul
)
echo Done.
