# Execução rápida

1. Configure `.env` com as credenciais WeDrop e Supabase conforme `.env.example`.
2. Execute `supabase_schema.sql` uma vez no SQL Editor do projeto Supabase.
3. Rode o mapeamento integrado:

   ```powershell
   python wedrop_monitor_sistema.py
   ```

O comando valida o acesso ao Supabase, autentica e salva os cookies automaticamente quando a sessão venceu, percorre as categorias e grava produtos e históricos. Não rode um autenticador separado.

Para abrir o painel:

```powershell
streamlit run app_monitoramento_vendas.py
```

Use `run_auto.bat` para iniciar a coleta integrada no Windows. O relatório, as tabelas remotas, a cobertura por categoria e a rotina diária estão descritos em [WEDROP_CATALOG_README.md](WEDROP_CATALOG_README.md).
