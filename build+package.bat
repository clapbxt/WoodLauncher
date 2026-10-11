@echo off
setlocal
cd /d "%~dp0" || exit /b 1
if not exist ".venv\Scripts\python.exe" py -3.10 -m venv .venv || exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt || exit /b 1
".venv\Scripts\python.exe" -m unittest discover -s tests -v || exit /b 1
".venv\Scripts\python.exe" scripts\build_release.py || exit /b 1
".venv\Scripts\python.exe" scripts\verify_distribution.py || exit /b 1
