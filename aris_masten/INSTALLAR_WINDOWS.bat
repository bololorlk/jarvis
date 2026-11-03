@echo off
setlocal
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "aris_masten\install_windows.ps1"
if errorlevel 1 pause
