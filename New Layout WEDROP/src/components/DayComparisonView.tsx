import React from 'react';
import {
  TrendingUp,
  Package,
  ArrowUp,
  ArrowDown,
  Minus,
  ExternalLink,
  Layers,
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

interface DayComparisonViewProps {
  categoriesComparison: Category24hComparison[];
  topProducts: Product24hStats[];
  onSelectCategory: (name: string) => void;
}

export const DayComparisonView: React.FC<DayComparisonViewProps> = ({
  categoriesComparison,
  topProducts,
  onSelectCategory,
}) => {
  // Chart data for categories sales comparison (Ontem vs Hoje)
  const salesChartData = categoriesComparison.map((c) => ({
    name: c.name,
    'Vendas Ontem': c.salesYesterday,
    'Vendas Hoje': c.salesToday,
  }));

  // Chart data for categories catalog item count comparison
  const itemsCountChartData = categoriesComparison.map((c) => ({
    name: c.name,
    'Produtos Ontem': c.itemsCountYesterday,
    'Produtos Hoje': c.itemsCountToday,
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
              Comparativo de quantos produtos ativos existiam ontem comparado com a leitura de hoje.
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
              <Bar dataKey="Produtos Ontem" fill="#94a3b8" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Produtos Hoje" fill="#3b82f6" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Table of Catalog Variations */}
        <div className="overflow-x-auto border border-theme rounded-lg">
          <table className="w-full text-xs text-left">
            <thead className="bg-card-secondary text-muted uppercase font-semibold border-b border-theme">
              <tr>
                <th className="px-3.5 py-2.5">Categoria</th>
                <th className="px-3 py-2.5 text-right">Produtos Ontem</th>
                <th className="px-3 py-2.5 text-right font-bold text-theme">Produtos Hoje</th>
                <th className="px-3 py-2.5 text-center">Variação Líquida</th>
                <th className="px-3 py-2.5">Diagnóstico da Variação</th>
                <th className="px-3 py-2.5 text-right text-blue-600 dark:text-blue-400">Reposições Hoje</th>
                <th className="px-3 py-2.5 text-center">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-theme text-theme">
              {categoriesComparison.map((c) => {
                const diff = c.itemsDiff;
                const isUp = diff > 0;
                const isDown = diff < 0;

                return (
                  <tr key={c.name} className="hover-bg transition-colors">
                    <td className="px-3.5 py-2.5 font-bold text-theme">
                      {c.name}
                    </td>
                    <td className="px-3 py-2.5 text-right text-muted">
                      {c.itemsCountYesterday}
                    </td>
                    <td className="px-3 py-2.5 text-right font-bold text-theme">
                      {c.itemsCountToday}
                    </td>
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
                      {c.itemsReason === 'new_products' ? (
                        <span className="text-emerald-700 dark:text-emerald-400 font-medium bg-emerald-50 dark:bg-emerald-950/30 px-2 py-0.5 rounded text-[11px] border border-emerald-200 dark:border-emerald-800">
                          Novos produtos adicionados
                        </span>
                      ) : c.itemsReason === 'restock' ? (
                        <span className="text-blue-700 dark:text-blue-400 font-medium bg-blue-50 dark:bg-blue-950/30 px-2 py-0.5 rounded text-[11px] border border-blue-200 dark:border-blue-800">
                          Reposição / Itens reativados
                        </span>
                      ) : c.itemsReason === 'out_of_stock' ? (
                        <span className="text-amber-700 dark:text-amber-400 font-medium bg-amber-50 dark:bg-amber-950/30 px-2 py-0.5 rounded text-[11px] border border-amber-200 dark:border-amber-800">
                          Estoque esgotado / Itens inativados
                        </span>
                      ) : (
                        <span className="text-muted text-[11px]">Estoque estável</span>
                      )}
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
