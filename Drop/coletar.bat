@echo off
setlocal
cd /d "%~dp0"
echo Coleta WeDrop: login, mapeamento completo e sincronizacao com Supabase.
echo Se a coleta anterior foi interrompida, ela continua de onde parou.
echo.
python -m wedrop coletar %*
if errorlevel 1 (
    echo.
    echo A coleta terminou com erro. Veja a mensagem acima e o log em logs\scraper_runs.log
    pause
    exit /b 1
)
echo.
echo Coleta concluida.
pause
