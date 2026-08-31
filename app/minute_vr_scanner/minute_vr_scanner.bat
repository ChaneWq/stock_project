@echo off
chcp 65001 >nul
rem 脚本位于 app/minute_vr_scanner/，需切到项目根目录以支持 python -m 启动
cd /d "%~dp0..\.."
echo 启动量比策略扫描服务: http://127.0.0.1:5001/
python -m app.minute_vr_scanner.web
pause
