#!/usr/bin/env bash
# Script para configurar sudo sem senha para comandos específicos

echo "Configurando sudo sem senha para comandos do scraper..."

# Cria arquivo de configuração sudoers
SUDOERS_FILE="/etc/sudoers.d/scraper-nopasswd"

# Adiciona regras (precisa rodar com sudo uma vez)
sudo tee "$SUDOERS_FILE" > /dev/null << 'EOF'
# Permite comandos do scraper sem senha
alexandre ALL=(ALL) NOPASSWD: /usr/bin/apt update
alexandre ALL=(ALL) NOPASSWD: /usr/bin/apt install
alexandre ALL=(ALL) NOPASSWD: /usr/sbin/service cron start
alexandre ALL=(ALL) NOPASSWD: /usr/sbin/service cron restart
alexandre ALL=(ALL) NOPASSWD: /usr/sbin/service cron status
EOF

# Define permissões corretas
sudo chmod 0440 "$SUDOERS_FILE"

echo "✅ Configuração concluída!"
echo "Agora os scripts não pedirão senha para:"
echo "  - apt update/install"
echo "  - service cron"
