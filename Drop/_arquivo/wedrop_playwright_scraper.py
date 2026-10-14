import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime


async def extract_product_details(page, category_name):
    """Extrai todos os detalhes de um produto individual"""
    details = {
        'name': '',
        'sku': '',
        'ean': '',
        'price': '',
        'availability': '',
        'category': category_name,
        'supplier': '',
        'origin_state': '',
        'ncm': '',
        'weight': '',
        'height': '',
        'width': '',
        'length': '',
        'description': '',
        'stock_history': []
    }

    try:
        # Nome do produto
        name_elem = await page.query_selector('h2.css-18puvtl')
        if name_elem:
            details['name'] = await name_elem.text_content()

        # SKU e EAN
        sku_ean_elem = await page.query_selector('p.css-nk7nkj')
        if sku_ean_elem:
            text = await sku_ean_elem.text_content()
            if 'SKU:' in text:
                details['sku'] = text.split('SKU:')[1].split('|')[0].strip()
            if 'EAN:' in text:
                details['ean'] = text.split('EAN:')[1].strip()

        # Preço
        price_elem = await page.query_selector('p.css-1enygfq')
        if price_elem:
            details['price'] = await price_elem.text_content()

        # Disponibilidade
        availability_elem = await page.query_selector('span.css-1dvt0g7')
        if availability_elem:
            details['availability'] = await availability_elem.text_content()

        # Fornecedor
        supplier_elem = await page.query_selector('p.css-1dv5bo2')
        if supplier_elem:
            text = await supplier_elem.text_content()
            if 'Fornecedor:' in text:
                details['supplier'] = text.split('Fornecedor:')[1].strip()

        # Estado de origem
        state_elem = await page.query_selector('p.css-ww2hub')
        if state_elem:
            text = await state_elem.text_content()
            if 'Estado de origem:' in text:
                details['origin_state'] = text.split('Estado de origem:')[1].strip()

        # Especificações técnicas
        specs = await page.query_selector_all('div.css-tuph3t')
        for spec in specs:
            try:
                label_elem = await spec.query_selector('p.css-1wld651')
                value_elem = await spec.query_selector('p.css-nidmuk')
                if label_elem and value_elem:
                    label = await label_elem.text_content()
                    value = await value_elem.text_content()
                    label_upper = label.upper()
                    if 'NCM' in label_upper:
                        details['ncm'] = value
                    elif 'PESO' in label_upper:
                        details['weight'] = value
                    elif 'ALTURA' in label_upper:
                        details['height'] = value
                    elif 'LARGURA' in label_upper:
                        details['width'] = value
                    elif 'COMPRIMENTO' in label_upper:
                        details['length'] = value
            except:
                pass

        # Descrição
        desc_elem = await page.query_selector('p.css-11h7gfg')
        if desc_elem:
            details['description'] = await desc_elem.text_content()

        # Histórico de estoque - clicar na aba
        try:
            # Procurar pela aba de histórico de estoque
            history_tab = await page.query_selector('button[role="tab"]')
            if history_tab:
                tabs = await page.query_selector_all('button[role="tab"]')
                for tab in tabs:
                    tab_text = await tab.text_content()
                    if 'Histórico de Estoque' in tab_text:
                        await tab.click()
                        await page.wait_for_timeout(1000)
                        break

                # Extrair histórico
                history_items = await page.query_selector_all('div.css-2p27im')
                for item in history_items:
                    try:
                        # Tipo de movimentação
                        type_elem = await item.query_selector('span.css-1kghjv8')
                        movement_type = await type_elem.text_content() if type_elem else ''

                        # Quantidade
                        qty_elem = await item.query_selector('p.css-1yd6l9q')
                        quantity = await qty_elem.text_content() if qty_elem else ''

                        # Data
                        date_elem = await item.query_selector('p.css-1dv5bo2')
                        date = await date_elem.text_content() if date_elem else ''

                        # Chave da NF
                        nf_elem = await item.query_selector('p.css-1dv5bo2')
                        nf_key = ''
                        if nf_elem:
                            nf_text = await nf_elem.text_content()
                            if 'Chave da NF:' in nf_text:
                                nf_key = nf_text.split('Chave da NF:')[1].strip()

                        if movement_type and quantity:
                            details['stock_history'].append({
                                'type': movement_type.strip(),
                                'quantity': quantity.strip(),
                                'date': date.strip(),
                                'nf_key': nf_key.strip()
                            })
                    except:
                        pass
        except Exception as e:
            print(f"  Erro ao extrair histórico de estoque: {e}")

    except Exception as e:
        print(f"  Erro ao extrair detalhes do produto: {e}")

    return details

