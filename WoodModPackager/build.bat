@echo off
setlocal
cd /d "%~dp0" || exit /b 1
set "WORKSPACE=%~dp0.."
set "PY=%WORKSPACE%\BuildEnvironment\.venv\Scripts\python.exe"
if not exist "%PY%" py -3.10 -m venv "%WORKSPACE%\BuildEnvironment\.venv" || exit /b 1
"%PY%" -m pip install -r requirements.txt || exit /b 1
"%PY%" -m unittest discover -s tests -v || exit /b 1
set "BUILD_PYTHON=%PY%"
"%PY%" -c "import tkinter; tkinter.Tcl().eval('info library')" >nul 2>&1
if errorlevel 1 (
    if not exist "C:\msys64\ucrt64\bin\python.exe" exit /b 1
    set "BUILD_PYTHON=C:\msys64\ucrt64\bin\python.exe"
    set "PYTHONPATH=%WORKSPACE%\BuildEnvironment\.venv\Lib\site-packages;%CD%"
)
"%BUILD_PYTHON%" scripts\build_packager.py || exit /b 1
echo Wood Mod Packager is in release\WoodModPackager.exe. Copy it to WoodWebsite\release\downloads when ready.
