@echo OFF
echo Iniciando automacao completa do Scraper Meudrop...

REM --- PASSO 1: Garantir que estamos na pasta correta ---
cd /D "%~dp0"
echo Estamos a executar a partir de: %CD%

REM --- PASSO 2: Executar o script de obtenção de cookie ---
echo (1/3) Atualizando o cookie de login...
py obter_cookie.py

IF %ERRORLEVEL% NEQ 0 (
    echo ERRO FATAL: O script 'obter_cookie.py' FALHOU.
    exit /b
)
echo Cookie atualizado com sucesso!

REM --- PASSO 3: Limpar dados antigos (JSON e DB) ---
IF EXIST data.json (
    echo Limpando data.json antigo...
    del data.json
)
IF EXIST transformacao\meudrop_data.db (
    echo Limpando meudrop_data.db antigo...
    del transformacao\meudrop_data.db
)

REM --- PASSO 4: Executar o Scraper (Scrapy) ---
echo (2/3) Executando o Scraper (meudrop)...
echo (Salvando progresso em data.json em tempo real...)

REM --- CORREÇÃO CONTRA CRASH/CONGELAMENTO (Funciona no Python 3.12) ---
set ASYNCIO_EVENT_LOOP=asyncio.SelectorEventLoop
REM Usamos -o (minúsculo) para salvar em tempo real (sua sugestão)
cmd /c "py -m scrapy crawl meudrop -o data.json"

REM (Pequena pausa para garantir que o Windows libere o arquivo)
timeout /t 2 /nobreak > NUL

IF NOT EXIST data.json (
    echo AVISO: O ficheiro data.json nao foi criado. O Scrapy falhou ou nao encontrou itens.
    goto :fim
)
echo Scraper finalizado.

REM --- PASSO 5: Executar a exportação para o Dashboard ---
echo (3/3) Exportando dados para SQL e Google Sheets...
cd transformacao

REM --- CORREÇÃO (ETAPA 3) ---
cmd /c "py data_export.py"
cd ..

:fim
echo Automacao concluida!