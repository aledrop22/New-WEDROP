# 🎯 Guia Rápido - Instalação e Uso

## ✨ O que foi criado?

Um **app Streamlit completo** para fazer scraping do novo site **Seu Armazém Drop**.

Migração do Scrapy (terminal) para Streamlit (interface web moderna) 🎉

---

## 🚀 Instalação em 4 passos

### **Passo 1️⃣ : Instalar Dependências**

**Opção A - Script Automático (Windows):**
```
Duplo clique em: instalar_dependencias.bat
```

**Opção B - Manual:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

### **Passo 2️⃣ : Configurar Credenciais**

Edite o arquivo `obter_cookie_novo_site.py`:

```python
LOGIN_EMAIL = "seu_email@seuarmazemdrop.com"  # ← ALTERE
SENHA_LOGIN = "sua_senha"                     # ← ALTERE
```

Salve.

### **Passo 3️⃣ : Fazer Login**

```bash
python obter_cookie_novo_site.py
```

O navegador abrirá automaticamente e fará o login.
Aguarde a confirmação → Arquivo `storage_state.json` será criado ✅

### **Passo 4️⃣ : Iniciar o App**

**Opção A - Script automático:**
```
Duplo clique em: start_streamlit.bat
```

**Opção B - Terminal:**
```bash
python start_streamlit.py
```

O app abrirá em: **http://localhost:8501** 🎉

---

## 📁 Estrutura de Arquivos

```
Drop/
├── 🎯 app_streamlit.py              ← App principal (Streamlit)
├── 🔐 obter_cookie_novo_site.py     ← Fazer login
├── ✅ validar_config_streamlit.py   ← Verificar tudo
├── 🚀 start_streamlit.py            ← Iniciar app (Python)
├── 🚀 start_streamlit.bat           ← Iniciar app (Windows)
├── 📦 instalar_dependencias.bat     ← Instalar tudo
│
├── 📚 README_STREAMLIT.md           ← Documentação completa
├── 📋 COMECE_AQUI_STREAMLIT.txt     ← Guia rápido
├── 📊 RESUMO_STREAMLIT.txt          ← Este arquivo
├── 📖 INSTALLATION_QUICK_START.md   ← Você está aqui
│
├── requirements.txt                 ← Dependências Python
├── storage_state.json               ← Gerado automaticamente
└── dados_catalogo.json              ← Dados coletados
```

---

## ✅ Verificação Rápida

Para verificar se tudo está instalado corretamente:

```bash
python validar_config_streamlit.py
```

Saída esperada:
```
✅ Python
✅ Dependências
✅ Playwright
✅ Autenticação
✅ Arquivos
```

Se algum item mostrar ❌, execute os comandos sugeridos.

---

## 💡 Como Usar o App

### Interface

1. **Sidebar (esquerda):**
   - Ajuste número de páginas (1-50)
   - Veja status da autenticação

2. **Botão Principal:**
   - Clique em "Começar Coleta de Dados"
   - Acompanhe em tempo real

3. **Resultados:**
   - Visualize tabela com dados
   - Download em CSV ou JSON
   - Veja estatísticas

### Exemplo de Uso

```
1. Abra o app
2. Na sidebar, escolha 5 páginas
3. Clique em "Começar"
4. Aguarde 2-5 minutos
5. Clique em "📥 Download CSV"
6. Arquivo baixado com sucesso!
```

---

## 🆘 Problemas Comuns

### ❌ "storage_state.json não encontrado"
```bash
python obter_cookie_novo_site.py
```

### ❌ "Streamlit não instalado"
```bash
pip install streamlit>=1.28.0
```

### ❌ "Playwright não encontrado"
```bash
python -m playwright install chromium
```

### ❌ "Timeout ao fazer scraping"
- Reduza número de páginas
- Ou aumente timeout (linha ~93 em `app_streamlit.py`):
  ```python
  timeout=45000  # aumentar de 30000
  ```

### ❌ "Dados não aparecem"
- Verifique se credenciais estão corretas
- Tente fazer login novamente
- Inspecione HTML da página (F12)

---

## 📊 Dados Coletados

O app coleta:
- **ID** do produto
- **Nome** do produto
- **Preço**
- **Estoque**
- **Categoria**
- **Status**
- **Data/hora** da coleta

Arquivos gerados:
- `dados_catalogo.json` (automático)
- `produtos_YYYYMMDD_HHMMSS.csv` (download)
- `produtos_YYYYMMDD_HHMMSS.json` (download)

---

## 🎯 Site Alvo

- **URL:** https://app.seuarmazemdrop.com.br/dashboard/catalog
- **Método:** GET
- **Parâmetros:** `per_page=100&page={número}`
- **Autenticação:** Requerida (cookies)

---

## 🔒 Segurança

⚠️ **Importante:**
- Nunca faça commit do `obter_cookie_novo_site.py` com credenciais
- Nunca compartilhe `storage_state.json`
- Use `.gitignore` para ignorar:
  ```
  storage_state.json
  obter_cookie_novo_site.py
  dados_catalogo.json
  *.csv
  ```

---

## 📞 Suporte

Se tiver problemas:

1. **Leia:** `README_STREAMLIT.md` (documentação completa)
2. **Execute:** `python validar_config_streamlit.py` (diagnóstico)
3. **Verifique:** `COMECE_AQUI_STREAMLIT.txt` (FAQ rápido)

---

## 🎓 Mais Informações

### Diferença Scrapy vs Streamlit

| Aspecto | Scrapy | Streamlit |
|---------|--------|-----------|
| **Interface** | Terminal | Web (navegador) |
| **Visualização** | Logs + JSON | Tabelas + Gráficos |
| **Interação** | Linha de comando | Botões e sliders |
| **Download** | Manual | One-click |
| **Tempo de setup** | Rápido | Médio |
| **Facilidade** | Técnico | User-friendly |

### Por que Streamlit?

✅ Interface moderna e intuitiva  
✅ Não precisa de HTML/CSS  
✅ Compartilha fácil (qualquer PC)  
✅ Visualização melhor  
✅ Download one-click  

### Por que Playwright?

✅ Suporta JavaScript (site usa JS)  
✅ Gerencia cookies automaticamente  
✅ Detecta quando página carregou  
✅ Rápido e confiável  

---

## 🚀 Comandos Úteis

```bash
# Instalar tudo
pip install -r requirements.txt && python -m playwright install chromium

# Fazer login
python obter_cookie_novo_site.py

# Validar configuração
python validar_config_streamlit.py

# Iniciar app
streamlit run app_streamlit.py

# Ou usar o inicializador
python start_streamlit.py
```

---

## 📅 Versão & Info

- **Versão:** 1.0
- **Criado:** Janeiro 2024
- **Status:** ✅ Pronto para produção
- **Python:** 3.10+
- **Streamlit:** 1.28+
- **Playwright:** 1.48+

---

## 🎉 Pronto!

Siga os **4 passos acima** e seu app estará funcionando em minutos! 🚀

Se tiver dúvidas, consulte `README_STREAMLIT.md` para documentação completa.

**Divirta-se fazendo scraping!** 📊
