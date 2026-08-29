@echo off
setlocal

REM Determine the directory of this batch file
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=python"
    goto :RUN
)

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py"
    goto :RUN
)

REM Python not found error
echo.
echo ============================================================
echo ZeroForge could not find Python.
echo ============================================================
echo.
echo Please install Python 3.x and make sure
echo Python is available from the command line.
echo.
echo Then run ZeroForge again.
echo.
exit /b 1

:RUN
"%PY_CMD%" -m zeroforge %*
exit /b %ERRORLEVEL%
