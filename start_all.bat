@echo off
echo ========================================================
echo   Launching DocuMind RAG (Backend + Frontend)
echo ========================================================
start "DocuMind Backend (FastAPI)" cmd /k "cd /d %~dp0backend && call .\venv\Scripts\activate.bat && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul
start "DocuMind Frontend (Vite)" cmd /k "cd /d %~dp0frontend && npm run dev"
echo.
echo Both servers have been launched in separate windows!
echo - Frontend UI:  http://localhost:5173
echo - Backend API:  http://127.0.0.1:8000
echo - Swagger Docs: http://127.0.0.1:8000/docs
echo ========================================================
