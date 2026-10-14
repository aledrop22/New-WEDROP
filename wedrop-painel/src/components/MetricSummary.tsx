import React from 'react';
import { Tag, CheckCircle2, XCircle, AlertCircle, ShoppingCart, ArrowDownToLine, HelpCircle } from 'lucide-react';
import { formatInt, WITHOUT_STATUS_HELP } from '../utils/status';

interface MetricSummaryProps {
  categoriesCount: number;
  activeProducts: number;
  inactiveProducts: number;
  withoutStatusProducts: number;
  unitsSold: number;
  unitsRestocked: number;
  isSingleDay: boolean;
  onOpenWithoutStatus?: () => void;
}

export const MetricSummary: React.FC<MetricSummaryProps> = ({
  categoriesCount,
  activeProducts,
  inactiveProducts,
  withoutStatusProducts,
  unitsSold,
  unitsRestocked,
  isSingleDay,
  onOpenWithoutStatus,
}) => {
  const salesLabel = isSingleDay ? 'Vendas 24h (Dia)' : 'Vendas no Período';
  const restockLabel = isSingleDay ? 'Reposição 24h' : 'Reposição no Período';

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-3 mb-6 w-full">
      {/* Categorias */}
      <div className="bg-card p-2.5 sm:p-3.5 rounded-lg border border-theme shadow-2xs min-w-0">
        <div className="flex items-center justify-between text-muted mb-1">
          <span className="text-xs font-semibold uppercase tracking-wider">Categorias</span>
          <Tag className="w-4 h-4 text-muted" />
        </div>
        <div className="text-2xl font-bold text-theme tracking-tight">
          {formatInt(categoriesCount)}
        </div>
        <div className="text-[11px] text-muted mt-0.5">catálogo completo</div>
      </div>

      {/* Itens Disponíveis */}
      <div className="bg-card p-2.5 sm:p-3.5 rounded-lg border border-theme shadow-2xs min-w-0">
        <div className="flex items-center justify-between text-muted mb-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Disponíveis</span>
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
        </div>
        <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tracking-tight">
          {formatInt(activeProducts)}
        </div>
        <div className="text-[11px] text-muted mt-0.5">selo disponível</div>
      </div>

      {/* Itens Indisponíveis */}
      <div className="bg-card p-2.5 sm:p-3.5 rounded-lg border border-theme shadow-2xs min-w-0">
        <div className="flex items-center justify-between text-muted mb-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted">Indisponíveis</span>
          <XCircle className="w-4 h-4 text-muted" />
        </div>
        <div className="text-2xl font-bold text-muted tracking-tight">
          {formatInt(inactiveProducts)}
        </div>
        <div className="text-[11px] text-muted mt-0.5">selo indisponível</div>
      </div>

      {/* Sem Status */}
      <div
        className={`bg-card p-2.5 sm:p-3.5 rounded-lg border shadow-2xs transition-all min-w-0 ${
          withoutStatusProducts > 0
            ? 'border-amber-400 hover:border-amber-500 cursor-pointer'
            : 'border-theme'
        }`}
        onClick={withoutStatusProducts > 0 ? onOpenWithoutStatus : undefined}
      >
        <div className="flex items-center justify-between text-muted mb-1">
          <div className="flex items-center gap-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">Sem status</span>
            <div className="group relative">
              <HelpCircle className="w-3.5 h-3.5 text-amber-500 cursor-help" />
              <div className="absolute left-0 bottom-full mb-1.5 hidden group-hover:block w-52 p-2 bg-slate-900 text-white text-[11px] rounded shadow-lg z-50 pointer-events-none leading-relaxed">
                {WITHOUT_STATUS_HELP}
              </div>
            </div>
          </div>
          <AlertCircle className="w-4 h-4 text-amber-500" />
        </div>
        <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 tracking-tight">
          {formatInt(withoutStatusProducts)}
        </div>
        <div className="text-[11px] text-amber-600/80 dark:text-amber-400/80 mt-0.5">
          {withoutStatusProducts > 0 ? 'auditar itens' : 'todos checados'}
        </div>
      </div>

      {/* Vendas */}
      <div className="bg-card p-2.5 sm:p-3.5 rounded-lg border border-red-300 dark:border-red-900 shadow-2xs min-w-0">
        <div className="flex items-center justify-between text-muted mb-1">
          <span className="text-xs font-bold uppercase tracking-wider text-accent">{salesLabel}</span>
          <ShoppingCart className="w-4 h-4 text-accent" />
        </div>
        <div className="text-2xl font-black text-accent tracking-tight">
          {formatInt(unitsSold)}
        </div>
        <div className="text-[11px] text-accent/80 mt-0.5">unidades vendidas</div>
      </div>

      {/* Reposição */}
      <div className="bg-card p-2.5 sm:p-3.5 rounded-lg border border-blue-300 dark:border-blue-900 shadow-2xs min-w-0">
        <div className="flex items-center justify-between text-muted mb-1">
          <span className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">{restockLabel}</span>
          <ArrowDownToLine className="w-4 h-4 text-blue-500" />
        </div>
        <div className="text-2xl font-black text-blue-600 dark:text-blue-400 tracking-tight">
          {formatInt(unitsRestocked)}
        </div>
        <div className="text-[11px] text-blue-500 mt-0.5">unidades repostas</div>
      </div>
    </div>
  );
};
