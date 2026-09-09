<#
  Полная установка КИС «Учёт клиентов» с нуля на Windows.

  Один запуск делает всё:
    1) проверяет Python и Node.js;
    2) создаёт .env из .env.example со случайным JWT-секретом;
    3) скачивает и поднимает portable PostgreSQL, создаёт роли и базы;
    4) создаёт виртуальное окружение и ставит Python-зависимости;
    5) накатывает миграции Alembic и наполняет базу менеджером;
    6) ставит npm-зависимости фронтенда.

  Запуск из корня проекта:
      powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#>
[CmdletBinding()]
param(
    [string]$PgVersion = '17.11-1',
    [switch]$NoDemo,
    [switch]$SkipNpm
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$VenvPython = Join-Path $Backend '.venv\Scripts\python.exe'
$step = 0
$total = 6

function Write-Step($msg) {
    $script:step++
    Write-Host ''
    Write-Host "[$script:step/$total] $msg" -ForegroundColor Cyan
}

Write-Host 'Установка корпоративной ИС «Учёт клиентов»' -ForegroundColor White
Write-Host "Каталог проекта: $Root" -ForegroundColor DarkGray

# --- 0. Инструменты --------------------------------------------------------
Write-Step 'Проверяю установленные инструменты'
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) { throw 'Не найден python. Установите Python 3.11 или новее с python.org (галочка Add to PATH).' }
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) { throw 'Не найден node. Установите Node.js 18 или новее с nodejs.org.' }
Write-Host "    python: $(& python --version 2>&1)"
Write-Host "    node:   $(& node --version)"
Write-Host "    npm:    v$(& npm --version)"

# --- 1. .env ---------------------------------------------------------------
Write-Step 'Готовлю файл конфигурации .env'
$envPath = Join-Path $Root '.env'
if (Test-Path $envPath) {
    Write-Host '    .env уже существует — оставляю без изменений'
} else {
    $template = Get-Content (Join-Path $Root '.env.example') -Raw -Encoding utf8
    $bytes = 1..48 | ForEach-Object { Get-Random -Maximum 256 } | ForEach-Object { [byte]$_ }
    $secret = [Convert]::ToBase64String($bytes)
    $template = $template -replace '(?m)^JWT_SECRET=.*$', "JWT_SECRET=$secret"
    # UTF-8 без BOM: иначе первая строка файла читается как «?DATABASE_URL».
    [System.IO.File]::WriteAllText($envPath, $template, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "    создан .env со случайным JWT_SECRET"
}

# --- 2. PostgreSQL ---------------------------------------------------------
Write-Step 'Разворачиваю локальный PostgreSQL'
& (Join-Path $PSScriptRoot 'pg-setup.ps1') -PgVersion $PgVersion

# --- 3. Python-окружение ---------------------------------------------------
Write-Step 'Создаю виртуальное окружение и ставлю зависимости backend'
Set-Location $Backend
if (-not (Test-Path $VenvPython)) {
    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось создать виртуальное окружение' }
}
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install --quiet -r requirements.txt -r dev-requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'pip install завершился с ошибкой' }
Write-Host '    зависимости backend установлены'

# --- 4. Миграции -----------------------------------------------------------
Write-Step 'Накатываю миграции Alembic'
& $VenvPython -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Миграции не применились' }

# --- 5. Начальное наполнение ----------------------------------------------
Write-Step 'Создаю учётную запись менеджера'
if ($NoDemo) {
    & $VenvPython -m app.seed
} else {
    & $VenvPython -m app.seed --demo
}
if ($LASTEXITCODE -ne 0) { throw 'Заполнение базы не выполнилось' }

# --- 6. Frontend -----------------------------------------------------------
Write-Step 'Ставлю зависимости фронтенда'
if ($SkipNpm) {
    Write-Host '    пропущено по флагу -SkipNpm' -ForegroundColor Yellow
} else {
    Set-Location $Root
    & npm install --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'npm install завершился с ошибкой' }
}

Set-Location $Root
Write-Host ''
Write-Host 'Установка завершена.' -ForegroundColor Green
Write-Host ''
Write-Host 'Запуск системы:            scripts\start.cmd   (или npm run dev в корне)'
Write-Host 'Открыть в браузере:         http://127.0.0.1:5173'
Write-Host 'Документация API (Swagger): http://127.0.0.1:8000/docs'
Write-Host 'Вход в систему:            manager / manager123'
Write-Host ''
