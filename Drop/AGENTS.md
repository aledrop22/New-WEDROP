# Sistema de Rastreamento de Produtos Falhados

## Problema Resolvido

**Antes:** Quando uma categoria não completava (faltavam produtos), o sistema relia **toda a categoria** na próxima execução, incluindo produtos que já foram lidos com sucesso. Isso causava:
- Tempo de execução dobrado ou triplicado
- Leituras desnecessárias de produtos já salvos
- Retrabalho constante

**Agora:** O sistema rastreia **quais produtos específicos falharam** e lê apenas eles na próxima execução.

## Como Funciona

### 1. Rastreamento de Falhas
- Arquivo: `dados/produtos_falhados.json`
- Salva: `product_id`, `url`, `category_name`, `error`, `failed_at`
- Organizado por categoria

### 2. Fluxo de Execução

**Execução 1:**
- Categoria "Brinquedos" tem 1000 produtos
- 995 são lidos com sucesso
- 5 falham (timeout, erro de página, etc.)
- Sistema salva os 5 produtos falhados em `produtos_falhados.json`
- Dados dos 995 produtos são enviados ao Supabase

**Execução 2:**
- Sistema verifica `produtos_falhados.json`
- Encontra 5 produtos falhados em "Brinquedos"
- Lê **apenas os 5 produtos** (não relê os 995)
- Se todos tiverem sucesso: limpa a lista de falhas
- Se alguns ainda falharem: atualiza a lista com os que ainda falharam

### 3. Vantagens

✅ **Nunca relê produtos já salvos**
✅ **Tempo de execução muito menor** (só lê o que falta)
✅ **Dados sempre atualizados** (envia ao Supabase mesmo incompleto)
✅ **Investigação focada** (sabe exatamente quais produtos falharam)

## Arquivos Modificados

- `wedrop/config.py` - Adicionado `FAILED_PRODUCTS_FILE`
- `wedrop/mapping.py` - Lógica de rastreamento de falhas
- `wedrop/storage/failed_products.py` - Novo módulo de rastreamento
- `wedrop/storage/run_state.py` - Estado da coleta (inalterado)

## Regras Importantes

1. **Sempre para frente, nunca para trás** - Nunca reler produtos já salvos
2. **Falhas são isoladas** - Cada produto que falha é rastreado individualmente
3. **Dados sempre enviados** - Mesmo com falhas, envia o que foi lido ao Supabase
4. **Investigar depois** - Se produtos falharem consistentemente, investigar a causa

## Exemplo de Log

```
[7/14] Brinquedos: categoria inteira (quantidade mudou de 1044 para 1041).
Categoria Brinquedos: 1037 listados (0 novos, 739 esgotados pulados pelo selo); 21 acabaram de sair da listagem e serão lidos por inteiro.
  5 produto(s) não lidos; salvando para próxima execução.
Categoria Brinquedos não ficou completa; produtos que falharam serão tentados na próxima execução.
```

**Próxima execução:**
```
[7/14] Brinquedos: 5 produto(s) falharam na execução anterior; tentando reler só eles.
[1/5] Produto X (ID 12345): 10 movimentações.
[2/5] Produto Y (ID 12346): 10 movimentações.
...
[7/14] Brinquedos: todos os 5 produtos que falharam foram lidos com sucesso.
```

## Manutenção

- O arquivo `produtos_falhados.json` é limpo automaticamente quando todos os produtos de uma categoria são lidos
- Se um produto falhar consistentemente, verificar se a página está quebrada ou se há problema de rede
- Backup do arquivo é criado automaticamente junto com o backup do data.json
