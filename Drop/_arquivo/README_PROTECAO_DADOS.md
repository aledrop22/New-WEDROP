# 🛡️ Sistema de Proteção de Dados - WeDrop Scraper

## 📋 Visão Geral

O novo sistema protegido resolve os problemas de perda de dados quando:
- Internet oscila ou cai durante a coleta
- Energia cai e o PC reinicia
- Erros no site WeDrop interrompem a coleta
- Coleta não puxa todos os produtos

## ✨ Funcionalidades

### 1. 🔄 Backup Automático
- Antes de cada coleta, cria backup do `data.json` e `wedrop_monitoramento.db`
- Backups salvos em `Drop/backups/backup_YYYYMMDD_HHMMSS/`
- Mantém os 5 backups mais recentes automaticamente

### 2. 📊 Validação de Quantidade
- Usa o banco de dados SQLite como referência
- Se a última coleta teve 5.000 produtos, exige pelo menos 90% (4.500) na nova
- Se não houver referência, aceita qualquer quantidade

### 3. 🔄 Retentativa Automática
- **Máximo 3 tentativas** com intervalo de 60 segundos
- Se falhar, restaura do backup automaticamente
- Só substitui os dados se a coleta for bem-sucedida

### 4. 🛡️ Proteção Contra Sobrescrita
- **NUNCA** sobrescreve dados se a coleta falhar
- Sempre restaura do backup mais recente em caso de erro
- Se todas as tentativas falharem, mantém os dados do backup inicial

## 🚀 Como Usar

### Execução Manual

Use o novo script protegido:

```bash
run_protected.bat
```

Ou diretamente:

```bash
python wedrop_protected_runner.py
```

### Execução Automática (Tarefa Agendada)

A tarefa do Windows já foi atualizada automaticamente para usar o runner protegido.

Se precisar reconfigurar:

```powershell
cd Drop
powershell -ExecutionPolicy Bypass -File configure_daily_task.ps1
```

## 📊 Como Funciona

### Fluxo de Execução

```
1. Obter quantidade esperada do banco de dados anterior
   ↓
2. Criar backup inicial (data.json + banco de dados)
   ↓
3. Executar scraper (tentativa 1)
   ↓
4. Validar resultado (pelo menos 90% dos produtos)
   ↓
   ✓ SUCESSO → Limpar backups antigos → FIM
   ✗ FALHA → Restaurar backup → Aguardar 60s → Tentar novamente
   ↓
5. Repetir até 3 tentativas
   ↓
   ✓ SUCESSO → Limpar backups antigos → FIM
   ✗ FALHA → Restaurar backup inicial → ERRO
```

### Exemplo de Log

```
2026-10-12 10:00:00 INFO Quantidade esperada de produtos: 5267
2026-10-12 10:00:01 INFO Backup inicial criado em: backups/backup_20261012_100001
2026-10-12 10:00:01 INFO ============================================================
2026-10-12 10:00:01 INFO Tentativa 1/3
2026-10-12 10:00:01 INFO ============================================================
2026-10-12 10:05:30 INFO Mapeamento concluído: 15 categorias, 3759 produtos
2026-10-12 10:05:31 INFO Validacao: 3759/5267 produtos (71.4%)
2026-10-12 10:05:31 WARNING ⚠️  Coleta insuficiente (71.4% < 90%)
2026-10-12 10:05:31 INFO Aguardando 60 segundos antes de tentar novamente...
2026-10-12 10:06:31 INFO Restaurando dados do backup inicial...
2026-10-12 10:06:32 INFO ============================================================
2026-10-12 10:06:32 INFO Tentativa 2/3
2026-10-12 10:06:32 INFO ============================================================
...
```

## ⚙️ Configuração

Você pode ajustar estes parâmetros em `wedrop_protected_runner.py`:

```python
MAX_RETRIES = 3              # Número máximo de tentativas
RETRY_DELAY_SECONDS = 60     # Tempo entre tentativas (segundos)
MIN_SUCCESS_PERCENTAGE = 0.90 # Porcentagem mínima de sucesso (90%)
```

## 📁 Estrutura de Arquivos

```
Drop/
├── wedrop_protected_runner.py    # Novo script protegido
├── run_protected.bat             # Novo batch para execução manual
├── wedrop_monitor_sistema.py     # Scraper original (usado internamente)
├── data.json                     # Dados atuais (protegido)
├── wedrop_monitoramento.db       # Banco de dados (protegido)
├── scraper_runs.log              # Log do scraper
└── backups/                      # Diretório de backups
    ├── backup_20261012_100001/
    │   ├── data.json
    │   └── wedrop_monitoramento.db
    ├── backup_20261011_195949/
    └── ...
```

## 🔍 Monitoramento

### Verificar últimos backups

```bash
dir backups\backup_* /O-D
```

### Verificar quantidade de produtos atual

```bash
python -c "import json; print(sum(1 for _ in open('data.json')))"
```

### Verificar quantidade no banco de dados

```bash
python -c "import sqlite3; c=sqlite3.connect('wedrop_monitoramento.db').cursor(); print(c.execute('SELECT COUNT(DISTINCT product_id) FROM products WHERE captured_at = (SELECT MAX(captured_at) FROM products)').fetchone()[0])"
```

## ❓ Perguntas Frequentes

### O PC precisa estar ligado?
**SIM**. O scraper roda localmente no seu computador. Se o PC estiver desligado, nada roda.

### E se a internet cair no meio da coleta?
O sistema detectará que a coleta não atingiu a quantidade esperada, restaurará o backup e tentará novamente até 3 vezes.

### E se a energia cair?
Se a energia cair DURANTE a coleta, o backup inicial ainda estará intacto na pasta `backups/`. Você pode restaurar manualmente se necessário.

### Os dados no Supabase também são protegidos?
Sim! O scraper original já envia para o Supabase em lotes de 50 produtos. Se a coleta falhar, o Supabase terá apenas os lotes que foram enviados antes do erro. O backup local garante que você tenha os dados completos para reenviar depois.

### Posso ajustar a porcentagem mínima de sucesso?
Sim! Edite `MIN_SUCCESS_PERCENTAGE` em `wedrop_protected_runner.py`. Por exemplo, para aceitar 80%:
```python
MIN_SUCCESS_PERCENTAGE = 0.80
```

## 🐛 Solução de Problemas

### "Todas as tentativas falharam"
- Verifique sua conexão com a internet
- Verifique se o site WeDrop está acessível
- Veja o log em `scraper_runs.log` para detalhes do erro
- Os dados foram restaurados do backup automaticamente

### "Quantidade esperada: 0"
- Isso é normal na primeira execução ou se o banco foi apagado
- O sistema aceitará qualquer quantidade como sucesso

### Tarefa agendada não rodou
- Verifique se o PC estava ligado
- Verifique se sua sessão do Windows estava ativa (pode estar bloqueada, mas logada)
- Execute `Get-ScheduledTask -TaskName "WeDrop Daily Catalog Scrape"` no PowerShell para ver o status

## 📞 Suporte

Se tiver problemas, verifique:
1. `scraper_runs.log` - Log detalhado do scraper
2. `wedrop_protected_runner.py` - Configure as tentativas e delays
3. Windows Task Scheduler - Verifique se a tarefa está configurada corretamente
