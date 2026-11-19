@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM RsAgent Windows Build Script
REM Usage: build-win.bat [--skip-install] [--skip-build] [--x64-only]
REM ============================================================================

set "REPO_ROOT=%~dp0..\..\..\"
set "DESKTOP_DIR=%~dp0..\"
set "UI_DIR=%REPO_ROOT%ui"
set "MEMORY_DIR=%REPO_ROOT%src\context\memory\edgeclaw-memory-core"
set "RESOURCES=%DESKTOP_DIR%resources"

set SKIP_INSTALL=0
set SKIP_BUILD=0
set X64_ONLY=0

for %%a in (%*) do (
    if "%%a"=="--skip-install" set SKIP_INSTALL=1
    if "%%a"=="--skip-build" set SKIP_BUILD=1
    if "%%a"=="--x64-only" set X64_ONLY=1
)

echo.
echo ========================================
echo  RsAgent Windows Builder
echo ========================================
echo.

REM --- Step 1: Skip git pull (local build) ---
echo [1] Skipping git pull (local build)

REM --- Step 2: Install dependencies ---
if %SKIP_INSTALL%==0 (
    echo.
    echo [2] Installing npm dependencies...
    cd /d "%REPO_ROOT%"
    call npm install --ignore-scripts
    if errorlevel 1 (
        echo ERROR: npm install failed
        exit /b 1
    )
    
    echo.
    echo [2a] Installing Windows-specific dependencies...
    call npm install @vscode/ripgrep-win32-x64
    if errorlevel 1 (
        echo WARNING: @vscode/ripgrep-win32-x64 install failed
    )
    
    echo.
    echo [2b] Linking local memory-core package...
    call npm install edgeclaw-memory-core@file:src/context/memory/edgeclaw-memory-core
    if errorlevel 1 (
        echo WARNING: edgeclaw-memory-core link failed
    )
    
    cd /d "%DESKTOP_DIR%"
    call npm install
    if errorlevel 1 (
        echo ERROR: desktop npm install failed
        exit /b 1
    )
    echo OK
) else (
    echo [2] Skipping npm install ^(--skip-install^)
)

REM --- Step 3: Download Node.js for Windows ---
if not exist "%RESOURCES%\node-bin\node.exe" (
    echo.
    echo [3] Downloading Node.js v22.14.0 for Windows x64...
    mkdir "%RESOURCES%\node-bin" 2>nul
    cd /d "%RESOURCES%\node-bin"
    curl -fsSL -o node-win-x64.zip https://nodejs.org/dist/v22.14.0/node-v22.14.0-win-x64.zip
    tar xf node-win-x64.zip node-v22.14.0-win-x64/node.exe
    move node-v22.14.0-win-x64\node.exe node.exe
    rd /s /q node-v22.14.0-win-x64
    del node-win-x64.zip
    echo OK: & node.exe --version
) else (
    echo [3] Node.js binary already present, skipping download
)

REM --- Step 3b: Rebuild native deps for bundled Node ABI ---
echo.
echo [3b] Rebuilding native deps for bundled Node...
cd /d "%REPO_ROOT%"
if exist node_modules\better-sqlite3\build rd /s /q node_modules\better-sqlite3\build
set "PATH=%RESOURCES%\node-bin;%PATH%"
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
"%RESOURCES%\node-bin\node.exe" "%NPM_CLI%" rebuild better-sqlite3
if errorlevel 1 (
    echo ERROR: better-sqlite3 native rebuild failed
    exit /b 1
)
echo OK

REM --- Step 4: Download Bun for Windows ---
if not exist "%RESOURCES%\bun-bin\bun.exe" (
    echo.
    echo [4] Downloading Bun v1.3.10 for Windows x64...
    mkdir "%RESOURCES%\bun-bin" 2>nul
    cd /d "%RESOURCES%\bun-bin"
    curl -fsSL -o bun-win-x64.zip https://github.com/oven-sh/bun/releases/download/bun-v1.3.10/bun-windows-x64.zip
    tar xf bun-win-x64.zip bun-windows-x64/bun.exe
    move bun-windows-x64\bun.exe bun.exe
    rd /s /q bun-windows-x64
    del bun-win-x64.zip
    echo OK: & bun.exe --version
) else (
    echo [4] Bun binary already present, skipping download
)

REM --- Step 5: Generate icons ---
echo.
echo [5] Generating application icons...
cd /d "%DESKTOP_DIR%"
if exist "%DESKTOP_DIR%assets/logo-dark-1024.png" (
    node scripts/generate-icon.js
    if errorlevel 1 (
        echo ERROR: icon generation failed
        exit /b 1
    )
) else (
    echo WARNING: logo-dark-1024.png not found, skipping icon generation
)
echo OK

