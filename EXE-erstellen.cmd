@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Bitte zuerst Start-Larp Studio.cmd ausfuehren.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip --isolated --disable-pip-version-check install --index-url https://pypi.org/simple pyinstaller==6.22.3
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "Larp Studio.spec"
if errorlevel 1 goto failed
echo Fertig: dist\Larp Studio\Larp Studio.exe
echo Den gesamten Ordner dist\Larp Studio zusammen behalten.
pause
exit /b 0
:failed
echo Der EXE-Build ist fehlgeschlagen. Siehe Meldung oben.
pause
exit /b 1
