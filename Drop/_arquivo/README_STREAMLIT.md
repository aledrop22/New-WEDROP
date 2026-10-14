# Painel WeDrop

O painel atualmente recomendado é `app_monitoramento_vendas.py`. A barra lateral mantém visíveis, uma abaixo da outra, as 14 categorias do catálogo WeDrop. Cada cartão apresenta o total informado pelo site, vendas, reposições e quantidades de produtos ativos e inativos. Selecione uma categoria para abrir no conteúdo principal a tabela de produtos, filtrável por status; o nome do produto abre o item no WeDrop e o SKU pode ser copiado da tabela.

## Executar

Configure `.env` conforme `.env.example`, execute uma vez `supabase_schema.sql` no Supabase e instale as dependências de `requirements.txt`. Depois inicie:

```powershell
streamlit run app_monitoramento_vendas.py
```

O painel não solicita e-mail ou senha. Localmente, eles são lidos de `WEDROP_EMAIL` e `WEDROP_PASSWORD` no `.env` (ou no ambiente do processo). No Streamlit Community Cloud, o `.env` local não é enviado: configure as credenciais em **App settings > Secrets**, usando nomes TOML no nível superior:

```toml
WEDROP_EMAIL = "seu-email"
WEDROP_PASSWORD = "sua-senha"
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "sua-chave-de-servico"
```

Nunca publique a chave de serviço nem coloque esses valores no repositório. Se a sessão salva estiver válida, o login é reutilizado; se estiver vencida, a coleta autentica, salva os cookies e continua sem etapa separada.

Use **Atualizar catálogo e históricos** para executar o login, o mapeamento e a sincronização sem obter cookies em uma etapa separada. O scraper salva cada lote de 50 produtos no `data.json` em formato JSON Lines, no banco SQLite local e nas tabelas `wedrop_categories`, `wedrop_products` e `wedrop_stock_events` do Supabase. O painel consulta o SQLite para montar tabelas e gráficos e, ao abrir uma categoria, mostra os dados salvos do produto, incluindo preço, SKU, descrição, NCM, estoque, dimensões e histórico agregado de vendas/reposições. Falhas de configuração ou gravação remota são mostradas como erro; os lotes locais já concluídos permanecem salvos.

Durante o mapeamento, o scraper seleciona 100 produtos por página quando essa opção está disponível, lê o indicador "Página X de Y" e avança sozinho até a última página de cada categoria. Divergências entre a contagem da categoria e os produtos coletados são reportadas como erro em vez de marcar silenciosamente a categoria como completa.

Veja [WEDROP_CATALOG_README.md](./WEDROP_CATALOG_README.md) para configuração, campos mapeados e solução de problemas.