REM --- Step 6: Build rsagentui ---
if %SKIP_BUILD%==0 (
    echo.
    echo [6] Building rsagentui ^(vite^)...
    cd /d "%UI_DIR%"
    call npx vite build
    if errorlevel 1 (
        echo ERROR: vite build failed
        exit /b 1
    )
    echo OK
) else (
    echo [6] Skipping builds ^(--skip-build^)
    goto :skip_builds
)

REM --- Step 7: Build memory-core + rsagent-main ---
echo.
echo [7] Building memory-core + rsagent-main ^(tsc^)...
cd /d "%MEMORY_DIR%"
if exist lib rd /s /q lib
call npx tsc -p tsconfig.json
if errorlevel 1 (
    echo ERROR: memory-core tsc build failed
    exit /b 1
)
cd /d "%REPO_ROOT%"
call npx tsc -p tsconfig.json
if errorlevel 1 (
    echo ERROR: tsc build failed
    exit /b 1
)
mkdir dist\src\extension\plugins 2>nul
xcopy /E /I /Y src\extension\plugins\builtin dist\src\extension\plugins\builtin >nul
echo OK

REM --- Step 7b: Ensure ui/node_modules has ALL (including transitive) hoisted dependencies ---
echo.
echo [7b] Ensuring ui/node_modules has all workspace dependencies (including transitive)...
cd /d "%UI_DIR%"
node "%DESKTOP_DIR%scripts\copy-hoisted-deps.cjs" "%REPO_ROOT%node_modules" "%UI_DIR%\node_modules" "%UI_DIR%\package.json"
if errorlevel 1 (
    echo ERROR: hoisted dependency copy failed
    exit /b 1
)
echo   workspace dependencies ensured

REM --- Step 8: Create bundle tars ---
echo.
echo [8] Creating bundle tars...

cd /d "%UI_DIR%"
tar cf "%RESOURCES%\rsagentui-bundle.tar" ^
    --exclude=node_modules/.cache --exclude=node_modules/.bin ^
    --exclude=node_modules/typescript --exclude=node_modules/@types ^
    --exclude=node_modules/vite --exclude=node_modules/@vitejs ^
    --exclude=node_modules/rollup --exclude=node_modules/@rollup ^
    --exclude=node_modules/esbuild --exclude=node_modules/@esbuild ^
    --exclude=node_modules/eslint --exclude=node_modules/@eslint ^
    package.json server shared dist scripts node_modules
echo   rsagentui-bundle.tar OK

REM --- Step 8a: Create lean rsagent-main-bundle via staging (no source code, no dev deps) ---
echo.
echo [8a] Creating lean rsagent-main-bundle via staging ^(production-only, no source^)...
set "STAGING=%DESKTOP_DIR%build-staging\rsagent-main"
if exist "%STAGING%" rd /s /q "%STAGING%"
mkdir "%STAGING%\dist" 2>nul

REM Copy compiled output and runtime scripts (no .ts source)
xcopy /E /I /Y "%REPO_ROOT%dist\src" "%STAGING%\dist\src" >nul
xcopy /E /I /Y "%REPO_ROOT%scripts\bootstrap-pilotdeck-config.mjs" "%STAGING%\scripts\" >nul

REM Create production-only package.json (no devDeps, no workspaces, no file: deps)
echo {"name":"rs-agent","version":"0.1.0","private":true,"type":"module","dependencies":{"@larksuiteoapi/node-sdk":"^1.65.0","@modelcontextprotocol/sdk":"^1.29.0","@types/react":"^19.2.14","@types/turndown":"^5.0.6","@vscode/ripgrep":"^1.18.0","@vscode/ripgrep-win32-x64":"^1.18.0","docx":"^9.7.1","ink":"^7.0.2","ink-text-input":"^6.0.0","js-tiktoken":"^1.0.21","jsonrepair":"^3.14.0","mupdf":"^1.27.0","react":"^19.2.6","slice-ansi":"^9.0.0","string-width":"^8.2.1","strip-ansi":"^7.2.0","turndown":"^7.2.4","weixin-ilink":"^0.1.0","ws":"^8.21.0","yaml":"^2.8.4"}} > "%STAGING%\package.json"

REM Install production dependencies only (without scripts for speed)
cd /d "%STAGING%"
call npm install --no-scripts --no-package-lock --no-audit --no-fund
if errorlevel 1 (
    echo ERROR: staging npm install failed
    exit /b 1
)

REM Replace staging @modelcontextprotocol/sdk with repo pre-built SDK (which already has correct dist/esm + dist/cjs)
REM Reason: staging npm install may not run prepack scripts (--no-scripts) and produces incomplete/broken dist/esm.
if exist "%STAGING%\node_modules\@modelcontextprotocol\sdk" (
    echo   Copying pre-built @modelcontextprotocol/sdk from repo...
    if exist "%STAGING%\node_modules\@modelcontextprotocol\sdk" rd /s /q "%STAGING%\node_modules\@modelcontextprotocol\sdk"
    xcopy /E /I /Y "%REPO_ROOT%node_modules\@modelcontextprotocol\sdk" "%STAGING%\node_modules\@modelcontextprotocol\sdk" >nul
    echo   @modelcontextprotocol/sdk OK
)
cd /d "%STAGING%"

