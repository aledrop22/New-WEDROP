# Sistema de Scraping Incremental WeDrop

Este sistema permite atualizações eficientes do catálogo WeDrop, evitando scraping desnecessário.

## Componentes

### 1. `wedrop_monitor_sistema.py` (Script Principal)
Scraping completo do catálogo - use apenas para:
- Primeira execução (catalogação inicial)
- Quando precisar de um mapeamento completo

### 2. `category_checker.py` (Verificador de Categorias)
Verifica apenas os números das categorias para detectar mudanças.
- Rápido: lê apenas a página inicial do catálogo
- Salva contagens em `category_counts.json`
- Detecta adições/remoções de produtos por categoria

Uso:
```bash
python Drop/category_checker.py
```

### 3. `stock_corrector.py` (Corretor de Saldo)
Atualiza apenas os campos de estoque no data.json existente.
- Não rescrapa produtos
- Visita cada produto e extrai: stock, total_stock_count, real_balance
- Edita o data.json inplace mantendo todos os outros dados

Uso:
```bash
python Drop/stock_corrector.py
```

### 4. `wedrop_incremental.py` (Script Incremental Inteligente)
Combina tudo em um fluxo automatizado:
1. Verifica mudanças nas categorias
2. Se não houver mudança → atualiza apenas saldos
3. Se houver mudança → rescrapa apenas categorias alteradas

Uso:
```bash
python Drop/wedrop_incremental.py
```

### 5. `wedrop_resume.py` (Retomada de Coleta)
Continua de onde o scraping parou sem apagar dados.
- Útil quando o scraping principal é interrompido por erro
- Detecta produtos já coletados no data.json
- Continua de onde parou

Uso:
```bash
python Drop/wedrop_resume.py
```

## Fluxo Recomendado

### Primeira Execução
```bash
python Drop/wedrop_monitor_sistema.py
```
Isso cria:
- `data.json` - catálogo completo
- `wedrop_monitoramento.db` - banco SQLite local
- `category_counts.json` - contagem inicial das categorias

### Atualizações Diárias (Recomendado)
```bash
python Drop/wedrop_incremental.py
```

**Cenário 1: Nenhuma mudança nas categorias**
- Detecta que os números são iguais
- Executa apenas `stock_corrector.py`
- Atualiza saldos de estoque rapidamente
- Não rescrapa produtos

**Cenário 2: Categoria alterada**
- Detecta mudança nos números
- Rescrapa apenas a categoria alterada
- Atualiza saldos das outras categorias
- Mantém produtos de categorias não alteradas

## Arquivos

- `data.json` - Catálogo completo em JSON Lines (1 produto por linha)
- `category_counts.json` - Contagem de produtos por categoria
- `wedrop_monitoramento.db` - Banco SQLite local
- `storage_state.json` - Sessão autenticada do navegador
- `scraper_runs.log` - Log detalhado das execuções

## Vantagens do Sistema Incremental

1. **Economia de tempo**: Se não houver mudanças, apenas atualiza saldos
2. **Economia de recursos**: Não rescrapa produtos que não mudaram
3. **Menos carga no servidor**: Apenas verifica números ou produtos específicos
4. **Rápido**: Atualização de saldos é muito mais rápida que scraping completo
5. **Flexível**: Pode ser agendado para rodar automaticamente

## Agendamento Automático (Windows)

### Agendar tarefa diária (Task Scheduler)

1. Abrir "Agendador de Tarefas do Windows"
2. Criar tarefa básica
3. Nome: "WeDrop Atualização Diária"
4. Gatilho: Diariamente às [horário desejado]
5. Ação: Iniciar programa
   - Programa: `python.exe`
   - Argumentos: `C:\Users\xandy\Documents\GitHub\Scrapy-WEDROP\.venv\Scripts\python.exe C:\Users\xandy\Documents\GitHub\Scrapy-WEDROP\Drop\wedrop_incremental.py`
   - Iniciar em: `C:\Users\xandy\Documents\GitHub\Scrapy-WEDROP`

### Agendamento via script batch

Criar `run_incremental.bat`:
```batch
@echo off
cd /d C:\Users\xandy\Documents\GitHub\Scrapy-WEDROP
.venv\Scripts\python.exe Drop\wedrop_incremental.py
```

## Notificações Futuras

O sistema pode ser expandido para:
- Detectar notificações de novos produtos
- Detectar mudanças de preço
- Alertas automáticos quando categorias mudam
- Integração com sistemas de notificação (email, Slack, etc.)

## Correções Implementadas

1. **Saldo de estoque**: Clique automático na aba "Valores/Estoque/Saldo" antes de extrair dados
2. **Erro de navegação**: Retry automático (até 3 tentativas) quando o contexto é destruído
3. **Limite de paginação**: Aviso em vez de erro quando não consegue acessar todas as páginas
