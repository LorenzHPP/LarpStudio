@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
py -3.13 -c "import sys; raise SystemExit(sys.version_info < (3, 9))" >nul 2>&1
if not errorlevel 1 goto python313
py -3 -c "import sys; raise SystemExit(sys.version_info < (3, 9))" >nul 2>&1
if not errorlevel 1 goto python3
python -c "import sys; raise SystemExit(sys.version_info < (3, 9))" >nul 2>&1
if not errorlevel 1 goto python
echo Python fehlt. Bitte normales Python 3.13 von python.org installieren.
echo Bei der Installation Add python.exe to PATH aktivieren.
pause
exit /b 1
:python313
start "" /b pyw -3.13 "%~dp0bootstrap.py"
exit /b 0
:python3
start "" /b pyw -3 "%~dp0bootstrap.py"
exit /b 0
:python
python "%~dp0bootstrap.py"
endlocal
