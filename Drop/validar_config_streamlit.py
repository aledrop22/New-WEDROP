#!/usr/bin/env python3
"""
✅ Script de Validação - Verifica se tudo está configurado corretamente
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def verificar_python():
    """Verifica versão do Python"""
    print("🐍 Verificando Python...")
    versao = sys.version_info
    print(f"   Python {versao.major}.{versao.minor}.{versao.micro}")
    
    if versao.major >= 3 and versao.minor >= 10:
        print("   ✅ Versão OK")
        return True
    else:
        print("   ❌ Python 3.10+ requerido")
        return False


def verificar_dependencias():
    """Verifica se as dependências estão instaladas"""
    print("\n📦 Verificando dependências...")
    
    dependencias = [
        'streamlit',
        'playwright',
        'pandas',
        'scrapy',
        'requests'
    ]
    
    todas_ok = True
    for dep in dependencias:
        try:
            __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} - NÃO INSTALADO")
            todas_ok = False
    
    return todas_ok


def verificar_playwright():
    """Verifica se Chromium foi instalado"""
    print("\n🌐 Verificando Playwright/Chromium...")
    
    try:
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                p.chromium
            print("   ✅ Chromium instalado")
            return True
        except:
            print("   ❌ Chromium NÃO instalado")
            print("   Execute: python -m playwright install chromium")
            return False
    except:
        print("   ❌ Playwright não encontrado")
        return False


def verificar_autenticacao():
    """Verifica se o arquivo de autenticação existe"""
    print("\n🔐 Verificando autenticação...")
    
    if os.path.exists('storage_state.json'):
        try:
            with open('storage_state.json', 'r') as f:
                data = json.load(f)
            print("   ✅ storage_state.json encontrado")
            return True
        except:
            print("   ❌ storage_state.json corrompido")
            return False
    else:
        print("   ⚠️  storage_state.json NÃO encontrado")
        print("   Execute: python obter_cookie_novo_site.py")
        return False


def verificar_arquivos():
    """Verifica se os arquivos principais existem"""
    print("\n📁 Verificando arquivos...")
    
    arquivos = [
        'app_streamlit.py',
        'obter_cookie_novo_site.py',
        'requirements.txt'
    ]
    
    todas_ok = True
    for arq in arquivos:
        if os.path.exists(arq):
            print(f"   ✅ {arq}")
        else:
            print(f"   ❌ {arq} - NÃO ENCONTRADO")
            todas_ok = False
    
    return todas_ok


def main():
    """Função principal"""
    print("=" * 60)
    print("✅ VALIDADOR DE CONFIGURAÇÃO")
    print("   Seu Armazém Drop - App Streamlit")
    print("=" * 60)
    print()
    
    resultados = {
        'Python': verificar_python(),
        'Dependências': verificar_dependencias(),
        'Playwright': verificar_playwright(),
        'Autenticação': verificar_autenticacao(),
        'Arquivos': verificar_arquivos()
    }
    
    print("\n" + "=" * 60)
    print("📊 RESUMO")
    print("=" * 60)
    
    for chave, resultado in resultados.items():
        status = "✅" if resultado else "❌"
        print(f"{status} {chave}")
    
    tudo_ok = all(resultados.values())
    
    print("\n" + "=" * 60)
    
    if tudo_ok:
        print("✅ TUDO PRONTO!")
        print("\nVocê pode iniciar o Streamlit:")
        print("  streamlit run app_streamlit.py")
        print("\nOu use o script:")
        print("  start_streamlit.bat")
    else:
        print("❌ PROBLEMAS ENCONTRADOS")
        print("\nResolva os itens com ❌ acima.")
        print("\nPasso a passo:")
        print("  1. Instale dependências: pip install -r requirements.txt")
        print("  2. Instale Playwright: python -m playwright install chromium")
        print("  3. Autentique: python obter_cookie_novo_site.py")
        print("  4. Execute novamente: python validar_config.py")
    
    print("=" * 60)
    
    return 0 if tudo_ok else 1


if __name__ == "__main__":
    sys.exit(main())
