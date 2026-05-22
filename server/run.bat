@echo off
set PYTHONDONTWRITEBYTECODE=1
set DISABLE_SERVER_BROWSER_OPEN=1
title Lunar Rover - Live Dev
color 0B
cls

echo.
echo  ============================================================
echo    LUNAR ROVER ^| LIVE DEV MODE
echo    Frontend: Vite (hot reload) ^| Backend: FastAPI
echo  ============================================================
echo.
echo  [*] Checking Python dependencies...
python -c "import fastapi, uvicorn, websockets, gymnasium, numpy" 2>nul
if %errorlevel% neq 0 (
    echo  [!] Installing required Python packages...
    pip install fastapi "uvicorn[standard]" websockets gymnasium numpy pygame -q
)
echo  [+] Python dependencies OK
echo.
echo  [*] Starting backend on 127.0.0.1:8000...
echo  [*] Starting frontend live on 127.0.0.1:5173...
echo.
echo  ============================================================
echo    Open: http://127.0.0.1:5173/AiMenu/
echo  ============================================================
echo.

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"
start "Lunar Rover Backend" cmd /k "cd /d %ROOT_DIR% && python -m uvicorn server.app:app --host 127.0.0.1 --port 8000 --log-level warning"
start "Lunar Rover Frontend" cmd /k "cd /d %ROOT_DIR%\\frontend && npm run dev -- --host 127.0.0.1 --port 5173"
timeout /t 2 >nul
start "" "http://127.0.0.1:5173/AiMenu/"

pause
