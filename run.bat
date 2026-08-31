@echo off
rem ============================================================
rem  Network-DNS-Monitoring Web Clone - run script (development server)
rem  Dev-only. For production use gunicorn + a real PostgreSQL.
rem  Credentials are read from a local .env file (not committed).
rem ============================================================
setlocal enableextensions

cd /d "%~dp0"

rem --- Pick a dev port (override with NEXTDNS_PORT env var). ---
set "PORT=%NEXTDNS_PORT%"
if "%PORT%"=="" set "PORT=8090"

rem --- Load .env if present.
rem     Uses a :setenv subroutine with parameter expansion
rem     (%%~2) so special chars such as '!' are preserved
rem     (delayed expansion is intentionally OFF). ---
if exist ".env" (
  for /f "usebackq delims=" %%L in (".env") do (
    echo(%%L | findstr /r "^[A-Za-z_][A-Za-z0-9_]*=" >nul && (
      for /f "tokens=1* delims==" %%A in ("%%L") do (
        call :setenv "%%A" "%%B"
      )
    )
  )
)

if not defined NEXTDNS_DB_PASSWORD (
    echo [!] NEXTDNS_DB_PASSWORD is not set in the environment or in .env.
    echo     Copy .env.example to .env and set NEXTDNS_DB_PASSWORD, or export it.
    exit /b 1
)

python --version >nul 2>&1 || (
    echo [!] Python not found on PATH. Install Python 3.12+.
    exit /b 1
)

echo [i] Installing dependencies...
call python -m pip install -q -r requirements.txt
if errorlevel 1 (echo [!] pip install failed. & exit /b 1)

echo [i] Applying database migrations...
call python manage.py migrate
if errorlevel 1 (echo [!] Database migration failed. Check the PostgreSQL connection above. & exit /b 1)

echo [i] Starting development server at http://127.0.0.1:%PORT%
echo     First admin: python manage.py createsuperuser
call python manage.py runserver 127.0.0.1:%PORT%

endlocal
exit /b %errorlevel%

:setenv
rem %1 = variable name, %2 = value (parameter expansion preserves '!')
if not "%~1"=="" set "%~1=%~2"
goto :eof
