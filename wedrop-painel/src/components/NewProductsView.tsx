import React, { useMemo, useState } from 'react';
import { ExternalLink, Search, Sparkles } from 'lucide-react';
import { NewProductsData, NewProductWithSales, ProductRecord } from '../types/wedrop';
import { formatCurrency, formatDateTimeBR, formatInt } from '../utils/status';

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

  const totalPages = Math.max(1, Math.ceil(filteredProducts.length / PAGE_SIZE));
  const paginatedProducts = filteredProducts.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <section className="space-y-5 mb-8">
      <div className="flex flex-col gap-3 rounded-xl border border-theme bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-emerald-500" />
            <h2 className="text-lg font-bold text-theme">Novos produtos disponíveis</h2>
          </div>
          <p className="mt-1 text-xs text-muted">
            Somente produtos disponíveis hoje. A primeira identificação é registrada pela coleta; para produtos anteriores à migração, a data pode ser aproximada (updated_at).
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
      </div>

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
                <th className="px-4 py-3">Produto</th>
                <th className="px-3 py-3">Categoria</th>
                <th className="px-3 py-3">Identificado em</th>
                <th className="px-3 py-3 text-right">Dias no catálogo</th>
                <th className="px-3 py-3 text-right">Vendido desde a entrada</th>
                <th className="px-3 py-3">Última venda</th>
                <th className="px-3 py-3 text-right">Preço</th>
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
