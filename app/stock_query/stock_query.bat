@echo off
chcp 65001 >nul
rem stock_query: cd to project root for python -m
cd /d "%~dp0..\.."
echo http://127.0.0.1:5002/
python -m app.stock_query.web
pause
