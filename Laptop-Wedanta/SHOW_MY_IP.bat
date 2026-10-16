@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
%PY% -c "from common import config; print('This laptop IP:', config.local_ip())"
ipconfig | findstr /i "IPv4"
pause
