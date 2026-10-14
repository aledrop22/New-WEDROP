@echo off
REM 📦 Script de Instalação de Dependências
REM Execute este arquivo para instalar/atualizar todas as dependências

echo.
echo ================================================================
echo   📦 INSTALADOR DE DEPENDÊNCIAS
echo   Seu Armazem Drop - App Streamlit
echo ================================================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Python não encontrado!
    echo Instale Python 3.10+ em: https://www.python.org
    pause
    exit /b 1
)

echo ✅ Python encontrado
python --version
echo.

REM Atualizar pip
echo 📦 Atualizando pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ❌ Erro ao atualizar pip
    pause
    exit /b 1
)
echo ✅ pip atualizado
echo.

REM Instalar dependências
echo 📦 Instalando dependências do requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Erro ao instalar dependências
    pause
    exit /b 1
)
echo ✅ Dependências instaladas
echo.

REM Instalar Playwright
echo 🌐 Instalando Playwright (Chromium)...
python -m playwright install chromium
if errorlevel 1 (
    echo ❌ Erro ao instalar Playwright
    pause
    exit /b 1
)
echo ✅ Playwright instalado
echo.

REM Validação
echo ✅ VALIDAÇÃO FINAL
echo Verificando se tudo está correto...
echo.

python -c "import streamlit; print('✅ Streamlit OK')" 2>nul || echo "❌ Streamlit não funcionou"
python -c "import playwright; print('✅ Playwright OK')" 2>nul || echo "❌ Playwright não funcionou"


echo.
echo ================================================================
echo ✅ INSTALAÇÃO CONCLUÍDA!
echo ================================================================
echo.
echo Próximos passos:
echo 1. Coleta manual: coletar.bat
echo 2. Credenciais: preencha o arquivo .env (veja .env.example)
echo 3. Painel de vendas: painel.bat
echo.
pause
