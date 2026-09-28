@echo off
chcp 65001 >nul
rem train mode day kline viewer: cd to project root for python -m
cd /d "%~dp0..\..\.."
echo http://127.0.0.1:5005/
python -m app.kline_view.train_mode_day_k.web
pause
