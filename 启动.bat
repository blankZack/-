@echo off
chcp 65001 >nul
echo 正在启动视频帧提取工具...
echo 浏览器访问 http://127.0.0.1:5000
echo.
start http://127.0.0.1:5000
python app.py
pause
