@echo off
rem ============================================================
rem  Push the Network-DNS-Monitoring Web Clone to GitHub.
rem  Remote: https://github.com/harys-rifai/Network-DNS-Monitoring.git
rem  Self-contained: initialises its own git repo, commits,
rem  and pushes branch "main". Respects .gitignore (.env excluded).
rem ============================================================
setlocal enableextensions
set "REMOTE=https://github.com/harys-rifai/Network-DNS-Monitoring.git"

cd /d "%~dp0"

where git >nul 2>&1 || (echo [!] git not found on PATH. & exit /b 1)

if not exist ".git" (
    echo [i] Initialising git repository.
    git init -b main
    if errorlevel 1 (echo [!] git init failed. & exit /b 1)
)

rem Ensure a .gitignore is present.
if not exist ".gitignore" (
    echo [!] No .gitignore found. Run from the project root with .gitignore present.
    exit /b 1
)

echo [i] Staging files.
git add .

rem Commit only if something is staged. git diff --cached --quiet exits 1
rem when there ARE staged changes (0 = none).
git diff --cached --quiet
if errorlevel 1 (
    echo [i] Committing.
    git commit -q -m "Add Network-DNS-Monitoring web clone"
    if errorlevel 1 (echo [!] Commit failed. & exit /b 1)
) else (
    echo [i] Nothing to commit.
)

git branch -M main 2>nul

rem Set (or update) the origin remote.
for /f "delims=" %%R in ('git remote get-url origin 2^>nul') do set "CUR=%R"
if defined CUR (
    echo [i] Remote already set to "%CUR%"; updating to %REMOTE%
    git remote set-url origin "%REMOTE%"
) else (
    git remote add origin "%REMOTE%"
)

echo [i] Pushing branch main to %REMOTE% ...
echo     (HTTPS may require a GitHub Personal Access Token on first push.)
git push -u origin main
if errorlevel 1 (echo [!] Push failed. & exit /b 1)
echo [i] Done. Remote: %REMOTE%

endlocal
exit /b %errorlevel%
