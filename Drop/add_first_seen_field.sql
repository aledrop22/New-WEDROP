-- Script SQL para adicionar o campo first_seen_at e popular retroativamente
-- Execute no SQL Editor do Supabase

-- 1. Adiciona a coluna (se não existir)
alter table public.wedrop_products add column if not exists first_seen_at timestamptz;

-- 2. Cria índice para performance
create index if not exists wedrop_products_first_seen_idx on public.wedrop_products (first_seen_at);

-- 3. Popula retroativamente: produtos que já existem recebem a data updated_at como first_seen_at
-- Isso garante que produtos coletados antes tenham uma data de primeira visualização
update public.wedrop_products
set first_seen_at = updated_at
where first_seen_at is null;

-- 4. Verificação: mostra quantos produtos foram atualizados
select count(*) as produtos_com_first_seen,
       count(*) filter (where first_seen_at is not null) as produtos_populados
from public.wedrop_products;
