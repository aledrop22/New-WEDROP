@echo off
REM Script para testar o scraper com as novas configurações
REM Será limitado a 3 páginas para validar as correções

echo ========================================
echo Iniciando teste do scraper (3 páginas)
echo ========================================
echo.

cd /d "%~dp0"

REM Executar scrapy com limite de páginas
python -m scrapy crawl wedrop -a limit=3 --loglevel=INFO

echo.
echo ========================================
echo Teste concluído!
echo Verifique os arquivos de saída em:
echo - data.json (itens extraídos)
echo ========================================
pause
