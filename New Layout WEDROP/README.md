# WeDrop Monitoramento (React)

Painel de vendas, catálogo e reposições do WeDrop, publicado na Vercel. Substitui o painel Streamlit (`Drop/app_monitoramento_vendas.py`), com as mesmas consultas e as mesmas regras de status e de dia.

Stack: **React + TypeScript + Vite + Tailwind CSS**, com uma função serverless em `api/snapshot.ts` que lê o Supabase.

## Como os dados chegam

```
WeDrop (site) → coleta Python (pasta Drop, roda no computador) → Supabase
Supabase → api/snapshot.ts (Vercel, chave de serviço no servidor) → painel React
```

- A coleta continua sendo feita pelo projeto Python. Este painel só lê o Supabase.
- A chave `SUPABASE_SERVICE_ROLE_KEY` fica só nas variáveis de ambiente da Vercel. O navegador nunca a recebe.
- Os dias são calculados no fuso de São Paulo (`America/Sao_Paulo`), igual ao Streamlit rodando no Brasil.
- O painel abre com o dia de hoje e lê o Supabase ao abrir a página. A coleta roda às 00:00, então não há atualização automática: o botão Atualizar relê os dados. O cache da função dura 5 minutos.

## Recursos

- **Métricas do período**: categorias, itens disponíveis e indisponíveis, sem status, vendas e reposições (do dia ou do período).
- **Auditoria de produtos sem status**: tabela expansível com ID, produto, categoria, fornecedor, estoque, data da leitura e link para o WeDrop.
- **Categorias ranqueadas**: as 14 categorias por unidades vendidas, com o Top 5 numerado.
- **Detalhe da categoria**: filtro por status (Todos, Disponíveis, Indisponíveis, Sem status), busca por nome, SKU, EAN ou fornecedor, tabela paginada e gráfico de vendas e reposições por produto.
- **Gráficos gerais**: movimentações por dia, movimentações por categoria, 20 produtos mais vendidos no período e tabela dos 100 produtos com mais movimentação, com volume por dia.
- **Decisão 24h** (tela inicial): vendas de ontem × hoje por categoria (quantos produtos venderam em cada dia), destaques de quem vende nos dois dias e de quem saiu só hoje ou só ontem, alertas de alteração de preço de ontem e hoje, top 20 e reposições.
- **Visões extras**: Comparativo D-1 vs D0 e Preços (alta/baixa). A visão de Preços fica vazia, porque o preço anterior não é guardado; os alertas de alteração estão na Decisão 24h.
- **Botões**: atualizar agora, exportar CSV, trocar tema e abrir o modal de conexão e status da leitura (só leitura).

## Variáveis de ambiente (Vercel)

Em **Project Settings → Environment Variables**:

| Variável | Valor |
|---|---|
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Chave service_role do Supabase |

Consulte `.env.example`. Não use prefixo `VITE_` nessas chaves.

## Publicar na Vercel

1. Em **Add New → Project**, importe o repositório.
2. Em **Root Directory**, selecione `New Layout WEDROP/New Layout WEDROP` (a pasta que tem este README).
3. Framework: **Vite**. Build: `npm run build`. Output: `dist`.
4. Configure as duas variáveis acima e faça o deploy.

## Rodar localmente

```bash
npm install
npx vercel dev
```

`npm run dev` sobe só o Vite. Sem a função `/api/snapshot`, o painel mostra o erro de leitura. Use `vercel dev` para testar com os dados reais.

## Estrutura do Banco de Dados

Consulte `supabase_schema.sql`:
- `wedrop_categories`
- `wedrop_products`
- `wedrop_stock_events`
