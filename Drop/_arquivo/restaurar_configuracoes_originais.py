#!/usr/bin/env python3
"""
Script para restaurar as configurações originais do Scrapy
caso as otimizações causem problemas.

Uso: python restaurar_configuracoes_originais.py
"""

import os
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = PROJECT_DIR / "Site" / "settings.py"
WEDROP_SPIDER = PROJECT_DIR / "Site" / "spiders" / "wedrop.py"
WEDROP_CATALOG_SPIDER = PROJECT_DIR / "Site" / "spiders" / "wedrop_catalog.py"

BACKUP_DIR = PROJECT_DIR / "backups_scrapy"
BACKUP_DIR.mkdir(exist_ok=True)

def backup_current_files():
    """Faz backup dos arquivos atuais antes de restaurar"""
    timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"📦 Fazendo backup dos arquivos atuais...")
    for file_path in [SETTINGS_FILE, WEDROP_SPIDER, WEDROP_CATALOG_SPIDER]:
        if file_path.exists():
            backup_path = BACKUP_DIR / f"{file_path.name}_{timestamp}"
            shutil.copy2(file_path, backup_path)
            print(f"   ✅ Backup criado: {backup_path}")

def restore_settings():
    """Restaura configurações originais no settings.py"""
    print(f"\n🔧 Restaurando settings.py...")

    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Substituições
    replacements = [
        ("CONCURRENT_REQUESTS_PER_DOMAIN = 32", "CONCURRENT_REQUESTS_PER_DOMAIN = 16"),
        ("CONCURRENT_REQUESTS = 32", "CONCURRENT_REQUESTS = 16"),
        ("DOWNLOAD_DELAY = 0", "DOWNLOAD_DELAY = 0.1"),
        ("DOWNLOAD_TIMEOUT = 60", "DOWNLOAD_TIMEOUT = 120"),
        ("PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000", "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 45_000"),
        ("PLAYWRIGHT_BROWSER_LAUNCH_TIMEOUT = 30_000", "PLAYWRIGHT_BROWSER_LAUNCH_TIMEOUT = 60_000"),
        ("PLAYWRIGHT_MAX_CONTEXTS = 8", "PLAYWRIGHT_MAX_CONTEXTS = 2"),
        ("PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 8", "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 3"),
    ]

    for old, new in replacements:
        content = content.replace(old, new)

    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"   ✅ settings.py restaurado")

def restore_wedrop_spider():
    """Restaura configurações originais no wedrop.py"""
    print(f"\n🔧 Restaurando wedrop.py...")

    with open(WEDROP_SPIDER, 'r', encoding='utf-8') as f:
        content = f.read()

    # Substituições
    replacements = [
        ('PageMethod("wait_for_selector", "ul.products", timeout=8000)', 'PageMethod("wait_for_selector", "ul.products", timeout=15000)'),
        ('await page.wait_for_selector("ul.products li.product", timeout=8000)', 'await page.wait_for_selector("ul.products li.product", timeout=15000)'),
        ('await page.wait_for_selector("div.tag-vendas-produto", timeout=1000)', 'await page.wait_for_selector("div.tag-vendas-produto", timeout=2000)'),
        ('timeout=15000', 'timeout=25000', 1),  # Primeira ocorrência apenas
        ('timeout=30000', 'timeout=45000', 1),  # Primeira ocorrência apenas
        ('timeout=5000', 'timeout=10000'),
    ]

    for old, new in replacements:
        if len(replacements) == 2 and isinstance(replacements[1], int):
            continue  # Pula o contador
        content = content.replace(old, new)

    # Restaura o wait_for_timeout removido
    content = content.replace(
        'await page.evaluate("() => { const button = document.querySelector(\'button#webbex-arp-entendido\'); if (button) { button.click(); } }")',
        'await page.evaluate("() => { const button = document.querySelector(\'button#webbex-arp-entendido\'); if (button) { button.click(); } }")\n                await page.wait_for_timeout(300)'
    )

    with open(WEDROP_SPIDER, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"   ✅ wedrop.py restaurado")

def restore_wedrop_catalog_spider():
    """Restaura configurações originais no wedrop_catalog.py"""
    print(f"\n🔧 Restaurando wedrop_catalog.py...")

    with open(WEDROP_CATALOG_SPIDER, 'r', encoding='utf-8') as f:
        content = f.read()

    # Substituições
    replacements = [
        ('timeout=30000', 'timeout=45000'),
        ('timeout=8000', 'timeout=15000'),
    ]

    for old, new in replacements:
        content = content.replace(old, new)

    with open(WEDROP_CATALOG_SPIDER, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"   ✅ wedrop_catalog.py restaurado")

def main():
    print("="*60)
    print("RESTAURAR CONFIGURAÇÕES ORIGINAIS DO SCRAPY")
    print("="*60)

    # Verifica se os arquivos existem
    missing_files = []
    for file_path in [SETTINGS_FILE, WEDROP_SPIDER, WEDROP_CATALOG_SPIDER]:
        if not file_path.exists():
            missing_files.append(str(file_path))

    if missing_files:
        print(f"\n❌ ERRO: Arquivos não encontrados:")
        for f in missing_files:
            print(f"   - {f}")
        return

    # Confirmação
    print(f"\n⚠️  Este script vai restaurar as configurações ORIGINAIS do Scrapy.")
    print(f"   Isso DESFARÁ as otimizações de performance aplicadas.")
    print(f"\nArquivos que serão modificados:")
    print(f"   - {SETTINGS_FILE}")
    print(f"   - {WEDROP_SPIDER}")
    print(f"   - {WEDROP_CATALOG_SPIDER}")

    response = input("\nDeseja continuar? (s/n): ").lower().strip()
    if response != 's':
        print("❌ Operação cancelada.")
        return

    # Backup
    backup_current_files()

    # Restauração
    restore_settings()
    restore_wedrop_spider()
    restore_wedrop_catalog_spider()

    print("\n" + "="*60)
    print("✅ CONFIGURAÇÕES ORIGINAIS RESTAURADAS COM SUCESSO!")
    print("="*60)
    print(f"\n📁 Backups salvos em: {BACKUP_DIR}")
    print(f"\n🔄 Para aplicar as mudanças, faça commit e push:")
    print(f"   git add Site/settings.py Site/spiders/wedrop.py Site/spiders/wedrop_catalog.py")
    print(f"   git commit -m 'Restaura configurações originais do Scrapy'")
    print(f"   git push origin main")

if __name__ == "__main__":
    main()
