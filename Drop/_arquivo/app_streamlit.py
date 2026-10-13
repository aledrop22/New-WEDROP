#!/usr/bin/env python3
"""
🎯 App Streamlit para Scraping - Seu Armazém Drop
Scraping do novo site: https://app.seuarmazemdrop.com.br/dashboard/catalog
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from playwright.async_api import async_playwright

# ==================== CONFIGURAÇÕES ====================
SITE_HOST = "app.seuarmazemdrop.com.br"
BASE_URL = "https://app.seuarmazemdrop.com.br/dashboard/catalog"
STORAGE_STATE_FILE = "storage_state.json"
OUTPUT_JSON = "dados_catalogo.json"

# Workaround para Windows asyncio
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

# ==================== CONFIGURAÇÃO STREAMLIT ====================
st.set_page_config(
    page_title="Scraper - Seu Armazém Drop",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== FUNÇÕES DE SCRAPING ====================

async def verificar_autenticacao() -> bool:
    """Verifica se o arquivo storage_state.json existe"""
    if not os.path.exists(STORAGE_STATE_FILE):
        return False
    return True


async def fazer_scraping(max_paginas: int = 5) -> list:
    """
    Faz o scraping do site usando Playwright
    
    Args:
        max_paginas: Número máximo de páginas a coletar
    
    Returns:
        Lista de produtos encontrados
    """
    produtos = []
    pagina_atual = 1

    if not await verificar_autenticacao():
        raise FileNotFoundError(
            f"Arquivo '{STORAGE_STATE_FILE}' não encontrado. "
            "Execute 'obter_cookie.py' primeiro!"
        )

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                storage_state=STORAGE_STATE_FILE
            )
            page = await context.new_page()

            while pagina_atual <= max_paginas:
                url = f"{BASE_URL}?per_page=100&page={pagina_atual}"
                st.write(f"📄 Acessando página {pagina_atual}: {url}")

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Aguardar carregamento da tabela de produtos
                    try:
                        await page.wait_for_selector(
                            "table tbody tr, div.product-item, .product-row",
                            timeout=10000
                        )
                    except Exception as e:
                        st.warning(f"⚠️ Seletor de produtos não encontrado: {e}")

                    # Extrair HTML da página
                    page_content = await page.content()

                    # Extrair dados usando JavaScript (mais confiável)
                    produtos_pagina = await page.evaluate("""
                        () => {
                            // Tentar diferentes seletores de tabela
                            const rows = Array.from(
                                document.querySelectorAll('table tbody tr') ||
                                document.querySelectorAll('.product-row') ||
                                document.querySelectorAll('[role="row"]')
                            );
                            
                            return rows.map(row => {
                                const cells = Array.from(row.querySelectorAll('td'));
                                return {
                                    id: cells[0]?.textContent?.trim() || '',
                                    nome: cells[1]?.textContent?.trim() || '',
                                    preco: cells[2]?.textContent?.trim() || '',
                                    estoque: cells[3]?.textContent?.trim() || '',
                                    categoria: cells[4]?.textContent?.trim() || '',
                                    status: cells[5]?.textContent?.trim() || '',
                                    data_scrapy: new Date().toISOString()
                                };
                            }).filter(p => p.id || p.nome);
                        }
                    """)

                    if not produtos_pagina:
                        st.info("ℹ️ Nenhum produto encontrado nesta página. Finalizando.")
                        break

                    produtos.extend(produtos_pagina)
                    st.success(f"✅ Página {pagina_atual}: {len(produtos_pagina)} produtos coletados")

                    # Verificar se há próxima página
                    tem_proxima = await page.evaluate("""
                        () => {
                            const botao_proximo = document.querySelector('a[aria-label="Next"]') ||
                                                 document.querySelector('button:has-text("Próxima")') ||
                                                 document.querySelector('.pagination .next');
                            return botao_proximo !== null && !botao_proximo.disabled;
                        }
                    """)

                    if not tem_proxima:
                        st.info("✋ Última página atingida.")
                        break

                    pagina_atual += 1

                except Exception as e:
                    st.error(f"❌ Erro ao processar página {pagina_atual}: {e}")
                    break

            await context.close()
            await browser.close()

        except Exception as e:
            st.error(f"❌ Erro ao iniciar o navegador: {e}")
            raise

    return produtos


def salvar_dados(produtos: list) -> str:
    """Salva os dados em arquivo JSON"""
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_produtos": len(produtos),
        "produtos": produtos
    }
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    return OUTPUT_JSON


# ==================== INTERFACE STREAMLIT ====================

def main():
    st.title("🎯 Scraper - Seu Armazém Drop")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        max_paginas = st.slider(
            "Número máximo de páginas:",
            min_value=1,
            max_value=50,
            value=5,
            step=1
        )

        st.markdown("---")
        st.subheader("📋 Status")

        # Verificar autenticação
        if asyncio.run(verificar_autenticacao()):
            st.success("✅ Autenticação OK (storage_state.json encontrado)")
        else:
            st.error(
                "❌ Arquivo não encontrado!\n\n"
                "Execute primeiro:\n```\npython obter_cookie.py\n```"
            )

    # Coluna principal
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("🚀 Iniciar Scraping")
        if st.button("Começar Coleta de Dados", type="primary", use_container_width=True):
            if not asyncio.run(verificar_autenticacao()):
                st.error("❌ Arquivo storage_state.json não encontrado!")
                st.stop()

            st.info("⏳ Iniciando scraping... Isso pode levar alguns minutos.")

            progress_bar = st.progress(0)
            status_placeholder = st.empty()

            try:
                produtos = asyncio.run(fazer_scraping(max_paginas))

                if produtos:
                    # Salvar dados
                    arquivo = salvar_dados(produtos)
                    st.success(f"✅ Scraping concluído! {len(produtos)} produtos coletados.")
                    st.info(f"📁 Dados salvos em: `{arquivo}`")

                    # Exibir preview
                    st.subheader("📊 Preview dos Dados")
                    df = pd.DataFrame(produtos)
                    st.dataframe(df, use_container_width=True)

                    # Opções de download
                    col_csv, col_json = st.columns(2)
                    with col_csv:
                        st.download_button(
                            label="📥 Download CSV",
                            data=df.to_csv(index=False),
                            file_name=f"produtos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    with col_json:
                        st.download_button(
                            label="📥 Download JSON",
                            data=json.dumps(produtos, ensure_ascii=False, indent=2),
                            file_name=f"produtos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )

                    # Estatísticas
                    st.subheader("📈 Estatísticas")
                    cols = st.columns(4)
                    with cols[0]:
                        st.metric("Total de Produtos", len(produtos))
                    with cols[1]:
                        produtos_com_estoque = len([p for p in produtos if p.get('estoque', '0') != '0'])
                        st.metric("Em Estoque", produtos_com_estoque)
                    with cols[2]:
                        st.metric("Sem Estoque", len(produtos) - produtos_com_estoque)
                    with cols[3]:
                        st.metric("Tempo Coleta", f"{len(produtos) * 0.5:.0f}s")

                else:
                    st.warning("⚠️ Nenhum produto encontrado.")

            except Exception as e:
                st.error(f"❌ Erro durante o scraping: {e}")

    with col2:
        st.subheader("ℹ️ Ajuda")
        st.markdown("""
        **Passos:**
        1. Execute `obter_cookie.py`
        2. Ajuste configurações
        3. Clique em "Começar"
        4. Aguarde conclusão
        5. Download dos dados
        """)

    # Histórico de execuções
    st.markdown("---")
    st.subheader("📜 Histórico")
    
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            historico = json.load(f)
        
        st.info(f"✅ Última execução: {historico.get('timestamp')}")
        st.text(f"Produtos coletados: {historico.get('total_produtos')}")
    else:
        st.info("ℹ️ Nenhuma execução anterior encontrada.")


if __name__ == "__main__":
    main()
