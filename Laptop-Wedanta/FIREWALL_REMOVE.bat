@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
REM Right-click > Run as administrator
netsh advfirewall firewall delete rule name="SISTER Lab REST 5151"
netsh advfirewall firewall delete rule name="SISTER Lab MQTT 1883"
pause
