#!/usr/bin/env bash
set -euo pipefail

# Verifica se os pacotes do sistema estão instalados (sem tentar instalar)
echo "Verificando dependências do sistema..."
if ! dpkg -l | grep -q "libgtk-3-0\|libgtk-3-0t64"; then
    echo "⚠️  AVISO: Bibliotecas do sistema para Playwright/Chromium podem estar faltando."
    # Tenta instalar automaticamente sem prompts:
    if [ "$(id -u)" -eq 0 ]; then
        ./install_wsl_deps.sh || true
    else
        if command -v sudo >/dev/null 2>&1; then
            sudo -n ./install_wsl_deps.sh || true
        fi
    fi
    echo "Continuando..."
fi

# Cria/renova ambiente virtual
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt

# Instala o navegador Chromium do Playwright
python -m playwright install chromium

# Executa o spider (JSON Lines para escrita incremental)
python -m scrapy crawl wedrop -O data.json:jsonlines

echo "✅ Scraper executado! Arquivo gerado em: $(pwd)/data.json"
