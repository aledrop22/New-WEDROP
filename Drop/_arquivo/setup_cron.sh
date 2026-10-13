#!/usr/bin/env bash
# Script para configurar o cron job para executar o scraper às 1h da manhã

# Define o caminho completo do script
SCRIPT_PATH="/mnt/c/Users/xandy/OneDrive/Documentos/GitHub/Scrapy-Drop-Brasil/Drop/setup_and_run.sh"

# Remove entradas antigas do cron para este script (se existirem)
crontab -l 2>/dev/null | grep -v "setup_and_run.sh" | crontab -

# Adiciona nova entrada do cron
# Formato: minuto hora dia mês dia_da_semana comando
# 0 1 * * * = todo dia às 1:00 AM
(crontab -l 2>/dev/null; echo "0 1 * * * cd $(dirname $SCRIPT_PATH) && bash $SCRIPT_PATH >> /mnt/c/Users/xandy/OneDrive/Documentos/GitHub/Scrapy-Drop-Brasil/Drop/scraper_cron.log 2>&1") | crontab -

echo "✅ Cron job configurado!"
echo "📅 O scraper rodará automaticamente todos os dias às 1:00 da manhã"
echo ""
echo "Para verificar se foi configurado corretamente:"
echo "  crontab -l"
echo ""
echo "Para ver os logs de execução:"
echo "  tail -f /mnt/c/Users/xandy/OneDrive/Documentos/GitHub/Scrapy-Drop-Brasil/Drop/scraper_cron.log"
echo ""
echo "Para remover o agendamento:"
echo "  crontab -r"
