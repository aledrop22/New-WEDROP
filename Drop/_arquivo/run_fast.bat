@echo off
setlocal
cd /d "%~dp0"
echo Iniciando coleta rapida do WeDrop...
echo.
python wedrop_monitor_sistema.py
if errorlevel 1 (
    echo.
    echo A coleta falhou. Veja a mensagem acima.
    pause
    exit /b 1
)
echo.
echo Coleta concluida!
pause
