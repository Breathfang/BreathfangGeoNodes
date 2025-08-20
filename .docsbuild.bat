@echo off
REM Clean up old builds
rm -r docs/_build

REM run Sphinx to build the documentation
sphinx-build -b html docs docs/_build

REM Open the generated documentation in the default web browser
start docs/_build/index.html

REM Wait 10 seconds to close
timeout /t 10