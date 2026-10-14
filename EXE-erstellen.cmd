@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Start-Larp Studio.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip --isolated --disable-pip-version-check install --index-url https://pypi.org/simple pyinstaller==6.22.3
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "Larp Studio.spec"
if errorlevel 1 goto failed
echo Done: dist\Larp Studio.exe
echo This EXE includes its required libraries and interface files.
pause
exit /b 0
:failed
echo The EXE build failed. See the message above.
pause
exit /b 1
