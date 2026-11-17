import React, { useState } from 'react';
import {
  TrendingUp,
  Package,
  ArrowUp,
  ArrowDown,
  Minus,
  ExternalLink,
  Layers,
  ChevronDown,
  ChevronUp,
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
import { Category24hComparison, Product24hStats } from '../types/wedrop';
import { formatInt } from '../utils/status';
import { SortableTableHeader, nextTableSort, sortTableRows, TableSortState } from './SortableTableHeader';

interface DayComparisonViewProps {
  categoriesComparison: Category24hComparison[];
  soldProducts: Product24hStats[];
  onSelectCategory: (name: string) => void;
}

export const DayComparisonView: React.FC<DayComparisonViewProps> = ({
  categoriesComparison,
  soldProducts,
  onSelectCategory,
}) => {
  const [sortState, setSortState] = useState<TableSortState | null>(null);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const productsByCategory = new Map<string, { yesterday: Product24hStats[]; today: Product24hStats[] }>();
  for (const product of soldProducts) {
    const categoryProducts = productsByCategory.get(product.category) || { yesterday: [], today: [] };
    if (product.salesYesterday > 0) categoryProducts.yesterday.push(product);
    if (product.salesToday > 0) categoryProducts.today.push(product);
    productsByCategory.set(product.category, categoryProducts);
  }
  const soldBreakdown = (categoryName: string) => {
    const categoryProducts = productsByCategory.get(categoryName) || { yesterday: [], today: [] };
    const yesterdayIds = new Set(categoryProducts.yesterday.map((product) => product.product_id));
    const todayIds = new Set(categoryProducts.today.map((product) => product.product_id));
    return {
      ...categoryProducts,
      repeated: categoryProducts.today.filter((product) => yesterdayIds.has(product.product_id)),
      onlyYesterday: categoryProducts.yesterday.filter((product) => !todayIds.has(product.product_id)),
      onlyToday: categoryProducts.today.filter((product) => !yesterdayIds.has(product.product_id)),
    };
  };
  const handleSort = (key: string) => setSortState((current) => nextTableSort(current, key));
  const sortedCategories = sortTableRows(categoriesComparison, sortState, (category, key) => {
    switch (key) {
      case 'name': return category.name;
      case 'items_yesterday': return category.itemsCountYesterday;
      case 'items_today': return category.itemsCountToday;
      case 'items_diff': return category.itemsDiff;
      case 'sold_products': {
        const breakdown = soldBreakdown(category.name);
        return breakdown.repeated.length + breakdown.onlyYesterday.length + breakdown.onlyToday.length;
      }
      case 'restock': return category.restockToday;
      default: return null;
    }
  });

  // Chart data for categories sales comparison (Ontem vs Hoje)
  const salesChartData = categoriesComparison.map((c) => ({
    name: c.name,
    'Vendas Ontem': c.salesYesterday,
    'Vendas Hoje': c.salesToday,
  }));

  // Chart data for active catalog item counts by category
  const itemsCountChartData = categoriesComparison.map((c) => ({
    name: c.name,
    'Ativos Ontem': c.itemsCountYesterday,
    'Ativos Hoje': c.itemsCountToday,
  }));

  return (
    <div className="space-y-6">
      {/* Overview Intro */}
      <div className="bg-card border border-theme rounded-xl p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <Layers className="w-5 h-5 text-accent" />
          <h2 className="text-xl font-bold text-theme">
            Comparativo Dia contra Dia (Ontem vs Hoje / D-1 vs D0)
          </h2>
        </div>
        <p className="text-xs text-muted max-w-3xl">
          Auditoria comparativa das 14 categorias do catálogo WeDrop. Analise se a quantidade de produtos ativos aumentou (novos produtos ou reposição) ou diminuiu (esgotamento de estoque), além do comparativo direto de vendas diárias.
        </p>
      </div>

      {/* 1. Gráfico e Tabela de Quantidade de Itens por Categoria */}
      <div className="bg-card border border-theme rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-theme pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Package className="w-5 h-5 text-blue-500" />
              <h3 className="text-base font-bold text-theme">
                Variação de Itens no Catálogo por Categoria
              </h3>
            </div>
            <p className="text-xs text-muted">
              Produtos ativos no catálogo ontem e hoje. A coluna de itens vendidos conta produtos distintos com venda em cada dia.
            </p>
          </div>
        </div>

        {/* Grouped Bar Chart: Itens Ontem vs Itens Hoje */}
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={itemsCountChartData} margin={{ top: 10, right: 20, left: 0, bottom: 35 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
              <XAxis dataKey="name" angle={-25} textAnchor="end" tick={{ fontSize: 10 }} height={45} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(val, name) => [`${val} produtos`, name]} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar dataKey="Ativos Ontem" fill="#94a3b8" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Ativos Hoje" fill="#3b82f6" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Table of Catalog Variations */}
        <div className="overflow-x-auto border border-theme rounded-lg">
          <table className="w-full text-xs text-left">
            <thead className="bg-card-secondary text-muted uppercase font-semibold border-b border-theme">
              <tr>
                <SortableTableHeader sortKey="name" sortState={sortState} onSort={handleSort} className="px-3.5 py-2.5">Categoria</SortableTableHeader>
                <SortableTableHeader sortKey="items_yesterday" sortState={sortState} onSort={handleSort} align="right" className="px-3 py-2.5">Produtos ativos ontem</SortableTableHeader>
                <SortableTableHeader sortKey="items_today" sortState={sortState} onSort={handleSort} align="right" className="px-3 py-2.5 font-bold text-theme">Produtos ativos hoje</SortableTableHeader>
                <SortableTableHeader sortKey="items_diff" sortState={sortState} onSort={handleSort} align="center" className="px-3 py-2.5">Variação Líquida</SortableTableHeader>
                <SortableTableHeader sortKey="sold_products" sortState={sortState} onSort={handleSort} className="px-3 py-2.5">Produtos vendidos (distintos)</SortableTableHeader>
                <SortableTableHeader sortKey="restock" sortState={sortState} onSort={handleSort} align="right" className="px-3 py-2.5 text-blue-600 dark:text-blue-400">Reposições Hoje</SortableTableHeader>
                <th className="px-3 py-2.5 text-center">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-theme text-theme">
              {sortedCategories.map((c) => {
                const diff = c.itemsDiff;
                const isUp = diff > 0;
                const isDown = diff < 0;
                const breakdown = soldBreakdown(c.name);
                const soldProductDiff = breakdown.today.length - breakdown.yesterday.length;
                const expanded = expandedCategory === c.name;
                const detailGroups = [
                  { title: `Venderam nos dois dias (${breakdown.repeated.length})`, products: breakdown.repeated },
                  { title: `Só ontem (${breakdown.onlyYesterday.length})`, products: breakdown.onlyYesterday },
                  { title: `Só hoje (${breakdown.onlyToday.length})`, products: breakdown.onlyToday },
                ];

                return (
                  <React.Fragment key={c.name}>
                    <tr className="hover-bg transition-colors">
                      <td className="px-3.5 py-2.5 font-bold text-theme">{c.name}</td>
                      <td className="px-3 py-2.5 text-right text-muted">{c.itemsCountYesterday}</td>
                      <td className="px-3 py-2.5 text-right font-bold text-theme">{c.itemsCountToday}</td>
                      <td className="px-3 py-2.5 text-center whitespace-nowrap">
                        {isUp ? (
                          <span className="inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400 font-bold">
                            <ArrowUp className="w-3.5 h-3.5" /> +{diff}
                          </span>
                        ) : isDown ? (
                          <span className="inline-flex items-center gap-0.5 text-red-500 font-bold">
                            <ArrowDown className="w-3.5 h-3.5" /> {diff}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-0.5 text-muted">
                            <Minus className="w-3.5 h-3.5" /> 0
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="whitespace-nowrap font-semibold text-theme">
                          Ontem {formatInt(breakdown.yesterday.length)} · Hoje {formatInt(breakdown.today.length)}
                          <span className={`ml-2 ${soldProductDiff > 0 ? 'text-emerald-600 dark:text-emerald-400' : soldProductDiff < 0 ? 'text-red-500' : 'text-muted'}`}>
                            ({soldProductDiff > 0 ? '+' : ''}{formatInt(soldProductDiff)})
                          </span>
                        </div>
                        <div className="mt-1 text-[10px] text-muted">
                          Repetiram {formatInt(breakdown.repeated.length)} · Só ontem {formatInt(breakdown.onlyYesterday.length)} · Só hoje {formatInt(breakdown.onlyToday.length)}
                        </div>
                        <button
                          type="button"
                          aria-expanded={expanded}
                          onClick={() => setExpandedCategory(expanded ? null : c.name)}
                          className="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold text-accent hover:underline"
                        >
                          {expanded ? 'Ocultar produtos' : 'Ver produtos'}
                          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                        </button>
                      </td>
                      <td className="px-3 py-2.5 text-right font-bold text-blue-600 dark:text-blue-400">
                        {c.restockToday > 0 ? `+${formatInt(c.restockToday)} un.` : '—'}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <button
                          onClick={() => onSelectCategory(c.name)}
                          className="text-xs text-accent font-semibold hover:underline"
                        >
                          Filtrar
                        </button>
                      </td>
                    </tr>
                    {expanded && (
                      <tr className="bg-card-secondary/60">
                        <td colSpan={7} className="px-4 py-4">
                          <div className="grid gap-4 md:grid-cols-3">
                            {detailGroups.map((group) => (
                              <section key={group.title} className="min-w-0">
                                <h4 className="mb-2 text-xs font-bold text-theme">{group.title}</h4>
                                {group.products.length === 0 ? (
                                  <p className="text-xs text-muted">Nenhum produto neste grupo.</p>
                                ) : (
                                  <ul className="max-h-64 space-y-1 overflow-y-auto">
                                    {[...group.products]
                                      .sort((a, b) => b.salesToday + b.salesYesterday - a.salesToday - a.salesYesterday)
                                      .map((product) => (
                                        <li key={product.product_id} className="flex items-start justify-between gap-3 text-xs">
                                          <a
                                            href={product.url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex min-w-0 items-center gap-1 text-accent hover:underline"
                                            title={`Abrir ${product.name} na WeDrop`}
                                          >
                                            <span className="truncate">{product.name}</span>
                                            <ExternalLink className="h-3 w-3 shrink-0" />
                                          </a>
                                          <span className="shrink-0 text-muted">
                                            {formatInt(product.salesYesterday)} un. ontem · {formatInt(product.salesToday)} un. hoje
                                          </span>
                                        </li>
                                      ))}
                                  </ul>
                                )}
                              </section>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. Comparativo de Vendas Dia a Dia por Categoria */}
      <div className="bg-card border border-theme rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex items-center gap-2 border-b border-theme pb-3">
          <TrendingUp className="w-5 h-5 text-accent" />
          <div>
            <h3 className="text-base font-bold text-theme">
              Comparativo de Volume de Vendas: Ontem vs Hoje por Categoria
            </h3>
            <p className="text-xs text-muted">
              Gráfico de barras lado a lado mostrando o faturamento comparativo das últimas 24 horas.
            </p>
          </div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={salesChartData} margin={{ top: 10, right: 20, left: 0, bottom: 35 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
              <XAxis dataKey="name" angle={-25} textAnchor="end" tick={{ fontSize: 10 }} height={45} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(val, name) => [`${val} unidades vendidas`, name]} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar dataKey="Vendas Ontem" fill="#94a3b8" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Vendas Hoje" fill="var(--accent-color)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
