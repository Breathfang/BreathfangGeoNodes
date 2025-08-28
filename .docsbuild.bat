@echo off
REM Clean up old builds
REM rm -r docs/_build

REM run Sphinx to build the documentation
sphinx-autobuild docs/ docs/_build/html

REM Open the generated documentation in the default web browser
start docs/_build/index.html

REM Launch google chrome and open 127.0.0.1:8000
start "" "chrome.exe" http://127.0.0.1:8000/

REM Wait 20 seconds to close
timeout /t 20