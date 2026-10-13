@echo off
setlocal
cd /d "%~dp0"
echo Iniciando coleta protegida com backup, validacao e retentativa automatica...
echo.
python wedrop_protected_runner.py
if errorlevel 1 (
    echo.
    echo A coleta falhou apos todas as tentativas.
    echo Dados foram restaurados do backup automaticamente.
    echo Veja o log acima para detalhes.
    pause
    exit /b 1
)
echo.
echo Coleta concluida com sucesso!
pause
