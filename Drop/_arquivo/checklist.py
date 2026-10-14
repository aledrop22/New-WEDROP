#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                   CHECKLIST DE EXECUÇÃO DO SCRAPER                      ║
║                       (Execute este arquivo primeiro)                    ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    print("\n" + "="*70)
    print("  🚀 CHECKLIST DE EXECUÇÃO - SCRAPER WEDROP BRASIL")
    print("="*70 + "\n")

def check_file(filename, description):
    """Verifica se arquivo existe"""
    path = Path(filename)
    if path.exists():
        print(f"{Colors.GREEN}✅{Colors.RESET} {description}")
        return True
    else:
        print(f"{Colors.RED}❌{Colors.RESET} {description}")
        print(f"   {Colors.YELLOW}→ Arquivo não encontrado: {filename}{Colors.RESET}")
        return False

def check_python():
    """Verifica versão do Python"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"{Colors.GREEN}✅{Colors.RESET} Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"{Colors.RED}❌{Colors.RESET} Python {version.major}.{version.minor} (requer 3.10+)")
        return False

def check_dependencies():
    """Verifica dependências principais"""
    deps = ['scrapy', 'scrapy_playwright', 'parsel', 'itemloaders']
    all_ok = True
    
    for dep in deps:
        try:
            __import__(dep)
            print(f"{Colors.GREEN}✅{Colors.RESET} {dep}")
        except ImportError:
            print(f"{Colors.RED}❌{Colors.RESET} {dep} (não instalado)")
            all_ok = False
    
    return all_ok

def check_storage_state():
    """Verifica cookie/storage state"""
    path = Path("storage_state.json")
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            if data and isinstance(data, dict):
                print(f"{Colors.GREEN}✅{Colors.RESET} storage_state.json (válido)")
                return True
        except:
            pass
    
    print(f"{Colors.RED}❌{Colors.RESET} storage_state.json (não encontrado ou inválido)")
    print(f"   {Colors.YELLOW}→ Execute: python obter_cookie.py{Colors.RESET}")
    return False

def check_settings():
    """Verifica se settings foram modificados"""
    settings_file = Path("Site/settings.py")
    
    if not settings_file.exists():
        print(f"{Colors.RED}❌{Colors.RESET} Site/settings.py não encontrado")
        return False
    
    content = settings_file.read_text()
    
    critical_checks = {
        "CONCURRENT_REQUESTS = 2": "Concorrência reduzida",
        "CONCURRENT_REQUESTS_PER_DOMAIN = 1": "Concorrência por domínio reduzida",
        "DOWNLOAD_DELAY = 1.5": "Delay aumentado",
        "DOWNLOAD_TIMEOUT = 120": "Timeout global aumentado",
        "PLAYWRIGHT_MAX_CONTEXTS = 2": "Max contexts reduzido",
    }
    
    failed = []
    for check, desc in critical_checks.items():
        if check not in content:
            failed.append(f"{desc} (procure: {check})")
    
    if not failed:
        print(f"{Colors.GREEN}✅{Colors.RESET} Site/settings.py (modificado corretamente)")
        return True
    else:
        print(f"{Colors.RED}❌{Colors.RESET} Site/settings.py (configuração incompleta)")
        for f in failed:
            print(f"   {Colors.YELLOW}→ {f}{Colors.RESET}")
        return False

def check_spider():
    """Verifica se spider foi modificado"""
    spider_file = Path("Site/spiders/wedrop.py")

    if not spider_file.exists():
        print(f"{Colors.RED}❌{Colors.RESET} wedrop.py não encontrado")
        return False

    content = spider_file.read_text()

    if "await page.close()" in content:
        count = content.count("await page.close()")
        print(f"{Colors.GREEN}✅{Colors.RESET} wedrop.py (limpeza de memória implementada: {count} closes)")
        return True
    else:
        print(f"{Colors.RED}❌{Colors.RESET} wedrop.py (limpeza de memória não implementada)")
        return False

def check_data_json():
    """Verifica arquivo de saída"""
    path = Path("data.json")
    
    if not path.exists():
        print(f"{Colors.YELLOW}⚠️{Colors.RESET}  data.json (não existe ainda - executar scraper)")
        return None
    
    try:
        with open(path) as f:
            lines = [l for l in f.readlines() if l.strip()]
        
        count = len(lines)
        if count > 0:
            print(f"{Colors.GREEN}✅{Colors.RESET} data.json ({count} items)")
            return True
        else:
            print(f"{Colors.YELLOW}⚠️{Colors.RESET}  data.json (vazio - executar scraper)")
            return None
    except:
        print(f"{Colors.RED}❌{Colors.RESET} data.json (erro ao ler)")
        return False

def print_next_steps(checks_passed):
    """Mostra próximos passos"""
    print("\n" + "="*70)
    print("  📋 PRÓXIMOS PASSOS")
    print("="*70 + "\n")
    
    if checks_passed == 0:
        print(f"{Colors.RED}❌ Alguns requisitos estão faltando!{Colors.RESET}\n")
        print("1. Instale as dependências:")
        print("   pip install -r requirements.txt\n")
        print("2. Gere o arquivo de cookie:")
        print("   python obter_cookie.py\n")
        print("3. Execute novamente este checklist:")
        print("   python checklist.py\n")
        return False
    
    elif checks_passed <= 4:
        print(f"{Colors.YELLOW}⚠️  Algumas correções podem estar faltando{Colors.RESET}\n")
        print("Verifique os arquivos modificados:")
        print("  • Site/settings.py")
        print("  • Site/spiders/wedrop.py\n")
        return False

    else:
        print(f"{Colors.GREEN}✅ TUDO PRONTO!{Colors.RESET}\n")
        print("Teste com 3 páginas:")
        print(f"   {Colors.BOLD}python -m scrapy crawl wedrop{Colors.RESET}\n")
        print("Monitorar progresso:")
        print(f"   {Colors.BOLD}tail -f data.json | head -20{Colors.RESET}\n")
        print("Quando terminar, remova a linha:")
        print("   CLOSESPIDER_PAGECOUNT = 3")
        print("E execute novamente para raspagem completa.\n")
        return True

def main():
    print_header()
    
    checks = []
    
    print(f"{Colors.BOLD}🔍 VERIFICAÇÕES PRELIMINARES{Colors.RESET}\n")
    checks.append(check_python())
    
    print(f"\n{Colors.BOLD}📦 DEPENDÊNCIAS{Colors.RESET}\n")
    checks.append(check_dependencies())
    
    print(f"\n{Colors.BOLD}🔐 AUTENTICAÇÃO{Colors.RESET}\n")
    checks.append(check_storage_state())
    
    print(f"\n{Colors.BOLD}⚙️  CONFIGURAÇÕES{Colors.RESET}\n")
    checks.append(check_settings())
    
    print(f"\n{Colors.BOLD}🐍 SPIDER{Colors.RESET}\n")
    checks.append(check_spider())
    
    print(f"\n{Colors.BOLD}📊 DADOS{Colors.RESET}\n")
    data_result = check_data_json()
    
    checks_passed = sum(1 for c in checks if c is True)
    
    if not print_next_steps(checks_passed):
        print(f"\n{Colors.RED}Corrija os problemas acima e execute novamente.{Colors.RESET}\n")
        return 1
    
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Cancelado pelo usuário.{Colors.RESET}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Erro: {e}{Colors.RESET}\n")
        sys.exit(1)
