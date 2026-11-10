export interface CategoryRecord {
  category_url: string;
  name: string;
  expected_products: number | null;
  mapped_products: number;
  updated_at: string;
}

export interface ProductRecord {
  product_id: string;
  name: string;
  category: string;
  url: string;
  sku: string | null;
  ean: string | null;
  price: string | null;
  previous_price?: string | null;
  availability: string | null;
  stock: string | null;
  total_stock_count: string | null;
  real_balance: string | null;
  is_active: string | null;
  was_active_yesterday?: boolean;
  /** Quando o preço mudou na última coleta que o viu mudar (o preço anterior não é guardado). */
  price_changed_at?: string | null;
  /** Primeira identificação registrada pelo scraper. */
  first_seen_at?: string | null;
  supplier: string | null;
  cnpj: string | null;
  origin_state: string | null;
  ncm: string | null;
  weight: string | null;
  height: string | null;
  width: string | null;
  length: string | null;
  description: string | null;
  number_sales: string | null;
  updated_at: string;
}

export type EventKind = 'sale' | 'stock_in' | 'other';

export interface StockEventRecord {
  event_id: string;
  product_id: string;
  movement_type: string;
  event_kind: EventKind;
  quantity: number;
  event_at: string;
  event_at_raw: string;
  nf_key: string | null;
  recorded_at: string;
}

export interface ProductStockSnapshot {
  observation_id: string;
  product_id: string;
  availability: string | null;
  is_active: string | null;
  stock: string | null;
  real_balance: string | null;
  is_listed: boolean | null;
  observed_at: string;
}

export interface CategorySummary {
  name: string;
  category_url?: string;
  expected_products: number | null;
  mapped_products: number;
  units_sold: number;
  units_restocked: number;
  active_products: number;
  inactive_products: number;
  products_without_status: number;
}

export interface ProductWithActivity extends ProductRecord {
  units_sold: number;
  units_restocked: number;
  status_bucket: 'Ativos' | 'Inativos' | 'Sem status';
}

export interface DailyActivityRow {
  day: string; // YYYY-MM-DD
  dayLabel: string; // DD/MM
  units_sold: number;
  units_restocked: number;
}

export interface TopProductDailyRow {
  product_id: string;
  name: string;
  category: string;
  url: string;
  total_sold: number;
  total_restocked: number;
  daily_sales: Record<string, number>; // dateString -> units
}

export interface DataSourceConfig {
  lastFetchedAt: string | null;
  isConnected: boolean;
  statusMessage: string;
}

// 24H & Day Comparison Models
export interface Product24hStats extends ProductRecord {
  salesToday: number;
  salesYesterday: number;
  salesDiff: number;
  salesPercentChange: number;
  restockToday: number;
  restockYesterday: number;
  isTrending: boolean;
  isReactivated: boolean;
  isOutOfStockNow: boolean;
}

export interface NewProductWithSales extends ProductRecord {
  first_seen_at: string;
  days_since_first_seen: number;
  units_sold_since_first_seen: number;
  last_sale_at: string | null;
}

export interface NewProductsData {
  totalAvailable: number;
  products: NewProductWithSales[];
  stockMonitoring: ProductStockMonitoring[];
  soldProducts: number;
  unsoldProducts: number;
  unitsSoldSinceEntry: number;
  missingFirstSeenCount: number;
  recentlyUnavailableCount: number;
  decliningStockCount: number;
  noRecentSalesCount: number;
  stockTrackingReady: boolean;
}

export interface ProductStockMonitoring extends ProductRecord {
  currentStock: number | null;
  previousStock: number | null;
  unitsSoldLast7Days: number;
  lastSaleAt: string | null;
  observedAt: string;
  situation:
    | 'Esgotado com vendas'
    | 'Esgotado sem vendas'
    | 'Saiu do catálogo'
    | 'Reposto'
    | 'Voltou ao catálogo'
    | 'Saldo em queda'
    | 'Sem vendas há 7 dias';
}

export interface Category24hComparison {
  name: string;
  category_url?: string;
  salesToday: number;
  salesYesterday: number;
  salesDiff: number;
  restockToday: number;
  itemsCountToday: number;
  itemsCountYesterday: number;
  itemsDiff: number;
  itemsReason: 'new_products' | 'restock' | 'out_of_stock' | 'stable';
  rank: number;
}

// Themes & Layout
export type ThemeMode = 'light' | 'dark';

export type ThemeId =
  | 'light-wedrop'
  | 'light-emerald'
  | 'light-amber'
  | 'dark-onyx'
  | 'dark-black'
  | 'dark-midnight';

export interface ThemeOption {
  id: ThemeId;
  name: string;
  mode: ThemeMode;
  description: string;
  primaryColor: string;
  badgeBg: string;
}

/** Cor de destaque escolhida pelo usuário; 'tema' usa a cor padrão do tema atual. */
export type AccentId =
  | 'tema'
  | 'vermelho'
  | 'esmeralda'
  | 'ciano'
  | 'azul'
  | 'violeta'
  | 'rosa'
  | 'ambar';

export interface AccentOption {
  id: AccentId;
  name: string;
  color: string;
  hover: string;
}

export type DashboardViewMode =
  | 'decision_24h'
  | 'day_comparison'
  | 'full_catalog'
  | 'new_products';
