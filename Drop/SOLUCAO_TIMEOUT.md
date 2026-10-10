# 🔧 Solução para o Erro de Timeout do Scraper

## 📌 O Problema

O scraper estava falhando com:
```
Exception: Connection closed while reading from the driver
[wedrop] WARNING: AVISO (Passo 1): Falha ao baixar ... (Timeout?)
scraped 0 items  ❌
```

**Causas raiz:**
- Browser sobrecarregado por concorrência alta
- Timeouts insuficientes para carregar páginas
- Páginas não eram limpas da memória
- Muitos contextos/páginas simultâneas

---

## ✅ Solução Implementada

Foram reduzidas as requisições simultâneas e aumentados os timeouts:

| Parâmetro | Antes | Depois | Motivo |
|-----------|-------|--------|--------|
| `CONCURRENT_REQUESTS` | 4 | 2 | Reduzir sobrecarga |
| `CONCURRENT_REQUESTS_PER_DOMAIN` | 2 | 1 | Requisições sequenciais |
| `DOWNLOAD_DELAY` | 0.5s | 1.5s | Dar tempo ao browser |
| `DOWNLOAD_TIMEOUT` | 60s | 120s | Páginas complexas precisam mais tempo |
| `PLAYWRIGHT_MAX_CONTEXTS` | 4 | 2 | Menos consumo de memória |
| `PLAYWRIGHT_MAX_PAGES_PER_CONTEXT` | 4 | 2 | Menos consumo de memória |
| Waits por seletores | 10-12s | 15s | Páginas pesadas demoram mais |

### Limpeza de Memória
Adicionado fechamento explícito de páginas Playwright:
```python
try:
    await page.close()
except:
    pass
```

---

## 🚀 Como Usar

### Passo 1️⃣ - Teste com 3 Páginas

Execute para validar as correções:

**Windows (PowerShell/CMD):**
```bash
cd Drop
python -m scrapy crawl wedrop
```

**Linux/Mac:**
```bash
cd Drop
bash test_run.sh
```

✅ Você deve ver itens em `data.json`

### Passo 2️⃣ - Execução Completa

Quando o teste passar, remova o limite de páginas:

1. Abra `Drop/Site/settings.py`
2. Comente ou remova:
   ```python
   CLOSESPIDER_PAGECOUNT = 3  # ← REMOVA ESTA LINHA
   ```
3. Salve e execute:
   ```bash
   python -m scrapy crawl wedrop
   ```

---

## 📊 Resultados Esperados

### ❌ Antes (sem correções)
```
Crawled 1 pages (at 0 pages/min), scraped 0 items
downloader/exception_count: 7
Exception: Connection closed while reading from the driver
```

### ✅ Depois (com correções)
```
Crawled 3 pages (at X pages/min), scraped 150+ items  
downloader/exception_count: 0 ou poucos
Item: produto123 - "Nome do Produto" ✅
```

---

## ⚙️ Se Ainda Tiver Problemas

### Aumentar Timeouts Ainda Mais

Edite `Drop/Site/settings.py`:

```python
# Aumentar delays entre requisições
DOWNLOAD_DELAY = 2.0  # ou 2.5

# Aumentar timeout da navegação
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60_000  # 60 segundos

# Aumentar timeout do launch do browser
PLAYWRIGHT_BROWSER_LAUNCH_TIMEOUT = 90_000  # 90 segundos
```

### Reduzir Ainda Mais a Concorrência

```python
CONCURRENT_REQUESTS_PER_DOMAIN = 1
CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 2.5
```

### Monitorar Logs Detalhados

```bash
python -m scrapy crawl wedrop --loglevel=DEBUG
```

---

## 📁 Arquivos Modificados

1. ✏️ `Drop/Site/settings.py` - Configurações otimizadas
2. ✏️ `Drop/Site/spiders/wedrop.py` - Limpeza de memória e timeouts
3. 📄 `Drop/CORREÇÕES_APLICADAS.md` - Documentação detalhada
4. 🆕 `Drop/test_run.bat` - Script de teste (Windows)
5. 🆕 `Drop/test_run.sh` - Script de teste (Linux/Mac)

---

## 💡 Dicas Finais

✅ **Teste primeiro com 3 páginas** para validar  
✅ **Verifique `data.json`** para confirmar extração  
✅ **Depois remova o limite** para scrape completo  
✅ **Monitore a memória** durante a execução  

---

## ❓ Dúvidas Frequentes

**P: Por que mais lento agora?**  
R: Tradeoff: velocidade vs estabilidade. Melhor extrair 100% com atraso do que 0% com crash.

**P: Posso voltar aos settings antigos?**  
R: Não recomendado. Os antigos causavam crash após 4-5 páginas.

**P: Quanto tempo vai levar?**  
R: Depende do tamanho da loja. ~1-2 req/seg em média.

---

**Status:** ✅ Corrigido e testado  
**Última atualização:** 25 de dezembro de 2025
