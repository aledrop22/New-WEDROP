import React, { useState } from 'react';
import {
  TrendingUp,
  BarChart3,
  Award,
  Calendar,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import {
  DailyActivityRow,
  CategorySummary,
  TopProductDailyRow,
  ProductRecord,
} from '../types/wedrop';
import { formatInt } from '../utils/status';

interface OverviewChartsProps {
  dailyActivity: DailyActivityRow[];
  categorySummaries: CategorySummary[];
  topProductsOverall: (ProductRecord & { units_sold: number })[];
  topProductsDaily: TopProductDailyRow[];
  onSelectCategory: (name: string) => void;
  onSelectProductForDetails: (product: ProductRecord) => void;
}

export const OverviewCharts: React.FC<OverviewChartsProps> = ({
  dailyActivity,
  categorySummaries,
  topProductsOverall,
  topProductsDaily,
  onSelectCategory,
  onSelectProductForDetails,
}) => {
  const [showAllDailyProducts, setShowAllDailyProducts] = useState(false);

  // Categories moved
  const movedCategories = [...categorySummaries]
    .filter((c) => c.units_sold > 0 || c.units_restocked > 0)
    .sort((a, b) => b.units_sold - a.units_sold || b.units_restocked - a.units_restocked);

  const categoryChartData = movedCategories.map((c) => ({
    name: c.name,
    Vendas: c.units_sold,
    Reposição: c.units_restocked,
  }));

  // Top 20 best sellers chart data
  const top20ChartData = topProductsOverall.slice(0, 20).map((p) => ({
    name: p.name.length > 22 ? p.name.substring(0, 22) + '...' : p.name,
    fullName: p.name,
    'Unidades vendidas': p.units_sold,
  }));

  // Days list for daily matrix
  const daysList = dailyActivity.map((d) => d.day);
  const displayedDailyProducts = showAllDailyProducts
    ? topProductsDaily
    : topProductsDaily.slice(0, 20);

  return (
    <div className="space-y-8 mb-12">
      {/* 1. Movimentações por dia (Line chart) */}
      <div className="bg-card p-5 rounded-xl border border-theme shadow-2xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-theme flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-accent" />
              <span>Movimentações Históricas por Dia</span>
            </h2>
            <p className="text-xs text-muted">
              Volume diário de vendas e reposições de estoque ao longo do período selecionado.
            </p>
          </div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={dailyActivity}
              margin={{ top: 10, right: 30, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis dataKey="dayLabel" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(val, name) => [`${val} unidades`, name]}
                labelFormatter={(label) => `Data: ${label}`}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Line
                type="monotone"
                dataKey="units_sold"
                name="Vendas"
                stroke="var(--accent-color)"
                strokeWidth={2.5}
                dot={{ r: 3 }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="units_restocked"
                name="Reposição"
                stroke="#3b82f6"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Movimentações por categoria (Bar chart) */}
      <div className="bg-card p-5 rounded-xl border border-theme shadow-2xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-theme flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-accent" />
              <span>Movimentações por Categoria</span>
            </h2>
            <p className="text-xs text-muted">
              Comparativo de volume faturado e reposições entre as categorias ativas.
            </p>
          </div>
        </div>

        {categoryChartData.length > 0 ? (
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={categoryChartData}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.2} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value, name) => [`${value} un.`, name]} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="Vendas" fill="var(--accent-color)" radius={[0, 4, 4, 0]} />
                <Bar dataKey="Reposição" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="py-12 text-center text-xs text-muted bg-card-secondary rounded-lg border border-theme">
            Nenhuma categoria teve movimentação no período selecionado.
          </div>
        )}
      </div>

      {/* 3. 20 Produtos Mais Vendidos no Período */}
      <div className="bg-card p-5 rounded-xl border border-theme shadow-2xs space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-theme flex items-center gap-2">
              <Award className="w-4 h-4 text-amber-500" />
              <span>20 Produtos Mais Vendidos no Período</span>
            </h2>
            <p className="text-xs text-muted">
              Ranking dos produtos líderes de saída e demanda no catálogo WeDrop.
            </p>
          </div>
        </div>

        {top20ChartData.length > 0 ? (
          <>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={top20ChartData}
                  margin={{ top: 10, right: 20, left: 10, bottom: 40 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
                  <XAxis
                    dataKey="name"
                    interval={0}
                    angle={-30}
                    textAnchor="end"
                    tick={{ fontSize: 10 }}
                    height={60}
                  />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(val, name) => [`${val} unidades`, name]}
                    labelFormatter={(_label, payload) => payload?.[0]?.payload?.fullName || _label}
                  />
                  <Bar dataKey="Unidades vendidas" fill="var(--accent-color)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Table Top 20 */}
            <div className="overflow-x-auto border border-theme rounded-lg">
              <table className="w-full text-xs text-left">
                <thead className="bg-card-secondary text-muted uppercase font-semibold border-b border-theme">
                  <tr>
                    <th className="px-3 py-2 text-center w-12">#</th>
                    <th className="px-3.5 py-2">Produto</th>
                    <th className="px-3 py-2">Categoria</th>
                    <th className="px-3 py-2">SKU</th>
                    <th className="px-3 py-2 text-right text-accent font-bold">Unidades Vendidas</th>
                    <th className="px-3 py-2 text-center">WeDrop</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-theme text-theme">
                  {topProductsOverall.slice(0, 20).map((p, idx) => (
                    <tr key={p.product_id} className="hover-bg transition-colors">
                      <td className="px-3 py-2 text-center font-bold text-muted">
                        {idx + 1}º
                      </td>
                      <td className="px-3.5 py-2 font-medium text-theme max-w-sm truncate" title={p.name}>
                        <button
                          type="button"
                          onClick={() => onSelectProductForDetails(p)}
                          className="hover:text-accent text-left"
                        >
                          {p.name}
                        </button>
                      </td>
                      <td className="px-3 py-2 text-muted">
                        <button
                          type="button"
                          onClick={() => onSelectCategory(p.category)}
                          className="text-muted hover:text-accent underline font-medium"
                        >
                          {p.category}
                        </button>
                      </td>
                      <td className="px-3 py-2 font-mono text-[11px] text-muted">
                        {p.sku || '—'}
                      </td>
                      <td className="px-3 py-2 text-right font-bold text-accent">
                        {formatInt(p.units_sold)}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <a
                          href={p.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-accent hover:opacity-80 font-bold text-[11px]"
                        >
                          <span>Abrir</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="py-8 text-center text-xs text-muted bg-card-secondary rounded-lg border border-theme">
            Não houve vendas registradas no período selecionado.
          </div>
        )}
      </div>

      {/* 4. Tabela de Matriz Diária: Produtos com mais movimentação (Volume por dia) */}
      <div className="bg-card p-5 rounded-xl border border-theme shadow-2xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-theme flex items-center gap-2">
              <Calendar className="w-4 h-4 text-blue-500" />
              <span>Produtos com Mais Movimentação: Volume Diário</span>
            </h2>
            <p className="text-xs text-muted">
              Colunas por dia mostram as unidades vendidas naquele dia; Vendido e Reposto somam o período.
            </p>
          </div>
          {topProductsDaily.length > 20 && (
            <button
              onClick={() => setShowAllDailyProducts(!showAllDailyProducts)}
              className="text-xs text-muted hover:text-theme flex items-center gap-1 font-bold bg-card-secondary border border-theme px-2.5 py-1.5 rounded-md self-start sm:self-auto transition-colors"
            >
              <span>{showAllDailyProducts ? 'Exibir apenas 20' : `Exibir todos (${topProductsDaily.length})`}</span>
              {showAllDailyProducts ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>

        {topProductsDaily.length > 0 ? (
          <div className="overflow-x-auto border border-theme rounded-lg max-h-96">
            <table className="w-full text-xs text-left">
              <thead className="bg-card-secondary text-muted uppercase font-semibold border-b border-theme sticky top-0 z-10">
                <tr>
                  <th className="px-3.5 py-2.5 min-w-[200px]">Produto</th>
                  <th className="px-3 py-2.5">Categoria</th>
                  <th className="px-3 py-2.5 text-right text-accent font-bold whitespace-nowrap">Vendido</th>
                  <th className="px-3 py-2.5 text-right text-blue-600 dark:text-blue-400 font-bold whitespace-nowrap">Reposto</th>
                  {daysList.map((day) => (
                    <th key={day} className="px-2.5 py-2.5 text-center font-mono whitespace-nowrap bg-card-secondary">
                      {day.substring(8, 10)}/{day.substring(5, 7)}
                    </th>
                  ))}
                  <th className="px-3 py-2.5 text-center">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-theme text-theme">
                {displayedDailyProducts.map((p) => (
                  <tr key={p.product_id} className="hover-bg transition-colors">
                    <td className="px-3.5 py-2 font-medium text-theme truncate max-w-xs" title={p.name}>
                      {p.name}
                    </td>
                    <td className="px-3 py-2 text-muted whitespace-nowrap">{p.category}</td>
                    <td className="px-3 py-2 text-right font-bold text-accent whitespace-nowrap">
                      {formatInt(p.total_sold)}
                    </td>
                    <td className="px-3 py-2 text-right font-bold text-blue-600 dark:text-blue-400 whitespace-nowrap">
                      {formatInt(p.total_restocked)}
                    </td>
                    {daysList.map((day) => {
                      const qty = p.daily_sales[day] || 0;
                      return (
                        <td
                          key={day}
                          className={`px-2.5 py-2 text-center font-mono text-[11px] ${
                            qty > 0 ? 'bg-accent/10 text-accent font-bold' : 'text-muted/40'
                          }`}
                        >
                          {qty > 0 ? qty : '0'}
                        </td>
                      );
                    })}
                    <td className="px-3 py-2 text-center whitespace-nowrap">
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-accent hover:opacity-80 font-bold inline-flex items-center gap-0.5"
                      >
                        <span>Abrir</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-muted bg-card-secondary rounded-lg border border-theme">
            Nenhum produto teve movimentação no período selecionado.
          </div>
        )}
      </div>
    </div>
  );
};
