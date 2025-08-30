@echo off
REM Clean up old builds
IF EXIST "./docs/_build" (
    echo Removing _build...
    rmdir /s /q "./docs/_build"
) ELSE (
    echo Folder ./docs/_build not found.
)

REM Check if sphinx-autobuild.exe is running
tasklist /Fi "IMAGENAME eq sphinx-autobuild.exe" 2>NUL | find /I "sphinx-autobuild.exe" >NUL
IF %ERRORLEVEL%==0 (
    echo Killing Sphinx host at 127.0.0.1:8000.
    taskkill /F /IM "sphinx-autobuild.exe"
)

REM run Sphinx to build the documentation
sphinx-autobuild docs/ docs/_build/html

REM Launch default browser and open 127.0.0.1:8000
start "" http://127.0.0.1:8000/