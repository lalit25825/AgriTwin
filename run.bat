@echo off
setlocal
if not exist .venv\Scripts\python.exe (
  echo Virtual environment not found. Run the setup commands in README.md first.
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m uvicorn backend.app.main:app --reload --port 8000
