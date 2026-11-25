# Sistema de Retry Automático de Produtos Falhados

## Visão Geral

Implementado sistema de retry automático que tenta corrigir produtos que falharam **30 minutos após a coleta principal**, sem esperar a próxima coleta agendada.

## Como Funciona

### Fluxo Principal

1. **Coleta Principal** (00:00 ou 10:00)
   - Lê todos os produtos
   - Salva dados no `data.json`
   - Envia ao Supabase
   - Identifica produtos que falharam

2. **Retry Automático** (30 minutos depois)
   - Aguarda a coleta principal terminar
   - Aguarda 30 minutos
   - Tenta ler **apenas os produtos que falharam**
   - Se conseguir: limpa a lista de falhas
   - Se não conseguir: documenta para investigação futura

### Rastreamento de Falhas

- **Arquivo:** `dados/produtos_falhados.json`
- **Conteúdo:** Lista de produtos que falharam por categoria
- **Campos:** `product_id`, `url`, `category_name`, `error`, `failed_at`

### Documentação de Problemas

- **Arquivo:** `dados/produtos_com_problema.md`
- **Conteúdo:** Produtos que falharam consistentemente
- **Uso:** Investigação futura de problemas

## Vantagens

✅ **Nunca relê produtos já salvos** - Só lê os que falharam
✅ **Dados sempre atualizados** - Retry automático corrige problemas rapidamente
✅ **Tempo de execução menor** - Não precisa esperar próxima coleta agendada
✅ **Investigação focada** - Sabe exatamente quais produtos falharam
✅ **Documentação automática** - Registra problemas para análise futura

## Configuração

- **Delay do retry:** 30 minutos (configurável em `protection.py`)
- **Tentativas:** 3 por produto (configurável em `config.py`)
- **Categorias:** Todas as categorias são verificadas

## Exemplo de Execução

```
00:00 - Coleta principal inicia
01:30 - Coleta principal termina
01:30 - 5 produtos falharam em "Brinquedos"
01:30 - Agendando retry automático em 30 minutos
02:00 - Retry automático inicia
02:00 - Tentando ler 5 produtos falhados de "Brinquedos"
02:05 - Todos os 5 produtos lidos com sucesso!
02:05 - Lista de falhas limpa
```

## Arquivos Modificados

- `wedrop/protection.py` - Sistema de retry automático
- `wedrop/mapping.py` - Lógica de rastreamento de falhas
- `wedrop/storage/failed_products.py` - Módulo de rastreamento (novo)
- `wedrop/config.py` - Adicionado `FAILED_PRODUCTS_FILE`
- `AGENTS.md` - Documentação do sistema

## Próximos Passos

1. **Monitorar** o arquivo `produtos_falhados.json` para ver padrões de falha
2. **Investigar** produtos que falham consistentemente
3. **Ajustar** timeouts ou seletores se necessário
4. **Otimizar** baseado nos dados de falha
