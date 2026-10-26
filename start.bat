@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo Starting MongoDB...
start "MongoDB" /D "%ROOT%\mongodb\mongodb-win32-x86_64-windows-7.0.14\bin" cmd /k .\mongod.exe --dbpath "%ROOT%\mongo-data" --port 27017 --bind_ip 127.0.0.1 --logpath "%ROOT%\mongo-data.mongod.log"

"%SystemRoot%\System32\timeout.exe" /t 3 /nobreak >nul

echo Starting backend (FastAPI)...
start "Backend - FastAPI" /D "%ROOT%\backend" cmd /k .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo Starting frontend (Vite)...
start "Frontend - Vite" /D "%ROOT%\frontend" cmd /k npm run dev

echo.
echo All three services are starting in separate windows:
echo   MongoDB  - localhost:27017
echo   Backend  - http://localhost:8000
echo   Frontend - http://localhost:5173
echo.
echo Open http://localhost:5173 in your browser once the windows say they are ready.
echo Close this window any time - the three service windows will keep running.
echo To stop everything, close the MongoDB / Backend / Frontend windows.
echo.
pause
