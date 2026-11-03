@echo off
setlocal
cd /d "%~dp0\.."
title ARIS / MASTEN - Windows
py -3.12 -m aris_masten.desktop
if errorlevel 1 (
 echo.
 echo Erro ao iniciar. Confira a instalacao e o Ollama.
 pause
)