async def scrape_wedrop_catalog():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Carregar storage state se existir
        storage_state = None
        try:
            with open('storage_state.json', 'r') as f:
                storage_state = json.load(f)
        except:
            print("storage_state.json não encontrado, usando contexto vazio")

        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()

        print("Navegando para https://dash.wedrop.com.br/catalog...")
        await page.goto('https://dash.wedrop.com.br/catalog', wait_until='domcontentloaded')

        # Aguardar carregamento
        await page.wait_for_timeout(5000)

        # Obter conteúdo
        content = await page.content()
        print(f"Comprimento do conteúdo: {len(content)}")

        # Salvar HTML para análise
        with open('debug_catalog_playwright.html', 'w', encoding='utf-8') as f:
            f.write(content)

        # Tentar extrair categorias
        print("\nTentando extrair categorias...")

        # Procurar elementos que contenham categorias
        # Buscar por elementos com texto que pareça categoria
        categories = []

        # Seletores baseados na estrutura HTML fornecida
        selectors_to_try = [
            'a[draggable="false"][data-group=""]',  # Seletor específico para categorias
            'a[href*="/catalog"]',  # Links para o catálogo
        ]

        for selector in selectors_to_try:
            elements = await page.query_selector_all(selector)
            print(f"Seletor '{selector}': {len(elements)} elementos encontrados")

            for elem in elements:
                try:
                    # Extrair nome da categoria (primeiro <p> com classe css-1uniu7j)
                    category_name_elem = await elem.query_selector('p.css-1uniu7j')
                    if category_name_elem:
                        category_name = await category_name_elem.text_content()
                    else:
                        # Fallback: tentar extrair do atributo title
                        title_attr = await elem.get_attribute('title')
                        if title_attr:
                            category_name = title_attr.split('—')[0].strip()
                        else:
                            continue

                    # Extrair quantidade (segundo <p> com classe css-1lser6l)
                    count_elem = await elem.query_selector('p.css-1lser6l')
                    if count_elem:
                        count = await count_elem.text_content()
                    else:
                        # Fallback: tentar extrair do atributo title
                        title_attr = await elem.get_attribute('title')
                        if title_attr and '—' in title_attr:
                            count = title_attr.split('—')[1].strip().replace('produtos', '').strip()
                        else:
                            count = '0'

                    # Extrair href
                    href = await elem.get_attribute('href')

                    if category_name and count:
                        categories.append({
                            'category_name': category_name.strip(),
                            'category_count': count.strip(),
                            'category_url': href if href else ''
                        })
                        print(f"  - {category_name.strip()}: {count.strip()} produtos")
                except Exception as e:
                    print(f"  Erro ao extrair categoria: {e}")
                    pass

        # Salvar categorias
        with open('wedrop_categories.json', 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)

        print(f"\nTotal de categorias encontradas: {len(categories)}")
        print("Salvo em wedrop_categories.json")

        # Agora, para cada categoria, extrair produtos
        all_products = []
        for cat in categories[:3]:  # Limitar a 3 categorias para teste
            if not cat['category_url']:
                continue

            category_url = f"https://dash.wedrop.com.br{cat['category_url']}" if cat['category_url'].startswith('/') else cat['category_url']
            print(f"\n\nAcessando categoria: {cat['category_name']}")
            print(f"URL: {category_url}")

            await page.goto(category_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)

            # Extrair produtos da categoria
            product_selectors = 'div.chakra-stack.css-5hmulo'
            products = await page.query_selector_all(product_selectors)
            print(f"Produtos encontrados: {len(products)}")

            for prod in products:
                try:
                    # Nome do produto
                    name_elem = await prod.query_selector('p.css-hgz24n')
                    name = await name_elem.text_content() if name_elem else ''

                    # Preço
                    price_elem = await prod.query_selector('p.css-1hulv5q')
                    price = await price_elem.text_content() if price_elem else ''

                    # Status de anúncios
                    status_elem = await prod.query_selector('p.css-12leqgu')
                    status = await status_elem.text_content() if status_elem else ''

                    # SKU
                    sku_elem = await prod.query_selector('p.css-ytmi7j')
                    sku = ''
                    if sku_elem:
                        sku_text = await sku_elem.text_content()
                        if 'SKU:' in sku_text:
                            sku = sku_text.replace('SKU:', '').strip()

                    # Categoria
                    category_elem = await prod.query_selector('p.css-ytmi7j')
                    product_category = cat['category_name']

                    if name:
                        # Extrair URL do produto clicando nele
                        try:
                            # Tentar encontrar o link pai
                            parent_link = await prod.query_selector('a')
                            if parent_link:
                                product_url = await parent_link.get_attribute('href')
                                if product_url:
                                    full_product_url = f"https://dash.wedrop.com.br{product_url}" if product_url.startswith('/') else product_url
                                    print(f"\n  Acessando produto: {name.strip()}")
                                    print(f"  URL: {full_product_url}")

                                    # Navegar para página do produto
                                    await page.goto(full_product_url, wait_until='domcontentloaded')
                                    await page.wait_for_timeout(2000)

                                    # Extrair detalhes completos do produto
                                    product_details = await extract_product_details(page, cat['category_name'])
                                    product_details['category_url'] = category_url
                                    all_products.append(product_details)
                                    print(f"  ✓ {product_details['name']}: {product_details['price']}")

                                    # Voltar para categoria
                                    await page.goto(category_url, wait_until='domcontentloaded')
                                    await page.wait_for_timeout(2000)
                                    products = await page.query_selector_all(product_selectors)  # Re-selecionar após voltar
                        except Exception as e:
                            print(f"  Erro ao acessar produto: {e}")
                            # Fallback: adicionar apenas dados básicos
                            all_products.append({
                                'name': name.strip(),
                                'price': price.strip(),
                                'status': status.strip(),
                                'sku': sku.strip(),
                                'category': product_category.strip(),
                                'category_url': category_url
                            })
                except Exception as e:
                    print(f"  Erro ao extrair produto: {e}")
                    pass

        # Salvar produtos
        with open('wedrop_products.json', 'w', encoding='utf-8') as f:
            json.dump(all_products, f, ensure_ascii=False, indent=2)

        print(f"\n\nTotal de produtos extraídos: {len(all_products)}")
        print("Salvo em wedrop_products.json")

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_wedrop_catalog())
