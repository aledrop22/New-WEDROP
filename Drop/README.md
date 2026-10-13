# WeDrop — coleta de catálogo e painel de vendas

## Como usar

| Para quê | Comando |
|---|---|
| Coleta manual (retoma se a anterior foi interrompida) | `coletar.bat` ou `python -m wedrop coletar` |
| Só algumas categorias | `python -m wedrop coletar --categoria Cozinha` |
| Painel de vendas e estoque | `painel.bat` |
| Coleta diária incremental (agendador do Windows) | `python -m wedrop diaria` |
| Preencher preços que faltam no data.json | `python -m ferramentas.corrigir_precos` |

Credenciais ficam no `.env` (`WEDROP_EMAIL`, `WEDROP_PASSWORD`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`).

## Regras de segurança dos dados

- Antes de qualquer coleta, o `dados/data.json` é copiado para `dados/backups/`.
- Coleta **concluída** anteriormente: a próxima começa do zero (o `data.json` é reescrito).
- Coleta **interrompida** (erro, queda de sessão, internet): a próxima **retoma**, sem apagar nada e sem repetir produtos já salvos. O estado fica em `dados/estado_coleta.json`.
- Produto que abre sem nome e sem preço não é gravado: é relido e, se continuar vazio, fica para a próxima execução.
- Backups antigos são comprimidos (`.json.gz`), nunca apagados.
- Coleta parcial (`--categoria` ou `--limite`) só acrescenta dados e não muda o estado da coleta completa.

## Coleta diária incremental

`python -m wedrop diaria` não percorre o site inteiro. Antes de ler produtos, compara a quantidade de cada categoria (mostrada na página de categorias) com a última coleta, guardada na tabela `categories` do SQLite:

- **Quantidade igual** e todos os produtos da categoria já no `data.json`: lê só **preço e saldo** de cada produto. O restante já está salvo, e a listagem da categoria não é percorrida.
- **Quantidade diferente**, categoria nunca coletada ou `data.json` com menos produtos que o site: lê a **categoria inteira** (listagem completa e todos os campos).
- Se uma leitura de preço e saldo falhar, a categoria inteira é lida.
- Produto que saiu da categoria é retirado do `data.json` quando a categoria é lida inteira.

Limite: uma categoria com quantidade igual não tem o histórico de movimentações relido. Vendas que não mudam a quantidade só entram no painel quando a categoria for lida inteira. A coleta manual (`coletar`) continua completa.

## Estrutura

```
Drop/
├── wedrop/                 pacote principal
│   ├── config.py           caminhos, URLs e limites
│   ├── mapping.py          coleta completa (categorias → listagens → produtos → gravação)
│   ├── protection.py       coleta diária com novas tentativas
│   ├── cli.py              comandos `coletar` e `diaria`
│   ├── names.py            limpeza de nomes de produto
│   ├── scraping/           navegador, sessão, categorias, leitura do produto (funções puras em parsing.py e product_record.py)
│   └── storage/            data.json, estado da coleta, SQLite (painel) e Supabase
├── ferramentas/            reparos pontuais (corrigir_precos)
├── app_monitoramento_vendas.py   painel Streamlit
├── tests/                  testes unitários (python -m unittest discover -s tests -t .)
├── dados/                  data.json, banco SQLite, backups e sessão (não versionado)
├── logs/                   log da coleta
├── _arquivo/               código e documentos antigos, mantidos para consulta
└── configure_daily_task.ps1   registra a tarefa diária no Windows
```

## Testes

```
python -m unittest tests.test_scraping tests.test_data_file tests.test_storage
```

## Pendências conhecidas

- A listagem da categoria Cozinha chega a 1275 de 1276 produtos; o último ainda não foi identificado.
- A API `api.wedrop.com.br/v3/api/catalog/<id>` responde em cerca de 0,3 s (o navegador leva de 3 a 5 s por produto). Ainda não foi usada na coleta porque os campos precisam ser mapeados e conferidos antes.
