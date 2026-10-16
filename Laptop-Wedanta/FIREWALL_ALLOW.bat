@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
REM Right-click > Run as administrator
netsh advfirewall firewall add rule name="SISTER Lab REST 5151" dir=in action=allow protocol=TCP localport=5151 profile=private,public
netsh advfirewall firewall add rule name="SISTER Lab MQTT 1883" dir=in action=allow protocol=TCP localport=1883 profile=private,public
echo Done. Remove these rules after the lab with FIREWALL_REMOVE.bat
pause
