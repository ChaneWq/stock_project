@echo off
chcp 65001 >nul
rem demo version of kline_view: cd to project root for python -m
cd /d "%~dp0..\..\.."
echo http://127.0.0.1:5003/
python -m app.kline_view.demo_day_k.web
pause
