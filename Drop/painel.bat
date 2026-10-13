@echo off
setlocal
cd /d "%~dp0"
echo Iniciando painel de vendas e estoque WeDrop...
python -m streamlit run app_monitoramento_vendas.py
if errorlevel 1 pause
