import React, { useState } from 'react';
import { CategorySummary } from '../types/wedrop';
import { formatInt } from '../utils/status';
import { Layers, CheckCircle2, XCircle, LayoutList, Columns } from 'lucide-react';

interface CategoryStripProps {
  categories: CategorySummary[];
  selectedCategory: string | null;
  onSelectCategory: (name: string | null) => void;
}

export const CategoryStrip: React.FC<CategoryStripProps> = ({
  categories,
  selectedCategory,
  onSelectCategory,
}) => {
  // Sort categories by units_sold desc
  const ranked = [...categories].sort((a, b) => b.units_sold - a.units_sold);

  // Layout mode for the cards: 'stacked' (1 embaixo do outro - default) or 'columns' (2 colunas)
  const [layoutMode, setLayoutMode] = useState<'stacked' | 'columns'>('stacked');

  return (
    <div className="mb-8 w-full">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-accent" />
            <h2 className="text-base sm:text-lg font-bold text-theme">
              Categorias do Depósito WeDrop
            </h2>
          </div>
          <p className="text-xs text-muted mt-0.5">
            14 categorias ranqueadas por saída com detalhamento de estoque (Disponível vs Indisponível).
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          {/* Layout mode switcher: Empilhado vs 2 Colunas */}
          <div className="flex items-center bg-card-secondary p-1 rounded-lg border border-theme text-xs">
            <button
              type="button"
              onClick={() => setLayoutMode('stacked')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors font-semibold ${
                layoutMode === 'stacked'
                  ? 'bg-card text-theme shadow-2xs font-bold'
                  : 'text-muted hover:text-theme'
              }`}
              title="Exibir Disponível e Indisponível empilhados (um embaixo do outro) para máxima legibilidade"
            >
              <LayoutList className="w-3.5 h-3.5" />
              <span>Empilhado (1 embaixo do outro)</span>
            </button>
            <button
              type="button"
              onClick={() => setLayoutMode('columns')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors font-semibold ${
                layoutMode === 'columns'
                  ? 'bg-card text-theme shadow-2xs font-bold'
                  : 'text-muted hover:text-theme'
              }`}
              title="Exibir Disponível e Indisponível em 2 colunas proporcionais"
            >
              <Columns className="w-3.5 h-3.5" />
              <span>2 Colunas</span>
            </button>
          </div>

          {selectedCategory && (
            <button
              onClick={() => onSelectCategory(null)}
              className="text-xs text-accent hover:underline font-bold px-2 py-1 bg-card rounded border border-theme"
            >
              Ver todas (limpar filtro)
            </button>
          )}
        </div>
      </div>

      <div className="wd-strip w-full">
        {ranked.map((cat, index) => {
          const position = index + 1;
          const isTop3 = position <= 3 && cat.units_sold > 0;
          const isTop5 = position <= 5 && cat.units_sold > 0;
          const isSelected = selectedCategory === cat.name;
          const totalProds = cat.expected_products ?? cat.mapped_products;

          const medalStyles = [
            'bg-amber-500 text-white shadow-xs', // 1st
            'bg-slate-400 text-white shadow-xs', // 2nd
            'bg-amber-700 text-white shadow-xs', // 3rd
          ];

          return (
            <button
              key={cat.name}
              type="button"
              onClick={() => onSelectCategory(isSelected ? null : cat.name)}
              className={`wd-card text-left transition-all cursor-pointer p-3 w-full flex flex-col justify-between ${
                isTop3
                  ? 'border-2 border-accent shadow-sm'
                  : isTop5
                  ? 'wd-card-top'
                  : ''
              } ${isSelected ? 'selected ring-2 ring-accent' : ''}`}
            >
              <div>
                {/* Ranking Medal */}
                {isTop3 ? (
                  <div className="text-center mb-1.5">
                    <span className={`wd-card-rank ${medalStyles[position - 1]}`}>
                      {position}º {position === 1 ? '🥇 Líder' : position === 2 ? '🥈 2º' : '🥉 3º'}
                    </span>
                  </div>
                ) : isTop5 ? (
                  <div className="text-center mb-1.5">
                    <span className="wd-card-rank bg-accent/80 text-white">{position}º Lugar</span>
                  </div>
                ) : (
                  <div className="text-center mb-1.5">
                    <span className="text-[10px] font-bold text-muted bg-card-secondary px-2 py-0.5 rounded-full border border-theme">
                      {position}º
                    </span>
                  </div>
                )}

                {/* Category Name */}
                <div className="wd-card-name font-bold text-center text-sm leading-snug px-1" title={cat.name}>
                  {cat.name}
                </div>

                {/* Vendas no Meio */}
                <div className="text-center my-2 py-1.5 px-2 bg-card-secondary rounded-lg border border-theme">
                  <span className="text-[10px] uppercase font-bold text-muted block">Vendas</span>
                  <span className="text-base font-black text-accent block">
                    {formatInt(cat.units_sold)} <span className="text-xs font-normal">un.</span>
                  </span>
                </div>

                {/* Total de Produtos na Categoria */}
                <div className="text-center text-[11px] text-muted mb-2 font-medium">
                  Total: <strong className="text-theme font-bold">{formatInt(totalProds)}</strong> itens
                </div>
              </div>

              {/* Bloco de Estoque: Empilhado (1 embaixo do outro) ou 2 Colunas Dinâmicas */}
              {layoutMode === 'stacked' ? (
                /* MODELO EMPILHADO (1 embaixo do outro): 100% responsivo, legível, sem corte */
                <div className="space-y-1.5 pt-2 border-t border-theme w-full">
                  {/* Card 1: Disponível */}
                  <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400">
                    <span className="text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5 min-w-0">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                      <span className="truncate">Disponível</span>
                    </span>
                    <span className="text-xs font-black shrink-0 ml-1">
                      {formatInt(cat.active_products)}
                    </span>
                  </div>

                  {/* Card 2: Indisponível */}
                  <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-slate-500/10 border border-slate-500/20 text-muted">
                    <span className="text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5 min-w-0">
                      <span className="w-2 h-2 rounded-full bg-slate-400 shrink-0" />
                      <span className="truncate">Indisponível</span>
                    </span>
                    <span className="text-xs font-black shrink-0 ml-1">
                      {formatInt(cat.inactive_products)}
                    </span>
                  </div>
                </div>
              ) : (
                /* MODELO 2 COLUNAS: Seguro e responsivo com overflow protegido */
                <div className="grid grid-cols-2 gap-1.5 pt-2 border-t border-theme text-center w-full">
                  <div className="bg-emerald-50/70 dark:bg-emerald-950/30 p-1.5 rounded-md border border-emerald-200 dark:border-emerald-800 min-w-0">
                    <span className="text-[9px] uppercase font-bold text-emerald-700 dark:text-emerald-400 block leading-tight truncate">
                      Disponível
                    </span>
                    <span className="text-xs font-black text-emerald-600 dark:text-emerald-400 block mt-0.5">
                      {formatInt(cat.active_products)}
                    </span>
                  </div>

                  <div className="bg-slate-100/70 dark:bg-slate-800/40 p-1.5 rounded-md border border-slate-200 dark:border-slate-700 min-w-0">
                    <span className="text-[9px] uppercase font-bold text-muted block leading-tight truncate">
                      Indisponível
                    </span>
                    <span className="text-xs font-black text-muted block mt-0.5">
                      {formatInt(cat.inactive_products)}
                    </span>
                  </div>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
