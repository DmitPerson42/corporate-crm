<#
  Разворачивает локальный PostgreSQL без установки и прав администратора:
  скачивает переносимую сборку EDB, создаёт кластер, запускает сервер на 127.0.0.1:5432
  и создаёт роль crm_user с базой crm_db.

  Скрипт идемпотентен: повторный запуск ничего не портит.
  Запуск из корня проекта:  powershell -ExecutionPolicy Bypass -File scripts\pg-setup.ps1
#>
[CmdletBinding()]
param(
    [string]$PgVersion = '17.11-1',
    [int]$Port = 5432,
    [string]$DbName = 'crm_db',
    [string]$DbUser = 'crm_user',
    [string]$DbPassword = 'crm_password',
    [string]$TestDbName = 'crm_test',
    [switch]$SkipDownload
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Vendor = Join-Path $Root '.vendor'
$PgDir = Join-Path $Vendor 'pgsql'
$DataDir = Join-Path $Vendor 'pgdata'
$Bin = Join-Path $PgDir 'bin'
$Log = Join-Path $Vendor 'pg.log'
$SuperPass = 'postgres'

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "    $msg" -ForegroundColor Green }

if (-not (Test-Path (Join-Path $Bin 'initdb.exe'))) {
    if ($SkipDownload) { throw "Бинарники PostgreSQL не найдены в $Bin" }
    New-Item -ItemType Directory -Force -Path $Vendor | Out-Null
    $zipName = "postgresql-$PgVersion-windows-x64-binaries.zip"
    $url = "https://get.enterprisedb.com/postgresql/$zipName"
    $zipPath = Join-Path $Vendor $zipName
    Write-Step "Скачиваю переносимый PostgreSQL $PgVersion (~325 МБ)"
    Write-Host "    $url"
    $curl = (Get-Command curl.exe -ErrorAction SilentlyContinue).Source
    if ($curl) {
        & $curl -L --fail --retry 3 -o $zipPath $url
        if ($LASTEXITCODE -ne 0) { throw "Не удалось скачать $url" }
    } else {
        Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
    }
    Write-Step "Распаковываю в $PgDir"
    if (Test-Path $PgDir) { Remove-Item $PgDir -Recurse -Force }
    & tar -xf $zipPath -C $Vendor
    if ($LASTEXITCODE -ne 0) { throw 'Распаковка архива не удалась' }
    Remove-Item $zipPath -Force
    Write-Ok 'Бинарники готовы'
} else {
    Write-Ok "PostgreSQL уже распакован: $PgDir"
}

# --- кластер ---------------------------------------------------------------
if (-not (Test-Path (Join-Path $DataDir 'PG_VERSION'))) {
    Write-Step "Инициализирую кластер в $DataDir"
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    $pwFile = Join-Path $Vendor 'superpass.txt'
    Set-Content -Path $pwFile -Value $SuperPass -NoNewline -Encoding ascii
    & (Join-Path $Bin 'initdb.exe') -D $DataDir -U postgres -E UTF8 `
        --pwfile=$pwFile --auth-local=trust --auth-host=scram-sha-256
    $initCode = $LASTEXITCODE
    Remove-Item $pwFile -Force
    if ($initCode -ne 0) { throw "initdb завершился с кодом $initCode" }
    Write-Ok 'Кластер создан'
} else {
    Write-Ok "Кластер уже существует: $DataDir"
}

# --- запуск сервера --------------------------------------------------------
$serverUp = $false
try {
    & (Join-Path $Bin 'pg_isready.exe') -h 127.0.0.1 -p $Port -q 2>$null | Out-Null
    $serverUp = ($LASTEXITCODE -eq 0)
} catch { $serverUp = $false }

if (-not $serverUp) {
    Write-Step "Запускаю PostgreSQL на 127.0.0.1:$Port"
    & (Join-Path $Bin 'pg_ctl.exe') -D $DataDir -l $Log -w -t 60 `
        -o "-p $Port -c listen_addresses=127.0.0.1" start
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Последние строки журнала:' -ForegroundColor Yellow
        if (Test-Path $Log) { Get-Content $Log -Tail 20 }
        throw "pg_ctl не смог запустить сервер (код $LASTEXITCODE)"
    }
    Write-Ok 'Сервер запущен'
} else {
    Write-Ok "Сервер уже запущен на порту $Port"
}

# --- роль и база -----------------------------------------------------------
$env:PGPASSWORD = $SuperPass
$psql = Join-Path $Bin 'psql.exe'

function Invoke-PsqlSuper($sql) {
    & $psql -h 127.0.0.1 -p $Port -U postgres -d postgres -v ON_ERROR_STOP=1 -q -c $sql
    if ($LASTEXITCODE -ne 0) { throw "psql отклонил: $sql" }
}

Write-Step "Создаю роль $DbUser (если нет)"
Invoke-PsqlSuper "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DbUser') THEN CREATE ROLE $DbUser LOGIN PASSWORD '$DbPassword'; ELSE ALTER ROLE $DbUser WITH LOGIN PASSWORD '$DbPassword'; END IF; END `$`$;"
Write-Ok "Роль $DbUser готова"

function Ensure-Database([string]$name) {
    $exists = & $psql -h 127.0.0.1 -p $Port -U postgres -d postgres -tAc `
        "SELECT 1 FROM pg_database WHERE datname = '$name'"
    if ($LASTEXITCODE -ne 0) { throw "Не удалось опросить список баз" }
    if ("$exists".Trim() -ne '1') {
        Invoke-PsqlSuper "CREATE DATABASE $name OWNER $DbUser;"
        Write-Ok "База $name создана"
    } else {
        Write-Ok "База $name уже существует"
    }
    Invoke-PsqlSuper "GRANT ALL PRIVILEGES ON DATABASE $name TO $DbUser;"
}

Write-Step "Создаю базу $DbName (владелец $DbUser) и тестовую базу $TestDbName"
Ensure-Database $DbName
if ($TestDbName) { Ensure-Database $TestDbName }
Remove-Item Env:\PGPASSWORD

Write-Host ''
Write-Ok "PostgreSQL готов: postgresql://$DbUser`:$DbPassword@127.0.0.1:$Port/$DbName"
Write-Host '    Superuser для администрирования: postgres / postgres (только для локальной разработки)'
Write-Host ''
