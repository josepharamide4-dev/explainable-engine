@echo off
echo Running full verification...

py -m pytest
if %errorlevel% neq 0 exit /b %errorlevel%

py scripts\release_check.py
if %errorlevel% neq 0 exit /b %errorlevel%

py main.py doctor --strict
if %errorlevel% neq 0 exit /b %errorlevel%

py main.py check . --baseline .explainable-baseline.json

echo.
echo All verification steps passed.
pause