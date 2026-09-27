@echo off
chcp 65001 >nul
rem signal day kline viewer: cd to project root for python -m
cd /d "%~dp0..\..\.."
echo http://127.0.0.1:5004/
python -m app.kline_view.signal_day_k.web
pause
