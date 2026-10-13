@echo off
REM Script para iniciar o WSL e manter o cron rodando em segundo plano

echo Iniciando WSL e servico cron...
wsl -d Ubuntu -u alexandre -- bash -c "sudo service cron start && echo 'Cron iniciado com sucesso!' && tail -f /dev/null"

REM O tail -f /dev/null mantém o WSL rodando
