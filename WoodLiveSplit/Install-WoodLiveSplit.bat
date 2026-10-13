@echo off
setlocal
title Wood LiveSplit Setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-WoodLiveSplit.ps1"
if errorlevel 1 (
  echo.
  echo Setup could not finish. Read the message above.
  pause
  exit /b 1
)
echo.
pause
