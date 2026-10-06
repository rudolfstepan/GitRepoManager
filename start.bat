@echo off
setlocal
cd /d "%~dp0"
where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw "%~dp0app.py" %*
    exit /b
)
where pyw >nul 2>nul
if not errorlevel 1 (
    start "" pyw -3 "%~dp0app.py" %*
    exit /b
)
echo Python 3 mit Tkinter wurde nicht gefunden. Bitte Python installieren.
pause
