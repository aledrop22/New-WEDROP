-- Execute uma única vez após atualizar o coletor.
-- A migração anterior usava updated_at como aproximação, fazendo produtos antigos
-- aparecerem como novos. Este marcador impede que novas datas sejam apagadas ao
-- executar novamente este script.

create table if not exists public.wedrop_migrations (
    migration_key text primary key,
    applied_at timestamptz not null default now()
);

do $$
begin
    if not exists (
        select 1
        from public.wedrop_migrations
        where migration_key = 'reset_first_seen_baseline_v1'
    ) then
        update public.wedrop_products
        set first_seen_at = null
        where first_seen_at = updated_at;

        insert into public.wedrop_migrations (migration_key)
        values ('reset_first_seen_baseline_v1');
    end if;
end
$$;

select
    count(*) as produtos_total,
    count(*) filter (where first_seen_at is not null) as produtos_com_primeira_identificacao,
    count(*) filter (where first_seen_at is null) as produtos_da_base_historica
from public.wedrop_products;
