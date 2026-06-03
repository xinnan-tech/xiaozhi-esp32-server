@echo off
echo Starting xiaozhi-server...
cd /d d:\code\xiaozhi-esp32-server\main\xiaozhi-server

set PATH=D:\software\Miniconda3\envs\xiaozhi-env\Library\bin;%PATH%
set PYTHONPATH=d:\code\xiaozhi-esp32-server\main\xiaozhi-server;%PYTHONPATH%

echo Starting test page server on port 8006...
start "Test Page Server" cmd /k "cd /d d:\code\xiaozhi-esp32-server\main\xiaozhi-server\test && D:\software\Miniconda3\envs\xiaozhi-env\python.exe -m http.server 8006"

echo Starting main server...
echo WebSocket: ws://localhost:8000/xiaozhi/v1/
echo HTTP API: http://localhost:8002/
echo Test Page: http://localhost:8006/test_page.html
echo.

"D:\software\Miniconda3\envs\xiaozhi-env\python.exe" app.py

pause
