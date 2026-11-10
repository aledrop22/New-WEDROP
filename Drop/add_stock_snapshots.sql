create table if not exists public.wedrop_stock_snapshots (
    observation_id text primary key,
    product_id text not null references public.wedrop_products(product_id),
    availability text,
    is_active text,
    stock text,
    real_balance text,
    is_listed boolean,
    observed_at timestamptz not null
);

create index if not exists wedrop_stock_snapshots_product_date_idx
    on public.wedrop_stock_snapshots (product_id, observed_at desc);
create index if not exists wedrop_stock_snapshots_date_idx
    on public.wedrop_stock_snapshots (observed_at);

grant all on public.wedrop_stock_snapshots to service_role;
alter table public.wedrop_stock_snapshots enable row level security;