REM Copy pre-compiled native module and local package (not available via npm)
xcopy /E /I /Y "%REPO_ROOT%node_modules\better-sqlite3" "%STAGING%\node_modules\better-sqlite3" >nul
mkdir "%STAGING%\node_modules\edgeclaw-memory-core" 2>nul
copy /Y "%REPO_ROOT%src\context\memory\edgeclaw-memory-core\package.json" "%STAGING%\node_modules\edgeclaw-memory-core\" >nul
xcopy /E /I /Y "%REPO_ROOT%src\context\memory\edgeclaw-memory-core\lib" "%STAGING%\node_modules\edgeclaw-memory-core\lib" >nul
if exist "%REPO_ROOT%src\context\memory\edgeclaw-memory-core\ui-source" xcopy /E /I /Y "%REPO_ROOT%src\context\memory\edgeclaw-memory-core\ui-source" "%STAGING%\node_modules\edgeclaw-memory-core\ui-source" >nul

REM Remove source code files (.ts except .d.ts, .js.map) for source code protection
del /S /Q "%STAGING%\dist\*.js.map" 2>nul
for /r "%STAGING%\dist" %%f in (*.ts) do (
    echo %%f | findstr /i "\.d\.ts$" >nul || del "%%f"
)

REM Create tar from staging directory
cd /d "%STAGING%"
tar cf "%RESOURCES%\rsagent-main-bundle.tar" dist scripts node_modules package.json
if errorlevel 1 (
    echo ERROR: rsagent-main-bundle.tar creation failed
    exit /b 1
)

REM Clean up staging
cd /d "%DESKTOP_DIR%"
rd /s /q "%STAGING%" 2>nul
echo   rsagent-main-bundle.tar OK ^(lean, production-only, no source code^)

cd /d "%MEMORY_DIR%"
tar cf "%RESOURCES%\rsagent-memory-core-bundle.tar" ^
    package.json lib ui-source
echo   rsagent-memory-core-bundle.tar OK

cd /d "%REPO_ROOT%\rs-engine"
tar cf "%RESOURCES%\rs-engine-bundle.tar" ^
    --exclude=*/__pycache__ --exclude=*.pyc ^
    *
echo   rs-engine-bundle.tar OK

cd /d "%REPO_ROOT%\products"
tar cf "%RESOURCES%\products-bundle.tar" ^
    --exclude=*/__pycache__ --exclude=*.pyc ^
    *
echo   products-bundle.tar OK

cd /d "%REPO_ROOT%\open-earth-engine"
tar cf "%RESOURCES%\open-earth-engine-bundle.tar" ^
    --exclude=*/__pycache__ --exclude=*.pyc ^
    *
echo   open-earth-engine-bundle.tar OK

:skip_builds

REM --- Step 9: Generate build-info.json ---
echo.
echo [9] Generating build-info.json...
cd /d "%REPO_ROOT%"
for /f "delims=" %%i in ('git rev-parse --short HEAD 2^>nul') do set "GIT_SHA=%%i"
for /f "delims=" %%i in ('git rev-parse HEAD 2^>nul') do set "GIT_FULL_SHA=%%i"
for /f "delims=" %%i in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "GIT_BRANCH=%%i"
for /f "delims=" %%i in ('node -e "console.log(require('./apps/desktop/package.json').version)"') do set "VERSION=%%i"

set "BUILD_DATE=%date:~0,4%-%date:~5,2%-%date:~8,2%"

mkdir "%DESKTOP_DIR%dist" 2>nul
echo {"version":"%VERSION%","gitSha":"%GIT_SHA%","gitFullSha":"%GIT_FULL_SHA%","gitBranch":"%GIT_BRANCH%","buildDate":"%BUILD_DATE%","mode":"win-build"} > "%DESKTOP_DIR%dist\build-info.json"
echo OK: v%VERSION% (%GIT_SHA%)

REM --- Step 10: Compile desktop TypeScript ---
echo.
echo [10] Compiling desktop TypeScript...
cd /d "%DESKTOP_DIR%"
call npx tsc
if errorlevel 1 (
    echo ERROR: desktop tsc failed
    exit /b 1
)
echo OK

REM --- Step 11: electron-builder ---
echo.
echo [11] Running electron-builder...
set CSC_IDENTITY_AUTO_DISCOVERY=false

if %X64_ONLY%==1 (
    call npx electron-builder --win --x64
) else (
    call npx electron-builder --win --x64 --arm64
)
if errorlevel 1 (
    echo ERROR: electron-builder failed
    exit /b 1
)

echo.
echo ========================================
echo  Build complete!
echo ========================================
echo.
echo Output:
dir /b "%DESKTOP_DIR%dist-electron\*.exe"
echo.
echo Location: %DESKTOP_DIR%dist-electron\
