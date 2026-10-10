# Painel WeDrop

O painel atualmente recomendado é `app_monitoramento_vendas.py`. No sidebar, selecione um período e consulte as categorias com unidades vendidas e reabastecidas. Ao selecionar uma categoria, o painel exibe os produtos movimentados, totais por produto e gráficos diários e por produto. A visão geral apresenta o comparativo por categoria e os 20 produtos mais vendidos no período.

## Executar

Configure `.env` conforme `.env.example`, execute uma vez `supabase_schema.sql` no Supabase e instale as dependências de `requirements.txt`. Depois inicie:

```powershell
streamlit run app_monitoramento_vendas.py
```

O painel não solicita e-mail ou senha. Eles são lidos de `WEDROP_EMAIL` e `WEDROP_PASSWORD` no `.env` (ou no ambiente do processo). Se a sessão salva estiver válida, o login é reutilizado; se estiver vencida, a coleta autentica automaticamente, salva os cookies e continua sem etapa separada.

Use **Atualizar catálogo e históricos** para executar o login, o mapeamento e a sincronização sem obter cookies em uma etapa separada. O scraper grava no banco SQLite local e nas tabelas `wedrop_categories`, `wedrop_products` e `wedrop_stock_events` do Supabase. Falhas de configuração ou gravação remota são mostradas como erro.

Veja [WEDROP_CATALOG_README.md](./WEDROP_CATALOG_README.md) para configuração, campos mapeados e solução de problemas.
