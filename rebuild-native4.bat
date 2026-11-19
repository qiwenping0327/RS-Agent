@echo off
setlocal enabledelayedexpansion

set "REPO_ROOT=D:\project\PilotDeck"
set "RESOURCES=%REPO_ROOT%\apps\desktop\resources"

echo ========================================
echo Rebuilding better-sqlite3 for bundled Node v22.14.0
echo ========================================

if not exist "%RESOURCES%\node-bin\node.exe" (
    echo ERROR: bundled node.exe not found
    exit /b 1
)

echo [1] Finding npm-cli.js...
set "NPM_CMD="
for /f "delims=" %%i in ('where npm.cmd 2^>nul') do (
    if not defined NPM_CMD set "NPM_CMD=%%i"
)
if not defined NPM_CMD (
    echo ERROR: npm.cmd not found
    exit /b 1
)
for %%i in ("%NPM_CMD%") do set "NPM_DIR=%%~dpi"
set "NPM_CLI=%NPM_DIR%node_modules\npm\bin\npm-cli.js"
if not exist "%NPM_CLI%" (
    echo ERROR: npm-cli.js not found: %NPM_CLI%
    exit /b 1
)
echo Found npm-cli.js: %NPM_CLI%

echo [2] Deleting old build directory...
if exist "%REPO_ROOT%\node_modules\better-sqlite3\build" (
    rd /s /q "%REPO_ROOT%\node_modules\better-sqlite3\build"
    echo Deleted old build
)

echo [3] Rebuilding better-sqlite3...
cd /d "%REPO_ROOT%"
set "PATH=%RESOURCES%\node-bin;%PATH%"
"%RESOURCES%\node-bin\node.exe" "%NPM_CLI%" rebuild better-sqlite3

if errorlevel 1 (
    echo ERROR: better-sqlite3 native rebuild failed
    exit /b 1
)

echo [4] Verifying build...
if not exist "%REPO_ROOT%\node_modules\better-sqlite3\build\Release\better_sqlite3.node" (
    echo ERROR: build output not found
    exit /b 1
)
dir "%REPO_ROOT%\node_modules\better-sqlite3\build\Release"

echo.
echo ========================================
echo SUCCESS: better-sqlite3 rebuilt for Node v22.14.0
echo ========================================