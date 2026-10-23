@echo off
rem Double-click this file to open the report program (app.py).
cd /d "%~dp0"
".venv\Scripts\python.exe" -c "import matplotlib, reportlab, mysql.connector, pypdfium2, PIL" 2>nul
if errorlevel 1 (
    echo Python or the libraries are missing. Follow "Get started" in README.md first.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" app.py
