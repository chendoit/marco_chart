@echo off
set PYTHONUTF8=1
cd /d "%~dp0"
for /l %%i in (1,1,8) do (
  "%~dp0..\..\..\..\venv\Scripts\python.exe" -u fetch.py >> fetch.log 2>&1
  findstr /c:"[done]" fetch.log >nul 2>&1 && goto :end
)
:end
echo [runner-exit] >> fetch.log
