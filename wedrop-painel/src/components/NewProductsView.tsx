import React, { useMemo, useState } from 'react';
import { ExternalLink, Search, Sparkles } from 'lucide-react';
import { NewProductsData, NewProductWithSales, ProductRecord, ProductStockMonitoring } from '../types/wedrop';
import { formatCurrency, formatDateTimeBR, formatInt } from '../utils/status';
import { SortableTableHeader, nextTableSort, parseSortNumber, sortTableRows, TableSortState } from './SortableTableHeader';

const PERIOD_OPTIONS = [3, 7, 15, 20, 30, 60, 90, 120];
const PAGE_SIZE = 20;

interface NewProductsViewProps {
  data: NewProductsData;
  periodDays: number;
  onChangePeriod: (days: number) => void;
  onSelectProduct: (product: ProductRecord) => void;
}

export const NewProductsView: React.FC<NewProductsViewProps> = ({
  data,
  periodDays,
  onChangePeriod,
  onSelectProduct,
}) => {
  const [search, setSearch] = useState('');
  const [salesFilter, setSalesFilter] = useState<'all' | 'sold' | 'unsold'>('all');
  const [page, setPage] = useState(1);
  const [sortState, setSortState] = useState<TableSortState | null>(null);

  const filteredProducts = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('pt-BR');
    return data.products.filter((product) => {
      if (salesFilter === 'sold' && product.units_sold_since_first_seen === 0) return false;
      if (salesFilter === 'unsold' && product.units_sold_since_first_seen > 0) return false;
      if (!query) return true;
      return [product.name, product.sku || '', product.category]
        .some((value) => value.toLocaleLowerCase('pt-BR').includes(query));
    });
  }, [data.products, salesFilter, search]);

  const handleSort = (key: string) => {
    setSortState((current) => nextTableSort(current, key));
    setPage(1);
  };
  const sortedProducts = sortTableRows(filteredProducts, sortState, (product, key) => {
    switch (key) {
      case 'name': return product.name;
      case 'category': return product.category;
      case 'first_seen': return Date.parse(product.first_seen_at);
      case 'days': return product.days_since_first_seen;
      case 'units_sold': return product.units_sold_since_first_seen;
      case 'last_sale': return product.last_sale_at ? Date.parse(product.last_sale_at) : null;
      case 'price': return parseSortNumber(product.price);
      default: return null;
    }
  });
  const totalPages = Math.max(1, Math.ceil(filteredProducts.length / PAGE_SIZE));
  const paginatedProducts = sortedProducts.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <section className="space-y-5 mb-8">
      <div className="flex flex-col gap-3 rounded-xl border border-theme bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-emerald-500" />
            <h2 className="text-lg font-bold text-theme">Entradas e acompanhamento de estoque</h2>
          </div>
          <p className="mt-1 text-xs text-muted">
            Acompanhe novas entradas, produtos que esgotaram ou saíram do catálogo, saldo em queda e itens com estoque sem venda recente.
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs font-semibold text-muted">
          Entraram nos últimos
          <select
            value={periodDays}
            onChange={(event) => {
              onChangePeriod(Number(event.target.value));
              setPage(1);
            }}
            className="rounded-lg border border-theme bg-card-secondary px-3 py-2 text-theme focus:outline-none focus:ring-2 focus:ring-accent"
          >
            {PERIOD_OPTIONS.map((days) => (
              <option key={days} value={days}>{days} dias</option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <MetricCard label="Disponíveis hoje" value={data.totalAvailable} tone="text-emerald-500" />
        <MetricCard label={`Novos disponíveis · ${periodDays} dias`} value={data.products.length} tone="text-accent" />
        <MetricCard label="Novos com vendas" value={data.soldProducts} tone="text-blue-500" />
        <MetricCard
          label="Novos sem vendas"
          value={data.unsoldProducts}
          detail={`${formatInt(data.unitsSoldSinceEntry)} unidades vendidas desde a entrada`}
          tone="text-amber-500"
        />
        <MetricCard label="Esgotados ou fora do catálogo · 7 dias" value={data.recentlyUnavailableCount} tone="text-red-500" />
        <MetricCard label="Saldo em queda · 7 dias" value={data.decliningStockCount} tone="text-orange-500" />
        <MetricCard label="Com saldo e sem vendas · 7 dias" value={data.noRecentSalesCount} tone="text-amber-500" />
      </div>

      {!data.stockTrackingReady && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
          O acompanhamento de saldo começa após configurar a tabela de histórico no Supabase e executar a próxima coleta. Não há snapshots antigos confiáveis para reconstruir essa semana.
        </div>
      )}

      {data.missingFirstSeenCount > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
          {formatInt(data.missingFirstSeenCount)} produtos disponíveis já faziam parte da base antes do início do rastreamento.
          Como não há histórico confiável da entrada deles, não são contados como novos. As novas inserções serão registradas pela coleta.
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-theme bg-card">
        <div className="flex flex-col gap-3 border-b border-theme p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-sm font-bold text-theme">Produtos identificados no período</h3>
            <p className="mt-1 text-xs text-muted">
              As vendas contam somente movimentações registradas a partir da data de entrada de cada produto.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="flex items-center gap-1 rounded-lg border border-theme bg-card-secondary p-1">
              {([
                ['all', 'Todos'],
                ['sold', 'Com vendas'],
                ['unsold', 'Sem vendas'],
              ] as const).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => {
                    setSalesFilter(value);
                    setPage(1);
                  }}
                  className={`rounded-md px-2.5 py-1.5 text-xs font-bold ${
                    salesFilter === value ? 'bg-card text-theme shadow-2xs' : 'text-muted hover:text-theme'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="relative w-full sm:w-56">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted" />
              <input
                type="search"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder="Buscar produto, SKU, categoria"
                className="w-full rounded-lg border border-theme bg-card-secondary py-2 pl-9 pr-3 text-xs text-theme focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-xs">
            <thead className="border-b border-theme bg-card-secondary uppercase text-muted">
              <tr>
                <SortableTableHeader sortKey="name" sortState={sortState} onSort={handleSort} className="px-4 py-3">Produto</SortableTableHeader>
                <SortableTableHeader sortKey="category" sortState={sortState} onSort={handleSort} className="px-3 py-3">Categoria</SortableTableHeader>
                <SortableTableHeader sortKey="first_seen" sortState={sortState} onSort={handleSort} className="px-3 py-3">Identificado em</SortableTableHeader>
                <SortableTableHeader sortKey="days" sortState={sortState} onSort={handleSort} align="right" className="px-3 py-3">Dias no catálogo</SortableTableHeader>
                <SortableTableHeader sortKey="units_sold" sortState={sortState} onSort={handleSort} align="right" className="px-3 py-3">Vendido desde a entrada</SortableTableHeader>
                <SortableTableHeader sortKey="last_sale" sortState={sortState} onSort={handleSort} className="px-3 py-3">Última venda</SortableTableHeader>
                <SortableTableHeader sortKey="price" sortState={sortState} onSort={handleSort} align="right" className="px-3 py-3">Preço</SortableTableHeader>
              </tr>
            </thead>
            <tbody className="divide-y divide-theme text-theme">
              {paginatedProducts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-muted">
                    {data.products.length === 0
                      ? `Nenhum produto disponível foi identificado nos últimos ${periodDays} dias.`
                      : 'Nenhum produto corresponde aos filtros.'}
                  </td>
                </tr>
              ) : (
                paginatedProducts.map((product) => (
                  <ProductRow key={product.product_id} product={product} onSelect={onSelectProduct} />
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-theme px-4 py-3 text-xs text-muted">
          <span>{formatInt(filteredProducts.length)} produtos</span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              className="rounded border border-theme px-2.5 py-1 disabled:opacity-40"
            >
              Anterior
            </button>
            <span>{page} / {totalPages}</span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              className="rounded border border-theme px-2.5 py-1 disabled:opacity-40"
            >
              Próxima
            </button>
          </div>
        </div>
      </div>

      <StockMonitoringTable products={data.stockMonitoring} onSelectProduct={onSelectProduct} />
    </section>
  );
};

const MetricCard: React.FC<{ label: string; value: number; detail?: string; tone: string }> = ({
  label,
  value,
  detail,
  tone,
}) => (
  <div className="rounded-xl border border-theme bg-card p-4">
    <div className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</div>
    <div className={`mt-1 text-2xl font-black ${tone}`}>{formatInt(value)}</div>
    {detail && <div className="mt-1 text-[11px] text-muted">{detail}</div>}
  </div>
);

const ProductRow: React.FC<{
  product: NewProductWithSales;
  onSelect: (product: ProductRecord) => void;
}> = ({ product, onSelect }) => (
  <tr className="hover:bg-card-secondary/60">
    <td className="px-4 py-3">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => onSelect(product)}
          className="text-left font-semibold text-theme hover:text-accent"
        >
          {product.name}
        </button>
        <a
          href={product.url}
          target="_blank"
          rel="noreferrer"
          title="Abrir produto na WeDrop"
          className="text-muted hover:text-accent"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>
      <div className="mt-1 text-[10px] text-muted">SKU: {product.sku || '—'}</div>
    </td>
    <td className="px-3 py-3">{product.category || '—'}</td>
    <td className="whitespace-nowrap px-3 py-3">{formatDateTimeBR(product.first_seen_at)}</td>
    <td className="px-3 py-3 text-right">{formatInt(product.days_since_first_seen)}</td>
    <td className="px-3 py-3 text-right">
      <span className={product.units_sold_since_first_seen > 0 ? 'font-bold text-blue-500' : 'text-amber-500'}>
        {product.units_sold_since_first_seen > 0
          ? `${formatInt(product.units_sold_since_first_seen)} un.`
          : 'Sem vendas'}
      </span>
    </td>
    <td className="whitespace-nowrap px-3 py-3">{formatDateTimeBR(product.last_sale_at)}</td>
    <td className="whitespace-nowrap px-3 py-3 text-right">{formatCurrency(product.price)}</td>
  </tr>
);

const StockMonitoringTable: React.FC<{
  products: ProductStockMonitoring[];
  onSelectProduct: (product: ProductRecord) => void;
}> = ({ products, onSelectProduct }) => {
  const [filter, setFilter] = useState<'all' | 'unavailable' | 'returned' | 'declining' | 'no_sales'>('all');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const matchingProducts = useMemo(() => {
    const search = query.trim().toLocaleLowerCase('pt-BR');
    return products.filter((product) => {
      if (filter === 'unavailable' && !['Esgotado com vendas', 'Esgotado sem vendas', 'Saiu do catálogo'].includes(product.situation)) return false;
      if (filter === 'returned' && !['Reposto', 'Voltou ao catálogo'].includes(product.situation)) return false;
      if (filter === 'declining' && product.situation !== 'Saldo em queda') return false;
      if (filter === 'no_sales' && product.situation !== 'Sem vendas há 7 dias') return false;
      return !search || [product.name, product.sku || '', product.category]
        .some((value) => value.toLocaleLowerCase('pt-BR').includes(search));
    });
  }, [products, filter, query]);
  const totalPages = Math.max(1, Math.ceil(matchingProducts.length / PAGE_SIZE));
  const visibleProducts = matchingProducts.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
  <div className="overflow-hidden rounded-xl border border-theme bg-card">
    <div className="border-b border-theme p-4">
      <h3 className="text-sm font-bold text-theme">Saídas e sinais de estoque · últimos 7 dias</h3>
      <p className="mt-1 text-xs text-muted">
        Mostra itens que esgotaram ou saíram do catálogo, saldo em queda e produtos com estoque sem venda recente.
      </p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <select
          value={filter}
          onChange={(event) => {
            const value = event.target.value;
            if (value === 'all' || value === 'unavailable' || value === 'returned' || value === 'declining' || value === 'no_sales') {
              setFilter(value);
            }
            setPage(1);
          }}
          className="rounded-lg border border-theme bg-card-secondary px-3 py-2 text-xs text-theme"
        >
          <option value="all">Todos os sinais</option>
          <option value="unavailable">Esgotados ou fora do catálogo</option>
          <option value="returned">Repostos ou retornados</option>
          <option value="declining">Saldo em queda</option>
          <option value="no_sales">Com saldo e sem vendas</option>
        </select>
        <input
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(1);
          }}
          placeholder="Buscar produto, SKU ou categoria"
          className="min-w-0 flex-1 rounded-lg border border-theme bg-card-secondary px-3 py-2 text-xs text-theme"
        />
      </div>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] text-left text-xs">
        <thead className="border-b border-theme bg-card-secondary uppercase text-muted">
          <tr>
            <th className="px-4 py-3">Produto</th>
            <th className="px-3 py-3">Categoria</th>
            <th className="px-3 py-3">Situação</th>
            <th className="px-3 py-3 text-right">Saldo início → atual</th>
            <th className="px-3 py-3 text-right">Vendas · 7 dias</th>
            <th className="px-3 py-3">Última venda</th>
            <th className="px-3 py-3 text-right">Preço</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-theme text-theme">
          {visibleProducts.length === 0 ? (
            <tr>
              <td colSpan={7} className="px-4 py-8 text-center text-muted">
                {products.length === 0
                  ? 'Nenhum produto com saída ou sinal de estoque nos últimos 7 dias.'
                  : 'Nenhum produto corresponde aos filtros.'}
              </td>
            </tr>
          ) : (
            visibleProducts.map((product) => (
              <tr key={product.product_id} className="hover:bg-card-secondary/60">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => onSelectProduct(product)}
                      className="text-left font-semibold text-theme hover:text-accent"
                    >
                      {product.name}
                    </button>
                    <a href={product.url} target="_blank" rel="noreferrer" title="Abrir produto na WeDrop" className="text-muted hover:text-accent">
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                  <div className="mt-1 text-[10px] text-muted">SKU: {product.sku || '—'}</div>
                </td>
                <td className="px-3 py-3">{product.category || '—'}</td>
                <td className="px-3 py-3 font-semibold">{product.situation}</td>
                <td className="px-3 py-3 text-right">
                  {product.previousStock === null ? '—' : formatInt(product.previousStock)}
                  {' → '}
                  {product.currentStock === null ? '—' : formatInt(product.currentStock)}
                  {' un.'}
                </td>
                <td className="px-3 py-3 text-right font-bold">
                  {formatInt(product.unitsSoldLast7Days)} un.
                </td>
                <td className="whitespace-nowrap px-3 py-3">{formatDateTimeBR(product.lastSaleAt)}</td>
                <td className="whitespace-nowrap px-3 py-3 text-right">{formatCurrency(product.price)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
    <div className="flex items-center justify-between border-t border-theme px-4 py-3 text-xs text-muted">
      <span>{formatInt(matchingProducts.length)} produtos monitorados</span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage((current) => Math.max(1, current - 1))}
          className="rounded border border-theme px-2.5 py-1 disabled:opacity-40"
        >
          Anterior
        </button>
        <span>{page} / {totalPages}</span>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
          className="rounded border border-theme px-2.5 py-1 disabled:opacity-40"
        >
          Próxima
        </button>
      </div>
    </div>
  </div>
  );
};
