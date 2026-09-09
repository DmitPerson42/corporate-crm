@echo off
rem Frontend КИС: dev-сервер Vite на http://127.0.0.1:5173
cd /d "%~dp0\..\frontend"

if not exist "..\node_modules" if not exist "node_modules" (
    echo Модули npm не установлены.
    echo Сначала выполните:  npm install   ^(в корне проекта^)
    exit /b 1
)

call npm run dev
exit /b %errorlevel%
