@echo off
setlocal
cd /d "%~dp0"
echo Iniciando autenticacao, mapeamento WeDrop e sincronizacao com Supabase...
python wedrop_monitor_sistema.py
if errorlevel 1 (
    echo A coleta falhou. Veja a mensagem acima e confira a configuracao.
    pause
    exit /b 1
)
echo Mapeamento concluido.
pause
