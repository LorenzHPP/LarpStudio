@echo off
setlocal
set "ATLAS_TASK_ROOT=%~dp0"
powershell.exe -NoProfile -Command "$atlasShell=New-Object -ComObject WScript.Shell; $atlasDesktop=$atlasShell.SpecialFolders.Item('Desktop'); $atlasLink=$atlasShell.CreateShortcut((Join-Path $atlasDesktop 'Larp Studio.lnk')); $atlasLink.TargetPath=Join-Path $env:ATLAS_TASK_ROOT 'Start-Larp Studio.cmd'; $atlasLink.WorkingDirectory=$env:ATLAS_TASK_ROOT; $atlasLink.IconLocation=Join-Path $env:ATLAS_TASK_ROOT 'ui\assets\larp-studio.ico'; $atlasLink.Description='Larp Studio - Your location studio'; $atlasLink.Save()"
if errorlevel 1 (
  echo Could not create the shortcut.
  pause
  exit /b 1
)
echo Larp Studio shortcut created on your desktop.
echo Keep the Larp Studio folder in this location.
pause
endlocal
