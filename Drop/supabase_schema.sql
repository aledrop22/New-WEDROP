create table if not exists public.wedrop_categories (
    category_url text primary key,
    name text not null,
    expected_products integer,
    mapped_products integer not null default 0,
    updated_at timestamptz not null
);

create table if not exists public.wedrop_products (
    product_id text primary key,
    name text not null,
    category text not null,
    url text not null,
    sku text,
    ean text,
    price text,
    availability text,
    stock text,
    total_stock_count text,
    real_balance text,
    is_active text,
    supplier text,
    cnpj text,
    origin_state text,
    ncm text,
    weight text,
    height text,
    width text,
    length text,
    description text,
    number_sales text,
    updated_at timestamptz not null,
    price_changed_at timestamptz
);

-- Em bancos já criados, rode só este comando no SQL Editor (a coleta exige a coluna).
alter table public.wedrop_products add column if not exists price_changed_at timestamptz;

create table if not exists public.wedrop_stock_events (
    event_id text primary key,
    product_id text not null references public.wedrop_products(product_id),
    movement_type text not null,
    event_kind text not null check (event_kind in ('sale', 'stock_in', 'other')),
    quantity integer not null,
    event_at timestamptz,
    event_at_raw text not null,
    nf_key text,
    recorded_at timestamptz not null
);

create index if not exists wedrop_stock_events_product_date_idx
    on public.wedrop_stock_events (product_id, event_at);

create index if not exists wedrop_stock_events_kind_date_idx
    on public.wedrop_stock_events (event_kind, event_at);

grant all on public.wedrop_categories to service_role;
grant all on public.wedrop_products to service_role;
grant all on public.wedrop_stock_events to service_role;

alter table public.wedrop_categories enable row level security;
alter table public.wedrop_products enable row level security;
alter table public.wedrop_stock_events enable row level security;
