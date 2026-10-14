import React, { useState } from 'react';
import { Tag, ArrowDownRight, ArrowUpRight, ExternalLink, Search } from 'lucide-react';
import { ProductPriceComparison } from '../types/wedrop';
import { formatCurrency } from '../utils/status';

interface PriceFluctuationViewProps {
  priceChangesUp: ProductPriceComparison[];
  priceChangesDown: ProductPriceComparison[];
  onSelectCategory: (name: string) => void;
}

export const PriceFluctuationView: React.FC<PriceFluctuationViewProps> = ({
  priceChangesUp,
  priceChangesDown,
  onSelectCategory,
}) => {
  const [filterType, setFilterType] = useState<'all' | 'down' | 'up'>('all');
  const [search, setSearch] = useState('');

  const allItems = [
    ...priceChangesDown.map((i) => ({ ...i, type: 'down' as const })),
    ...priceChangesUp.map((i) => ({ ...i, type: 'up' as const })),
  ];

  const filtered = allItems.filter((item) => {
    if (filterType === 'down' && item.type !== 'down') return false;
    if (filterType === 'up' && item.type !== 'up') return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        item.product.name.toLowerCase().includes(q) ||
        item.product.category.toLowerCase().includes(q) ||
        item.product.sku?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Intro Header */}
      <div className="bg-card border border-theme rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Tag className="w-5 h-5 text-accent" />
              <h2 className="text-xl font-bold text-theme">
                Auditoria de Preços: Produtos que Subiram e Desceram
              </h2>
            </div>
            <p className="text-xs text-muted max-w-2xl">
              Comparativo automático de preços capturado pela rotina noturna do scraper. Identifique reduções de preço dos fornecedores para aumentar sua margem e aumentos de custo para reajustar na sua loja.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="text-center px-3 py-1.5 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg border border-emerald-200 dark:border-emerald-800">
              <span className="text-[10px] text-emerald-700 dark:text-emerald-400 font-bold block">Baixaram Preço</span>
              <span className="text-lg font-black text-emerald-600 dark:text-emerald-400">{priceChangesDown.length} itens</span>
            </div>
            <div className="text-center px-3 py-1.5 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-800">
              <span className="text-[10px] text-amber-700 dark:text-amber-400 font-bold block">Subiram Preço</span>
              <span className="text-lg font-black text-amber-600 dark:text-amber-400">{priceChangesUp.length} itens</span>
            </div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-card border border-theme rounded-xl p-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 bg-card-secondary p-1 rounded-lg border border-theme">
          <button
            onClick={() => setFilterType('all')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              filterType === 'all'
                ? 'bg-card text-theme shadow-2xs font-bold'
                : 'text-muted hover:text-theme'
            }`}
          >
            Todos ({allItems.length})
          </button>
          <button
            onClick={() => setFilterType('down')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1 ${
              filterType === 'down'
                ? 'bg-card text-emerald-600 dark:text-emerald-400 shadow-2xs font-bold'
                : 'text-muted hover:text-theme'
            }`}
          >
            <ArrowDownRight className="w-3.5 h-3.5 text-emerald-500" />
            <span>Baixaram ({priceChangesDown.length})</span>
          </button>
          <button
            onClick={() => setFilterType('up')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1 ${
              filterType === 'up'
                ? 'bg-card text-amber-600 dark:text-amber-400 shadow-2xs font-bold'
                : 'text-muted hover:text-theme'
            }`}
          >
            <ArrowUpRight className="w-3.5 h-3.5 text-amber-500" />
            <span>Subiram ({priceChangesUp.length})</span>
          </button>
        </div>

        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Buscar por produto, SKU, categoria..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-card-secondary border border-theme rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-hidden text-theme"
          />
        </div>
      </div>

      {/* Comparison Table */}
      <div className="bg-card border border-theme rounded-xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-card-secondary text-muted uppercase font-semibold border-b border-theme">
              <tr>
                <th className="px-3.5 py-2.5">Produto</th>
                <th className="px-3 py-2.5">Categoria</th>
                <th className="px-3 py-2.5">SKU</th>
                <th className="px-3 py-2.5 text-right">Preço Anterior</th>
                <th className="px-3 py-2.5 text-right font-bold text-theme">Preço Atual</th>
                <th className="px-3 py-2.5 text-right">Diferença (R$)</th>
                <th className="px-3 py-2.5 text-center">Variação (%)</th>
                <th className="px-3 py-2.5">Recomendação</th>
                <th className="px-3 py-2.5 text-center">Link Direto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-theme text-theme">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-muted">
                    Nenhum produto encontrado com os filtros selecionados.
                  </td>
                </tr>
              ) : (
                filtered.map((item) => {
                  const isDrop = item.direction === 'down';
                  const isRise = item.direction === 'up';

                  return (
                    <tr key={item.product.product_id} className="hover-bg transition-colors">
                      <td className="px-3.5 py-2.5 max-w-sm">
                        <div className="font-semibold text-theme line-clamp-1" title={item.product.name}>
                          {item.product.name}
                        </div>
                        <div className="text-[10px] text-muted">
                          Fornecedor: {item.product.supplier || '—'}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap">
                        <button
                          onClick={() => onSelectCategory(item.product.category)}
                          className="text-muted hover:text-accent font-medium"
                        >
                          {item.product.category}
                        </button>
                      </td>
                      <td className="px-3 py-2.5 font-mono text-[11px] text-muted whitespace-nowrap">
                        {item.product.sku || '—'}
                      </td>
                      <td className="px-3 py-2.5 text-right text-muted line-through whitespace-nowrap">
                        {formatCurrency(item.previousPriceNum)}
                      </td>
                      <td className="px-3 py-2.5 text-right font-bold text-theme whitespace-nowrap text-sm">
                        {formatCurrency(item.currentPriceNum)}
                      </td>
                      <td className="px-3 py-2.5 text-right font-bold whitespace-nowrap">
                        <span
                          className={
                            isDrop
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : isRise
                              ? 'text-amber-600 dark:text-amber-400'
                              : 'text-muted'
                          }
                        >
                          {isDrop ? '-' : '+'}
                          {formatCurrency(Math.abs(item.diff))}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-center whitespace-nowrap">
                        {isDrop ? (
                          <span className="inline-flex items-center gap-0.5 text-[11px] font-bold text-emerald-700 bg-emerald-100 dark:bg-emerald-950/40 dark:text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-300 dark:border-emerald-700">
                            <ArrowDownRight className="w-3.5 h-3.5" />
                            {item.percentChange.toFixed(1)}%
                          </span>
                        ) : isRise ? (
                          <span className="inline-flex items-center gap-0.5 text-[11px] font-bold text-amber-700 bg-amber-100 dark:bg-amber-950/40 dark:text-amber-300 px-2 py-0.5 rounded-full border border-amber-300 dark:border-amber-700">
                            <ArrowUpRight className="w-3.5 h-3.5" />
                            +{item.percentChange.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-muted">0%</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-[11px]">
                        {isDrop ? (
                          <span className="text-emerald-700 dark:text-emerald-400 font-medium">
                            Ganho de margem / criar oferta
                          </span>
                        ) : (
                          <span className="text-amber-700 dark:text-amber-400 font-medium">
                            Ajustar preço de venda na loja
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-center whitespace-nowrap">
                        <a
                          href={item.product.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-accent hover:opacity-80 font-bold text-[11px] bg-card px-2.5 py-1 rounded border border-theme shadow-2xs"
                        >
                          <span>Abrir na Loja</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
