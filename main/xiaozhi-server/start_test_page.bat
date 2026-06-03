@echo off
echo Starting test page server...
cd /d d:\code\xiaozhi-esp32-server\main\xiaozhi-server\test

"D:\software\Miniconda3\envs\xiaozhi-env\python.exe" -m http.server 8006

echo Test page is at: http://localhost:8006/test_page.html
pause
