# Guia de execução WeDrop

## Configurar uma vez

- Copie `.env.example` para `.env` e informe `WEDROP_EMAIL`, `WEDROP_PASSWORD`, `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`.
- Use aspas nas variáveis de senha que contenham `#`, espaços ou caracteres especiais.
- Execute `supabase_schema.sql` uma vez no SQL Editor do Supabase.
- Instale dependências com `python -m pip install -r requirements.txt` e Chromium com `python -m playwright install chromium`.

## Coletar e atualizar

```powershell
python wedrop_monitor_sistema.py
```

Login, confirmação da sessão, salvamento automático de cookies, mapeamento integral e sincronização de dados ocorrem nessa mesma execução. Se a sessão existente não funcionar, o comando autentica novamente antes de iniciar o mapeamento. O estado de autenticação fica em `storage_state.json`, ignorado pelo Git.

As tabelas `wedrop_categories`, `wedrop_products` e `wedrop_stock_events` são verificadas antes da coleta. Erros de autenticação ou gravação no Supabase interrompem a execução com uma mensagem de erro.

## Dashboard

```powershell
streamlit run app_monitoramento_vendas.py
```

O painel exibe o top 20 diário, gráficos de vendas, entradas de estoque e cobertura do mapeamento. Também é possível fornecer e-mail/senha no formulário de atualização do painel. Para uma coleta diária automática, agende `python wedrop_monitor_sistema.py` no Agendador de Tarefas do Windows.

Veja [WEDROP_CATALOG_README.md](WEDROP_CATALOG_README.md) para lista de campos e solução de problemas.
