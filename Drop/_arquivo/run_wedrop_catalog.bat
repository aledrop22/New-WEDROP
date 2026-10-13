@echo off
setlocal
cd /d "%~dp0"
echo WeDrop: login automatico, mapeamento completo e sincronizacao Supabase
python wedrop_monitor_sistema.py
if errorlevel 1 (
    pause
    exit /b 1
)
pause
