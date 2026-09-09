@echo off
rem ============================================================
rem  Запуск КИС «Учёт клиентов» одним файлом:
rem  PostgreSQL -> backend -> frontend, каждый в своём окне.
rem  Предварительно один раз выполните scripts\setup.ps1
rem ============================================================
setlocal
cd /d "%~dp0\.."

echo [1/3] Проверяю и при необходимости поднимаю PostgreSQL...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\pg-setup.ps1" -SkipDownload
if errorlevel 1 (
    echo.
    echo Не удалось запустить PostgreSQL. Сначала выполните установку:
    echo     powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
    pause
    exit /b 1
)

echo [2/3] Запускаю backend на http://127.0.0.1:8000 ...
start "CIS backend" cmd /k ""%~dp0run-backend.cmd""

echo [3/3] Запускаю frontend на http://127.0.0.1:5173 ...
start "CIS frontend" cmd /k ""%~dp0run-frontend.cmd""

echo.
echo Оба сервера стартуют в отдельных окнах.
echo Через несколько секунд откройте в браузере:  http://127.0.0.1:5173
echo Вход: manager / manager123
echo.
echo Чтобы остановить систему, закройте эти два окна серверов.
pause
