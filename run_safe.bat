@echo off
chcp 65001 >nul
cd /d "%~dp0"
set DESKTOP_PET_SAFE=1
set KIVY_GL_BACKEND=glew

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py --safe
) else (
    python run.py --safe
)

if errorlevel 1 pause
