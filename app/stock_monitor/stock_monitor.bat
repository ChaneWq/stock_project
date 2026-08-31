@echo off
chcp 65001 >nul
rem 脚本位于 app/stock_monitor/，需切到项目根目录以支持 python -m 启动
cd /d "%~dp0..\.."
echo 启动个股监控服务: http://127.0.0.1:5000/
python -m app.stock_monitor.server
pause
