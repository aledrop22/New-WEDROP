# Monitoramento do catálogo WeDrop

O fluxo principal está concentrado em `wedrop_monitor_sistema.py`: ele lê a configuração local, valida a sessão, autentica automaticamente quando necessário, mapeia todas as categorias e produtos e grava catálogo e histórico no SQLite e no Supabase. Não é preciso obter cookies antes nem executar um segundo scraper.

## Configuração inicial

1. Para execução local, copie `.env.example` para `.env` dentro de `Drop`.
2. Preencha `WEDROP_EMAIL`, `WEDROP_PASSWORD`, `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`.
3. No SQL Editor do projeto Supabase, execute uma vez o conteúdo de `supabase_schema.sql`.
4. Instale as dependências: `python -m pip install -r requirements.txt`.
5. Execute o mapeamento integrado: `python wedrop_monitor_sistema.py`.

O arquivo `.env` e os cookies locais não devem ser enviados ao Git. A chave de serviço Supabase fica somente no processo local do scraper; não a coloque em JavaScript ou código do navegador. Para o Streamlit Community Cloud, o `.env` do computador não é publicado com o app. Configure as quatro variáveis em **App settings > Secrets** no formato TOML (uma variável por linha, entre aspas). O dashboard lê as chaves do Secrets sem expor seus valores.

## Coleta local de teste

Para testar uma categoria sem enviar dados ao Supabase, execute dentro de `Drop`:

```powershell
python wedrop_monitor_sistema.py --category Beleza --limit 10 --local-only
```

O filtro procura o texto no nome da categoria, preferindo correspondência exata. O limite é total por execução; a contagem completa informada pelo site é mantida separada da quantidade de produtos detalhados. O comando grava os registros coletados em `data.json` (JSON Lines) e no SQLite local, sem sincronização remota. Sem `--local-only`, o comportamento padrão continua validando e sincronizando com o Supabase.

O scraper mostra no terminal cada etapa de autenticação, leitura dos produtos e gravação. O mesmo registro fica em `scraper_runs.log`, com rotação dos arquivos antigos. Antes de iniciar uma nova leitura válida, `data.json` é limpo; o histórico do SQLite e os dados sincronizados anteriormente no Supabase não são apagados.

## Agendamento diário no Windows

Execute uma vez `.\configure_daily_task.ps1` no PowerShell dentro desta pasta para registrar a coleta completa às 00:00 no Agendador de Tarefas do Windows. A tarefa usa o ambiente virtual do repositório, lê as credenciais do `.env` e atualiza `data.json`, SQLite e Supabase. O usuário precisa permanecer conectado ao Windows; a sessão pode estar bloqueada. Se o computador estiver suspenso, a tarefa pode acordá-lo e executar a coleta quando estiver disponível. Confira o andamento e falhas em `scraper_runs.log`.

O programa verifica a sessão do catálogo a cada execução. Se ela tiver expirado, usa as credenciais configuradas, valida o login, salva `storage_state.json` e continua a coleta na mesma execução. Em terminal interativo, e-mail e senha podem ser solicitados sem gravar a senha; no painel, são lidos do `.env`/ambiente ou de Streamlit Secrets e nenhum campo de credenciais é exibido. O processo falha explicitamente se o login, a configuração do Supabase ou uma gravação remota falhar.

## Dados mantidos

- Categorias, contagem informada pelo site e quantidade de produtos encontrados.
- Identificador, título, categoria e URL do produto.
- SKU, EAN, preço, disponibilidade/estoque, saldo, situação, fornecedor, CNPJ, estado de origem, NCM, dimensões, peso, descrição e contador de vendas quando exibidos na página.
- Registros do histórico de estoque, com tipo de movimento, quantidade, data/hora original, data interpretada e chave da nota fiscal.

Em cada categoria, a coleta seleciona 100 produtos por página quando o seletor oferece essa opção. Ela acompanha "Página X de Y", avança automaticamente até a página final e interrompe com erro explícito se a paginação ou a contagem reportada indicar que faltaram produtos.

Cada produto detalhado é salvo em lotes de 50 no `data.json` (JSON Lines), no SQLite e no Supabase. O arquivo é reiniciado no começo de uma coleta válida e recebe cada lote sincronizado, para que os lotes concluídos continuem disponíveis se uma execução falhar. Ele inclui nome/título, preço, SKU, EAN, estoque, saldo, descrição, NCM, dimensões, fornecedor, vendas e histórico de estoque. Os scripts de transformação existentes aceitam JSON Lines.

O Streamlit consulta o SQLite local para apresentar os produtos e as movimentações; assim, cada lote local salvo fica disponível para o painel quando a execução retorna ou informa um erro. As tabelas `wedrop_categories`, `wedrop_products` e `wedrop_stock_events` recebem upserts idempotentes. Eventos repetidos em uma coleta diária não são contabilizados duas vezes.

## Painel e rotina diária

Inicie o painel com `streamlit run app_monitoramento_vendas.py` ou `start_streamlit.bat`. Enquanto a página estiver aberta, o painel relê o SQLite automaticamente a cada cinco minutos, refletindo a coleta noturna sem precisar atualizar o navegador. A barra lateral mantém fixas as 14 categorias exibidas no catálogo, em uma lista vertical, inclusive antes da primeira coleta. Cada card mostra o total reportado pelo site, vendas e reposições no dia (ou no intervalo escolhido), além da contagem de produtos mapeados ativos e inativos. Ao abrir uma categoria, os produtos aparecem na página principal; filtre a tabela por status. O nome do produto é um link direto para o WeDrop e o SKU pode ser copiado. Use **Atualizar catálogo e históricos** para executar a coleta e renovar a sessão quando necessário.

Para manter a série diária, execute o scraper uma vez por dia pelo Agendador de Tarefas do Windows. O comando é `python wedrop_monitor_sistema.py`; ele faz autenticação, mapeamento e sincronização numa única execução.

## Troubleshooting

- **Supabase não configurado:** localmente, verifique as variáveis no `.env`. No Streamlit Cloud, configure `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` em **App settings > Secrets**; configure também `WEDROP_EMAIL` e `WEDROP_PASSWORD` para autenticar. O `.env` local não é enviado à hospedagem.
- **Tabela inexistente/permissão negada:** execute `supabase_schema.sql` no SQL Editor e mantenha a chave de serviço apenas no processo local.
- **Login recusado:** confira as credenciais; cookies só são salvos depois de confirmar a navegação autenticada.
- **Categoria com cobertura incompleta:** o painel compara o total reportado com os links de produtos encontrados; confira se o site carrega paginação/lazy-loading ou se mudou sua interface.
- **Histórico sem totais no gráfico:** eventos com data ilegível são preservados no banco, porém não podem ser agrupados por dia.

O spider Scrapy antigo continua no repositório por compatibilidade, mas não é usado pelos lançadores principais. Use o fluxo unificado acima.
