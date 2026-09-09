@echo off
rem Backend КИС: uvicorn с перезагрузкой. Порт и хост берутся из ..\.env
cd /d "%~dp0\..\backend"

if not exist ".venv\Scripts\python.exe" (
    echo Виртуальное окружение не найдено.
    echo Сначала выполните:  powershell -ExecutionPolicy Bypass -File ..\scripts\setup.ps1
    exit /b 1
)

".venv\Scripts\python.exe" -m app.main
exit /b %errorlevel%
