@echo off
echo ============================================
echo   CloudGuard KR Elixir - Production Server
echo ============================================
echo.

cd /d "C:\Users\krelixiradmin\Downloads\Cloud_Guard\backend"

echo Starting CloudGuard on port 80...
echo Access URL: http://10.238.46.116
echo.

"C:\Users\krelixiradmin\Downloads\Cloud_Guard\backend\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 80 --workers 4 --timeout-keep-alive 120

pause
