# Monitoramento WeDrop

O fluxo principal mapeia o catálogo autenticado WeDrop e sincroniza produtos, estoque, saldos e histórico de movimentações no Supabase e em um banco SQLite local.

## Configuração única

1. Na pasta `Drop`, copie `.env.example` para `.env`.
2. Configure `WEDROP_EMAIL`, `WEDROP_PASSWORD`, `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`.
3. Execute `Drop/supabase_schema.sql` uma vez no SQL Editor do Supabase.
4. Instale as dependências de `Drop/requirements.txt` e o Chromium do Playwright:

   ```powershell
   cd Drop
   python -m pip install -r requirements.txt
   python -m playwright install chromium
   ```

As credenciais e cookies são privados. `.env` e `storage_state.json` estão ignorados pelo Git.

## Coletar

Dentro de `Drop`, execute:

```powershell
python wedrop_monitor_sistema.py
```

O mesmo comando verifica ou renova a sessão, salva os cookies e continua o mapeamento completo, sem executar um script de autenticação separado. Também pode ser iniciado por `run_auto.bat` ou `run_wedrop_catalog.bat`. O processo verifica as tabelas do Supabase antes de abrir o catálogo e falha explicitamente se configuração ou gravação remota estiver indisponível.

## Visualizar relatórios

```powershell
streamlit run app_monitoramento_vendas.py
```

O painel mostra o ranking diário dos 20 produtos mais vendidos, gráficos de vendas, entradas de estoque e cobertura de produtos por categoria. Consulte [Drop/WEDROP_CATALOG_README.md](Drop/WEDROP_CATALOG_README.md) para detalhes.
