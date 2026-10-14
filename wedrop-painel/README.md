# WeDrop Monitoramento (React)

Painel de vendas, catÃ¡logo e reposiÃ§Ãµes do WeDrop, publicado na Vercel. Substitui o painel Streamlit (`Drop/app_monitoramento_vendas.py`), com as mesmas consultas e as mesmas regras de status e de dia.

Stack: **React + TypeScript + Vite + Tailwind CSS**, com uma funÃ§Ã£o serverless em `api/snapshot.ts` que lÃª o Supabase.

## Como os dados chegam

```
WeDrop (site) â†’ coleta Python (pasta Drop, roda no computador) â†’ Supabase
Supabase â†’ api/snapshot.ts (Vercel, chave de serviÃ§o no servidor) â†’ painel React
```

- A coleta continua sendo feita pelo projeto Python. Este painel sÃ³ lÃª o Supabase.
- A chave `SUPABASE_SERVICE_ROLE_KEY` fica sÃ³ nas variÃ¡veis de ambiente da Vercel. O navegador nunca a recebe.
- Os dias sÃ£o calculados no fuso de SÃ£o Paulo (`America/Sao_Paulo`), igual ao Streamlit rodando no Brasil.
- O painel abre com o dia de hoje e lÃª o Supabase ao abrir a pÃ¡gina. A coleta roda Ã s 00:00, entÃ£o nÃ£o hÃ¡ atualizaÃ§Ã£o automÃ¡tica: o botÃ£o Atualizar relÃª os dados. O cache da funÃ§Ã£o dura 5 minutos.

## Recursos

- **MÃ©tricas do perÃ­odo**: categorias, itens disponÃ­veis e indisponÃ­veis, sem status, vendas e reposiÃ§Ãµes (do dia ou do perÃ­odo).
- **Auditoria de produtos sem status**: tabela expansÃ­vel com ID, produto, categoria, fornecedor, estoque, data da leitura e link para o WeDrop.
- **Categorias ranqueadas**: as 14 categorias por unidades vendidas, com o Top 5 numerado.
- **Detalhe da categoria**: filtro por status (Todos, DisponÃ­veis, IndisponÃ­veis, Sem status), busca por nome, SKU, EAN ou fornecedor, tabela paginada e grÃ¡fico de vendas e reposiÃ§Ãµes por produto.
- **GrÃ¡ficos gerais**: movimentaÃ§Ãµes por dia, movimentaÃ§Ãµes por categoria, 20 produtos mais vendidos no perÃ­odo e tabela dos 100 produtos com mais movimentaÃ§Ã£o, com volume por dia.
- **DecisÃ£o 24h** (tela inicial): vendas de ontem Ã— hoje por categoria (quantos produtos venderam em cada dia), destaques de quem vende nos dois dias e de quem saiu sÃ³ hoje ou sÃ³ ontem, alertas de alteraÃ§Ã£o de preÃ§o de ontem e hoje, top 20 e reposiÃ§Ãµes.
- **VisÃµes extras**: Comparativo D-1 vs D0 e PreÃ§os (alta/baixa). A visÃ£o de PreÃ§os fica vazia, porque o preÃ§o anterior nÃ£o Ã© guardado; os alertas de alteraÃ§Ã£o estÃ£o na DecisÃ£o 24h.
- **BotÃµes**: atualizar agora, exportar CSV, trocar tema e abrir o modal de conexÃ£o e status da leitura (sÃ³ leitura).

## VariÃ¡veis de ambiente (Vercel)

Em **Project Settings â†’ Environment Variables**:

| VariÃ¡vel | Valor |
|---|---|
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Chave service_role do Supabase |

Consulte `.env.example`. NÃ£o use prefixo `VITE_` nessas chaves.

## Publicar na Vercel

1. Em **Add New â†’ Project**, importe o repositÃ³rio.
2. Em **Root Directory**, selecione `wedrop-painel` (a pasta que tem este README).
3. Framework: **Vite**. Build: `npm run build`. Output: `dist`.
4. Configure as duas variÃ¡veis acima e faÃ§a o deploy.

## Rodar localmente

```bash
npm install
npx vercel dev
```

`npm run dev` sobe sÃ³ o Vite. Sem a funÃ§Ã£o `/api/snapshot`, o painel mostra o erro de leitura. Use `vercel dev` para testar com os dados reais.

## Estrutura do Banco de Dados

Consulte `supabase_schema.sql`:
- `wedrop_categories`
- `wedrop_products`
- `wedrop_stock_events`


