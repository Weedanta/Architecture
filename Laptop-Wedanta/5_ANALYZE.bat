@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
%PY% analysis\analyze.py
start "" results\summary.md
pause
