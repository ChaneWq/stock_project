@echo off
rem feature_import: interactive params (board / date), then run
cd /d "%~dp0..\..\.."

set ARGS=
set BOARD=
set START=
set END=

set /p BOARD=Main board only (SH/SZ)? [Y/N] (Enter=N all): 
if /i "%BOARD%"=="Y" set ARGS=%ARGS% --board main

set /p START=Start date YYYY-MM-DD (Enter=default window): 
if not "%START%"=="" set ARGS=%ARGS% --start %START%

set /p END=End date YYYY-MM-DD (Enter=today): 
if not "%END%"=="" set ARGS=%ARGS% --end %END%

echo Run: python -m app.database.feature_import.main%ARGS%
python -m app.database.feature_import.main%ARGS%
pause
