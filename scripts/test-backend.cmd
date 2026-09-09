@echo off
rem Интеграционные тесты backend на отдельной базе crm_test.
cd /d "%~dp0\..\backend"

if not exist ".venv\Scripts\python.exe" (
    echo Виртуальное окружение не найдено. Выполните scripts\setup.ps1
    exit /b 1
)

".venv\Scripts\python.exe" -m pytest
exit /b %errorlevel%
