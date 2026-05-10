@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  Google Form Automation Tool - Build Script
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "VENV_PYBABEL=%SCRIPT_DIR%.venv\Scripts\pybabel.exe"
set "BUILD_MODE=%~1"
if "%BUILD_MODE%"=="" set "BUILD_MODE=debug"
if /I "%BUILD_MODE%"=="release" (
    set "GOOGLE_FORM_TOOL_CONSOLE=0"
) else (
    set "BUILD_MODE=debug"
    set "GOOGLE_FORM_TOOL_CONSOLE=1"
)

:: Verify venv exists
if not exist "%VENV_PYTHON%" (
    echo [ERROR] .venv not found. Run this first:
    echo   uv sync
    pause & exit /b 1
)

echo Using Python: %VENV_PYTHON%
echo Build mode: %BUILD_MODE%
"%VENV_PYTHON%" --version
echo.

:: [1/4] Compile Babel translations
echo [1/4] Compiling translations...
if exist "%VENV_PYBABEL%" (
    "%VENV_PYBABEL%" compile -d "%SCRIPT_DIR%app\translations"
    if errorlevel 1 (
        echo [WARN] pybabel compile failed - existing .mo files will be used.
    ) else (
        echo       Translations compiled OK.
    )
) else (
    echo [WARN] pybabel.exe not found - existing .mo files will be used.
)
echo.

:: [2/4] Install PyInstaller via uv (preferred) or python -m pip
echo [2/4] Checking PyInstaller...
"%VENV_PYTHON%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo       Not found - installing via uv...
    where uv >nul 2>&1
    if errorlevel 1 (
        echo       uv not found, trying python -m pip...
        "%VENV_PYTHON%" -m pip install --timeout 120 --retries 5 pyinstaller
    ) else (
        uv pip install --python "%VENV_PYTHON%" pyinstaller
    )
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller. Check internet connection.
        pause & exit /b 1
    )
) else (
    echo       PyInstaller already installed - OK.
)
echo.

:: [3/4] Sync dependencies
echo [3/4] Syncing dependencies...
where uv >nul 2>&1
if not errorlevel 1 (
    uv sync --quiet
    echo       Dependencies synced via uv.
) else (
    "%VENV_PYTHON%" -m pip install --timeout 120 --retries 5 -r "%SCRIPT_DIR%requirements.txt" --quiet
    echo       Dependencies installed via pip.
)
echo.

:: [4/4] Build
echo [4/4] Building exe with PyInstaller...
"%VENV_PYTHON%" -m PyInstaller "%SCRIPT_DIR%google_form_tool.spec" --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Build failed. See output above.
    pause & exit /b 1
)

echo.
echo ============================================================
echo  Build complete!
echo  Exe: dist\GoogleFormTool\GoogleFormTool.exe
echo.
echo  Backend artifact is ready for Electron packaging.
echo  Use scripts\package-windows.ps1 to build versioned installers from package.json.
echo ============================================================
pause
