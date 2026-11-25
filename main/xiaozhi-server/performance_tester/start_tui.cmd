@echo off
rem device-simulator-tui launcher - double click; q to quit; errors go to tui_error_*.log
cd /d "%~dp0"
python -X utf8 device_simulator_tui.py %*
pause
