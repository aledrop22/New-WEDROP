import React, { useState } from 'react';
import { Calendar, Filter, Layers, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { getLocalDateString, getPastDate, formatDateBR, CATEGORY_NAMES } from '../utils/status';

interface SidebarProps {
  startDate: string;
  endDate: string;
  onChangeStartDate: (date: string) => void;
  onChangeEndDate: (date: string) => void;
  selectedCategory: string | null;
  onSelectCategory: (category: string | null) => void;
  totalProductsCount: number;
  dataSourceName: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  startDate,
  endDate,
  onChangeStartDate,
  onChangeEndDate,
  selectedCategory,
  onSelectCategory,
  totalProductsCount,
  dataSourceName,
}) => {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const today = getLocalDateString();
  const yesterday = getPastDate(1);
  const sevenDaysAgo = getPastDate(7);
  const thirtyDaysAgo = getPastDate(30);

  const applyPreset = (start: string, end: string) => {
    onChangeStartDate(start);
    onChangeEndDate(end);
  };

  return (
    <aside className="w-full lg:w-64 xl:w-72 bg-card border-b lg:border-b-0 lg:border-r border-theme p-3 sm:p-4 shrink-0 transition-colors">
      {/* Mobile Toggle Bar */}
      <div className="lg:hidden flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <Calendar className="w-4 h-4 text-accent shrink-0" />
          <div className="min-w-0">
            <span className="font-bold text-xs text-theme block truncate">Filtro de Período & Categorias</span>
            <span className="text-[10px] text-muted block truncate">
              {formatDateBR(startDate)} a {formatDateBR(endDate)}
              {selectedCategory ? ` · ${selectedCategory}` : ''}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="flex items-center gap-1 text-xs text-accent font-bold px-2.5 py-1.5 rounded-lg bg-card-secondary border border-theme shrink-0 ml-2"
        >
          <span>{isMobileOpen ? 'Recolher' : 'Filtrar'}</span>
          {isMobileOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Main Filter Content (collapsible on mobile, always visible on desktop) */}
      <div className={`mt-3 lg:mt-0 flex-col gap-5 ${isMobileOpen ? 'flex' : 'hidden lg:flex'}`}>
        {/* Período Section */}
        <div>
          <div className="flex items-center gap-2 text-theme font-bold text-sm mb-3">
            <Calendar className="w-4 h-4 text-accent" />
            <span>Filtro de Período</span>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-muted mb-1">
                Data Inicial
              </label>
              <input
                type="date"
                value={startDate}
                max={endDate || today}
                onChange={(e) => onChangeStartDate(e.target.value)}
                className="w-full px-3 py-1.5 text-xs bg-card-secondary border border-theme rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-hidden text-theme"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-muted mb-1">
                Data Final
              </label>
              <input
                type="date"
                value={endDate}
                min={startDate}
                max={today}
                onChange={(e) => onChangeEndDate(e.target.value)}
                className="w-full px-3 py-1.5 text-xs bg-card-secondary border border-theme rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-hidden text-theme"
              />
            </div>

            {/* Quick Presets */}
            <div className="pt-2">
              <span className="block text-[11px] text-muted font-bold uppercase tracking-wider mb-2">
                Atalhos Rápidos
              </span>
              <div className="grid grid-cols-2 gap-1.5 text-xs">
                <button
                  type="button"
                  onClick={() => applyPreset(today, today)}
                  className={`px-2 py-1.5 rounded-md border text-center transition-colors font-medium ${
                    startDate === today && endDate === today
                      ? 'bg-accent text-white border-accent font-bold'
                      : 'bg-card-secondary text-muted border-theme hover:text-theme'
                  }`}
                >
                  Hoje (24h)
                </button>
                <button
                  type="button"
                  onClick={() => applyPreset(yesterday, yesterday)}
                  className={`px-2 py-1.5 rounded-md border text-center transition-colors font-medium ${
                    startDate === yesterday && endDate === yesterday
                      ? 'bg-accent text-white border-accent font-bold'
                      : 'bg-card-secondary text-muted border-theme hover:text-theme'
                  }`}
                >
                  Ontem (D-1)
                </button>
                <button
                  type="button"
                  onClick={() => applyPreset(sevenDaysAgo, today)}
                  className={`px-2 py-1.5 rounded-md border text-center transition-colors font-medium ${
                    startDate === sevenDaysAgo && endDate === today
                      ? 'bg-accent text-white border-accent font-bold'
                      : 'bg-card-secondary text-muted border-theme hover:text-theme'
                  }`}
                >
                  Últimos 7 dias
                </button>
                <button
                  type="button"
                  onClick={() => applyPreset(thirtyDaysAgo, today)}
                  className={`px-2 py-1.5 rounded-md border text-center transition-colors font-medium ${
                    startDate === thirtyDaysAgo && endDate === today
                      ? 'bg-accent text-white border-accent font-bold'
                      : 'bg-card-secondary text-muted border-theme hover:text-theme'
                  }`}
                >
                  Últimos 30 dias
                </button>
              </div>
            </div>
          </div>
        </div>

        <hr className="border-theme" />

        {/* Categoria Selector */}
        <div>
          <div className="flex items-center gap-2 text-theme font-bold text-sm mb-3">
            <Filter className="w-4 h-4 text-accent" />
            <span>Filtro de Categoria</span>
          </div>

          <label className="block text-xs font-semibold text-muted mb-1.5">
            Filtrar 1 categoria específica
          </label>
          <select
            value={selectedCategory || ''}
            onChange={(e) => onSelectCategory(e.target.value === '' ? null : e.target.value)}
            className="w-full px-3 py-2 text-xs bg-card-secondary border border-theme rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-hidden font-semibold text-theme"
          >
            <option value="">Nenhuma (visão geral)</option>
            {CATEGORY_NAMES.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>

          {selectedCategory && (
            <button
              type="button"
              onClick={() => onSelectCategory(null)}
              className="mt-2 text-xs text-accent hover:underline flex items-center gap-1 font-bold"
            >
              <span>Limpar e voltar à visão geral</span>
            </button>
          )}
        </div>

        <hr className="border-theme" />

        {/* System info */}
        <div className="bg-card-secondary border border-theme rounded-lg p-3 text-xs space-y-2">
          <div className="flex items-center gap-1.5 font-bold text-theme">
            <Layers className="w-3.5 h-3.5 text-accent" />
            <span>Status do Depósito</span>
          </div>
          <div className="flex justify-between text-muted">
            <span>Itens catalogados:</span>
            <span className="font-bold text-theme">{totalProductsCount}</span>
          </div>
          <div className="flex justify-between text-muted">
            <span>Origem dos dados:</span>
            <span className="font-semibold text-theme truncate max-w-[120px]" title={dataSourceName}>
              {dataSourceName}
            </span>
          </div>
        </div>

        {/* Helpful hint */}
        <div className="mt-auto bg-card-secondary border border-theme rounded-lg p-3 text-xs text-muted flex gap-2">
          <HelpCircle className="w-4 h-4 text-accent shrink-0 mt-0.5" />
          <p className="leading-relaxed text-[11px]">
            O robô roda à meia-noite (00:00) mapeando o catálogo para identificar vendas de 24h, flutuações de preços e reposições.
          </p>
        </div>
      </div>
    </aside>
  );
};
