#!/usr/bin/env bash
set -euo pipefail

# Instala dependências do sistema necessárias para Chromium/Playwright no WSL (Ubuntu/Debian)
# Executa de forma não-interativa e idempotente.

if [ "$(id -u)" -ne 0 ]; then
  echo "Este script precisa de privilégios de administrador (sudo)."
  echo "Execute: sudo ./install_wsl_deps.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -yq
apt-get install -yq \
  ca-certificates \
  curl \
  wget \
  git \
  python3 \
  python3-venv \
  python3-pip \
  libnss3 \
  libxkbcommon0 \
  libgtk-3-0 \
  libxcb1 \
  libxcomposite1 \
  libxrandr2 \
  libxi6 \
  libxtst6 \
  libdrm2 \
  libgbm1 \
  libasound2

# Alguns ambientes 24.04 usam pacotes com sufixo t64; instala se disponível
apt-get install -yq libgtk-3-0t64 libasound2t64 || true

echo "✅ Dependências do sistema instaladas."