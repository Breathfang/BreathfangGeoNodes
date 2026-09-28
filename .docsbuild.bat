@echo off
setlocal
REM ==========================================================================
REM  DragonGraph's Toolset Pack - documentation live-reload server
REM
REM  Usage:
REM    .docsbuild.bat                  Start on port 8000 with a clean build
REM    .docsbuild.bat 8080             Start on a different port
REM    .docsbuild.bat --port 8080      Same, explicit form
REM    .docsbuild.bat --no-clean       Keep the existing docs/_build output
REM    .docsbuild.bat /?               Show this help
REM
REM  While it runs, press a key to choose an action:
REM    R  force a rebuild          B  open the browser
REM    L  show the build log       C  clean rebuild
REM    Q  stop the server and quit
REM
REM  Requires Python 3.13+ with sphinx and sphinx-autobuild installed.
REM  Run _PythonLibraryAutoSetup.py first if they are missing.
REM ==========================================================================

setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title DragonGraph Docs Builder

REM --------------------------------------------------------------- settings --
set "DOCS_DIR=docs"
set "BUILD_ROOT=docs\_build"
set "BUILD_DIR=docs\_build\html"
set "HOST=127.0.0.1"
set "PORT=8000"
set "STARTUP_TIMEOUT=180"
set "SCRIPT_LOG=.docsbuild.log"
set "SPHINX_LOG=.docsbuild-sphinx.log"
set "TOUCH_FILE=docs\conf.py"
set "CLEAN=1"
set "PY="
set "PORT_PID="
set "PORT_NAME="

REM ------------------------------------------------------------------- args --
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--port" goto take_port
if /i "%~1"=="/p" goto take_port
if /i "%~1"=="--no-clean" (
    set "CLEAN=0"
    shift
    goto parse_args
)
REM A bare number is a port, so `.docsbuild.bat 8080` works.
echo %~1 | findstr /R /C:"^[0-9][0-9]*$" >nul && (
    set "PORT=%~1"
    shift
    goto parse_args
)
if /i "%~1"=="/?" goto usage
if /i "%~1"=="--help" goto usage
echo Unknown option: %~1
goto usage

:take_port
set "PORT=%~2"
shift
shift
goto parse_args

:args_done
call :log INFO "=== Documentation build starting ==="
call :log INFO "Repository : %CD%"

call :find_python
if not defined PY (
    call :log ERROR "Python was not found on PATH."
    call :pause
    endlocal & exit /b 1
)
call :log INFO "Python     : %PY%"

REM -------------------------------------------------------------- preflight --
if not exist "%DOCS_DIR%\" (
    call :log ERROR "Documentation source folder not found: %DOCS_DIR%"
    call :pause
    endlocal & exit /b 1
)

"%PY%" -c "import sphinx, sphinx_autobuild" >nul 2>&1
if errorlevel 1 (
    call :log ERROR "sphinx and sphinx-autobuild are not installed for this interpreter."
    call :log INFO  "Run _PythonLibraryAutoSetup.py to install them, then try again."
    call :pause
    endlocal & exit /b 1
)
call :log INFO "Packages   : sphinx + sphinx-autobuild OK"

call :free_port
if not "%PORT_PID%"=="" (
    call :log WARN "Port %PORT% is busy with PID %PORT_PID% (%PORT_NAME%). Trying to stop it."
    call :kill_port
    if not "%PORT_PID%"=="" (
        call :log ERROR "Port %PORT% is still in use. Close that process or pass --port."
        call :pause
        endlocal & exit /b 1
    )
)

if "%CLEAN%"=="1" (
    call :log INFO "Removing %BUILD_ROOT%..."
    if exist "%BUILD_ROOT%" rmdir /s /q "%BUILD_ROOT%" 2>nul
)
if not exist "%BUILD_ROOT%\" md "%BUILD_ROOT%" 2>nul

REM --------------------------------------------------------- start the build --
call :log INFO "Starting sphinx-autobuild on http://%HOST%:%PORT%/ ..."
start "DragonGraph Docs" /B cmd /c ""%PY%" -m sphinx_autobuild --host %HOST% --port %PORT% --no-color "%DOCS_DIR%" "%BUILD_DIR%" > "%SPHINX_LOG%" 2>&1"

set /a "WAITED=0"
:wait_loop
call :port_pid
if not "%PORT_PID%"=="" goto server_up
call :log_ticker
ping -n 3 127.0.0.1 >nul
set /a "WAITED+=2"
if !WAITED! GEQ %STARTUP_TIMEOUT% goto server_timeout
goto wait_loop

:server_timeout
call :log ERROR "Server did not start within %STARTUP_TIMEOUT% seconds."
call :log INFO  "Last build log lines:"
call :tail_sphinx_log
call :pause
endlocal & exit /b 1

:server_up
call :log INFO "Server ready at http://%HOST%:%PORT%/ (PID %PORT_PID%)."
start "" "http://%HOST%:%PORT%/"
call :log INFO "Browser opened. Press Q in this window to stop the server."

