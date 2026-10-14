import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Search,
  ExternalLink,
  ChevronLeft,
  Info,
  BarChart2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import { CategorySummary, ProductWithActivity, ProductRecord } from '../types/wedrop';
import { formatInt, WITHOUT_STATUS_HELP } from '../utils/status';

interface CategoryDetailViewProps {
  category: CategorySummary;
  products: ProductWithActivity[];
  onBackToOverview: () => void;
  onSelectProductForDetails: (product: ProductRecord) => void;
}

type StatusFilter = 'Todos' | 'Disponível' | 'Indisponível' | 'Sem status';

export const CategoryDetailView: React.FC<CategoryDetailViewProps> = ({
  category,
  products,
  onBackToOverview,
  onSelectProductForDetails,
}) => {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('Todos');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const filteredProducts = products.filter((p) => {
    if (statusFilter === 'Disponível' && p.status_bucket !== 'Ativos') {
      return false;
    }
    if (statusFilter === 'Indisponível' && p.status_bucket !== 'Inativos') {
      return false;
    }
    if (statusFilter === 'Sem status' && p.status_bucket !== 'Sem status') {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = p.name.toLowerCase().includes(q);
      const matchSku = p.sku?.toLowerCase().includes(q);
      const matchEan = p.ean?.toLowerCase().includes(q);
      const matchSupplier = p.supplier?.toLowerCase().includes(q);
      return matchName || matchSku || matchEan || matchSupplier;
    }
    return true;
  });

  const movedProducts = [...filteredProducts]
    .filter((p) => p.units_sold > 0 || p.units_restocked > 0)
    .sort((a, b) => b.units_sold - a.units_sold || b.units_restocked - a.units_restocked);

  const chartData = movedProducts.map((p) => ({
    name: p.name.length > 25 ? p.name.substring(0, 25) + '...' : p.name,
    fullName: p.name,
    'Unidades vendidas': p.units_sold,
    'Unidades repostas': p.units_restocked,
  }));

  const totalPages = Math.ceil(filteredProducts.length / pageSize) || 1;
  const paginatedProducts = filteredProducts.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="space-y-6 mb-8">
      {/* Category Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-4 rounded-xl border border-theme">
        <div>
          <button
            onClick={onBackToOverview}
            className="inline-flex items-center gap-1 text-xs text-muted hover:text-accent mb-1 font-semibold transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Voltar para visão geral</span>
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-theme">{category.name}</h1>
            {category.category_url && (
              <a
                href={category.category_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-accent hover:underline flex items-center gap-1 font-bold"
              >
                <span>Ver no WeDrop</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>

        {/* Status mini summary metrics */}
        <div className="flex items-center gap-2 sm:gap-4">
          <div className="text-center px-3 py-1.5 bg-card-secondary rounded-lg border border-theme">
            <div className="text-xs text-emerald-600 dark:text-emerald-400 font-bold">Disponíveis</div>
            <div className="text-lg font-bold text-theme">{category.active_products}</div>
          </div>
          <div className="text-center px-3 py-1.5 bg-card-secondary rounded-lg border border-theme">
            <div className="text-xs text-muted font-bold">Indisponíveis</div>
            <div className="text-lg font-bold text-theme">{category.inactive_products}</div>
          </div>
          <div
            className="text-center px-3 py-1.5 bg-card-secondary rounded-lg border border-theme cursor-help"
            title={WITHOUT_STATUS_HELP}
          >
            <div className="text-xs text-amber-600 dark:text-amber-400 font-bold flex items-center gap-1 justify-center">
              <span>Sem status</span>
              <Info className="w-3 h-3" />
            </div>
            <div className="text-lg font-bold text-theme">{category.products_without_status}</div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-card p-4 rounded-xl border border-theme flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Status Filter Radio Pills */}
        <div className="flex items-center gap-1 bg-card-secondary p-1 rounded-lg border border-theme">
          {(['Todos', 'Disponível', 'Indisponível', 'Sem status'] as StatusFilter[]).map((tab) => (
            <button
              key={tab}
              onClick={() => {
                setStatusFilter(tab);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
                statusFilter === tab
                  ? 'bg-card text-theme shadow-2xs font-extrabold'
                  : 'text-muted hover:text-theme'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Buscar por nome, SKU, EAN..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-card-secondary border border-theme rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-hidden text-theme"
          />
        </div>
      </div>

      {/* Products Table */}
      <div className="bg-card rounded-xl border border-theme overflow-hidden shadow-2xs">
        <div className="p-4 border-b border-theme flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-theme">Produtos da Categoria</h2>
            <span className="text-xs bg-card-secondary text-muted px-2 py-0.5 rounded-full font-bold border border-theme">
              {filteredProducts.length} encontrados
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-card-secondary text-muted uppercase font-semibold border-b border-theme">
              <tr>
                <th className="px-3.5 py-2.5">Produto</th>
                <th className="px-3 py-2.5">SKU</th>
                <th className="px-3 py-2.5">Status</th>
                <th className="px-3 py-2.5">Preço</th>
                <th className="px-3 py-2.5 text-right text-accent font-bold">Vendido</th>
                <th className="px-3 py-2.5 text-right text-blue-600 dark:text-blue-400 font-bold">Reposto</th>
                <th className="px-3 py-2.5 text-right">Estoque</th>
                <th className="px-3 py-2.5 text-right">Saldo Real</th>
                <th className="px-3 py-2.5">Fornecedor</th>
                <th className="px-3 py-2.5 text-center">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-theme text-theme">
              {paginatedProducts.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-4 py-8 text-center text-muted">
                    Nenhum produto encontrado com os filtros selecionados.
                  </td>
                </tr>
              ) : (
                paginatedProducts.map((p) => {
                  const isAvailable = p.status_bucket === 'Ativos';
                  const isWithout = p.status_bucket === 'Sem status';

                  return (
                    <tr key={p.product_id} className="hover-bg transition-colors">
                      <td className="px-3.5 py-2.5 max-w-xs">
                        <button
                          type="button"
                          onClick={() => onSelectProductForDetails(p)}
                          className="text-left font-medium text-theme hover:text-accent line-clamp-2"
                        >
                          {p.name}
                        </button>
                      </td>
                      <td className="px-3 py-2.5 font-mono text-[11px] text-muted whitespace-nowrap">
                        {p.sku || '—'}
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap">
                        {isAvailable ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 dark:bg-emerald-950/40 dark:text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-300 dark:border-emerald-700">
                            <CheckCircle2 className="w-3 h-3" />
                            Disponível
                          </span>
                        ) : isWithout ? (
                          <span
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 dark:bg-amber-950/40 dark:text-amber-300 px-2 py-0.5 rounded-full border border-amber-300 dark:border-amber-700"
                            title={WITHOUT_STATUS_HELP}
                          >
                            <AlertCircle className="w-3 h-3" />
                            Sem status
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-muted bg-card-secondary px-2 py-0.5 rounded-full border border-theme">
                            <XCircle className="w-3 h-3" />
                            Indisponível
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 font-bold text-theme whitespace-nowrap">
                        {p.price || '—'}
                      </td>
                      <td className="px-3 py-2.5 text-right font-black text-accent whitespace-nowrap">
                        {p.units_sold > 0 ? formatInt(p.units_sold) : '—'}
                      </td>
                      <td className="px-3 py-2.5 text-right font-black text-blue-600 dark:text-blue-400 whitespace-nowrap">
                        {p.units_restocked > 0 ? formatInt(p.units_restocked) : '—'}
                      </td>
                      <td className="px-3 py-2.5 text-right text-theme whitespace-nowrap">
                        {p.stock ?? '0'}
                      </td>
                      <td className="px-3 py-2.5 text-right font-medium text-theme whitespace-nowrap">
                        {p.real_balance ?? '0'}
                      </td>
                      <td className="px-3 py-2.5 text-muted whitespace-nowrap max-w-[140px] truncate" title={p.supplier || ''}>
                        {p.supplier || '—'}
                      </td>
                      <td className="px-3 py-2.5 text-center whitespace-nowrap">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            type="button"
                            onClick={() => onSelectProductForDetails(p)}
                            className="text-muted hover:text-theme text-[11px] font-medium"
                          >
                            Ficha
                          </button>
                          <a
                            href={p.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-0.5 text-accent hover:opacity-80 text-[11px] font-bold"
                            title="Abrir no WeDrop"
                          >
                            <span>Loja</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-3 border-t border-theme flex items-center justify-between text-xs text-muted">
            <span>
              Página {page} de {totalPages} ({filteredProducts.length} itens)
            </span>
            <div className="flex items-center gap-1">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-2.5 py-1 border border-theme rounded disabled:opacity-40 hover-bg"
              >
                Anterior
              </button>
              <button
                disabled={page === totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="px-2.5 py-1 border border-theme rounded disabled:opacity-40 hover-bg"
              >
                Próxima
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Chart: Vendas e Reposições por produto */}
      <div className="bg-card p-5 rounded-xl border border-theme shadow-2xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-theme flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-accent" />
              <span>Vendas e Reposições por Produto ({category.name})</span>
            </h2>
            <p className="text-xs text-muted">
              {movedProducts.length > 0
                ? `${movedProducts.length} produtos com movimentação no período.`
                : 'Nenhum produto deste filtro teve movimentação no período selecionado.'}
            </p>
          </div>
        </div>

        {chartData.length > 0 ? (
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.2} />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value, name) => [`${value} unidades`, name]}
                  labelFormatter={(_label, payload) => {
                    const row = payload?.[0]?.payload;
                    return row ? row.fullName : _label;
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="Unidades vendidas" fill="var(--accent-color)" radius={[0, 4, 4, 0]} />
                <Bar dataKey="Unidades repostas" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="py-12 text-center text-xs text-muted bg-card-secondary rounded-lg border border-theme">
            Sem registros de venda ou reposição nesta categoria no período selecionado.
          </div>
        )}
      </div>
    </div>
  );
};
