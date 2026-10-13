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
    echo A working Windows Python Tcl/Tk installation is required. Check sandbox access or repair Python.
    exit /b 1
)
"%BUILD_PYTHON%" scripts\build_setup.py || exit /b 1
"%PY%" scripts\verify_distribution.py || exit /b 1
echo Wood Setup is in release\WoodSetup.exe. Copy it to ..\WoodWebsite\release\downloads when ready.