REM ---------------------------------------------------------------- the menu --
:menu
echo.
echo   [R] Rebuild   [B] Browser   [L] Build log   [C] Clean rebuild   [Q] Quit
echo.
choice /C RBLCQ /N /M "  Select: "
if errorlevel 5 goto do_quit
if errorlevel 4 goto do_clean
if errorlevel 3 goto do_log
if errorlevel 2 goto do_browser
if errorlevel 1 goto do_rebuild
goto menu

:do_rebuild
call :log INFO "Manual rebuild requested."
call :touch_source
goto menu

:do_browser
start "" "http://%HOST%:%PORT%/"
goto menu

:do_log
call :tail_sphinx_log
goto menu

:do_clean
call :log INFO "Clean rebuild requested. Press B afterwards to reload the browser."
if exist "%BUILD_ROOT%" rmdir /s /q "%BUILD_ROOT%" 2>nul
md "%BUILD_ROOT%" 2>nul
call :touch_source
goto menu

:do_quit
call :log INFO "Stopping the server..."
call :kill_port
call :log INFO "=== Build stopped ==="
call :pause
endlocal & exit /b 0

REM ------------------------------------------------------------- subroutines --
:find_python
for /f "usebackq delims=" %%P in (`where python 2^>nul`) do (
    "%%P" -c "pass" >nul 2>&1 && (
        set "PY=%%P"
        goto :eof
    )
)
for /f "usebackq delims=" %%P in (`py -3 -c "import sys; print(sys.executable)" 2^>nul`) do (
    set "PY=%%P"
    goto :eof
)
goto :eof

:touch_source
if exist "%TOUCH_FILE%" (
    copy /b "%TOUCH_FILE%" +,, >nul
) else (
    echo.>"%DOCS_DIR%\index.rst"
)
goto :eof

REM Sets PORT_PID to the PID listening on PORT, or empty if nothing is.
:port_pid
set "PORT_PID="
for /f "tokens=5" %%P in ('netstat -ano -p tcp 2^>nul ^| findstr /R /C:"127\.0\.0\.1:%PORT% .*LISTENING"') do (
    set "PORT_PID=%%P"
    goto :eof
)
for /f "tokens=5" %%P in ('netstat -ano -p tcp 2^>nul ^| findstr /R /C:"0\.0\.0\.0:%PORT% .*LISTENING"') do (
    set "PORT_PID=%%P"
    goto :eof
)
for /f "tokens=5" %%P in ('netstat -ano -p tcp 2^>nul ^| findstr /R /C:"\[::1\]:%PORT% .*LISTENING"') do (
    set "PORT_PID=%%P"
    goto :eof
)
goto :eof

:free_port
call :port_pid
if "%PORT_PID%"=="" goto :eof
for /f "usebackq tokens=1 delims=," %%A in (`tasklist /FI "PID eq %PORT_PID%" /FO CSV /NH 2^>nul`) do (
    set "PORT_NAME=%%~A"
    goto :eof
)
goto :eof

REM Stops the process on PORT, but only if it is a Python process.
:kill_port
call :free_port
if "%PORT_PID%"=="" goto :eof
echo !PORT_NAME! | findstr /I /C:"python" /C:"sphinx" >nul
if errorlevel 1 (
    call :log ERROR "PID %PORT_PID% (%PORT_NAME%) is not a Python process. Not killing it."
    set "PORT_PID="
    goto :eof
)
set "KILLED_PID=%PORT_PID%"
taskkill /T /F /PID %KILLED_PID% >nul 2>&1
ping -n 2 127.0.0.1 >nul
call :port_pid
if "%PORT_PID%"=="" call :log INFO "Stopped PID %KILLED_PID%."
goto :eof

REM Rolls its own timer so progress stays visible without a second window.
:log_ticker
set /a "MOD=WAITED %% 10"
if !MOD! EQU 0 echo   Still waiting... !WAITED!s of %STARTUP_TIMEOUT%s
goto :eof

:tail_sphinx_log
if not exist "%SPHINX_LOG%" (
    echo   No build log yet at %SPHINX_LOG%.
    goto :eof
)
powershell -NoProfile -Command "Get-Content -LiteralPath '%SPHINX_LOG%' -Tail 25" 2>nul
echo.
goto :eof

:log
set "LOG_LINE=[%DATE% %TIME%] [%~1] %~2"
echo %LOG_LINE%
>>"%SCRIPT_LOG%" echo %LOG_LINE%
goto :eof

:pause
echo.
pause
goto :eof

:usage
echo.
echo   DragonGraph docs builder
echo   -----------------------
echo     .docsbuild.bat                 Start on port %PORT% with a clean build
echo     .docsbuild.bat 8080            Start on port 8080
echo     .docsbuild.bat --port 8080     Start on port 8080
echo     .docsbuild.bat --no-clean      Reuse the existing docs\_build output
echo     .docsbuild.bat /?              Show this help
echo.
echo   Keys while running:  R rebuild   B browser   L log   C clean   Q quit
echo.
endlocal & exit /b 0
