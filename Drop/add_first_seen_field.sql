-- Script SQL para adicionar o campo first_seen_at.
-- Produtos existentes permanecem sem first_seen_at: não há histórico confiável
-- para inferir quando entraram no catálogo a partir de updated_at.
-- Execute no SQL Editor do Supabase

-- 1. Adiciona a coluna (se não existir)
alter table public.wedrop_products add column if not exists first_seen_at timestamptz;

-- 2. Cria índice para performance
create index if not exists wedrop_products_first_seen_idx on public.wedrop_products (first_seen_at);

-- 3. Verificação: novas inserções passam a receber first_seen_at na coleta.
select count(*) as produtos_com_first_seen,
       count(*) filter (where first_seen_at is null) as produtos_na_base_historica
from public.wedrop_products;
