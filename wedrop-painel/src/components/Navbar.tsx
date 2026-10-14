import React from 'react';
import { Database, RefreshCw, Settings, Download, ExternalLink, Zap, BarChart2, Tag, LayoutGrid } from 'lucide-react';
import { DataSourceConfig, ThemeId, DashboardViewMode } from '../types/wedrop';
import { ThemeSelector } from './ThemeSelector';

interface NavbarProps {
  config: DataSourceConfig;
  currentTheme: ThemeId;
  onSelectTheme: (themeId: ThemeId) => void;
  viewMode: DashboardViewMode;
  onChangeViewMode: (mode: DashboardViewMode) => void;
  onOpenSettings: () => void;
  onExportData: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  config,
  currentTheme,
  onSelectTheme,
  viewMode,
  onChangeViewMode,
  onOpenSettings,
  onExportData,
  onRefresh,
  isRefreshing,
}) => {
  return (
    <header className="bg-card border-b border-theme sticky top-0 z-30 shadow-xs transition-colors w-full">
      <div className="w-full px-3 sm:px-4 lg:px-6">
        <div className="flex items-center justify-between h-16 gap-3">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 shrink-0">
            <div className="w-9 h-9 rounded-lg bg-accent flex items-center justify-center text-white font-black text-lg shadow-xs">
              W
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-lg font-extrabold tracking-tight text-theme">
                  WeDrop <span className="text-accent">Monitor</span>
                </span>
                <span className="text-[10px] bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300 font-bold px-1.5 py-0.5 rounded uppercase">
                  Depósito 24h
                </span>
              </div>
              <p className="text-[11px] text-muted hidden sm:block">
                Leitura noturna de catálogo, estoque e preços
              </p>
            </div>
          </div>

          {/* Center: Navigation View Modes */}
          <div className="hidden lg:flex items-center gap-1 bg-card-secondary p-1 rounded-xl border border-theme">
            <button
              type="button"
              onClick={() => onChangeViewMode('decision_24h')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                viewMode === 'decision_24h'
                  ? 'bg-card text-theme shadow-2xs'
                  : 'text-muted hover:text-theme'
              }`}
            >
              <Zap className="w-3.5 h-3.5 text-accent" />
              <span>Decisão 24h</span>
            </button>

            <button
              type="button"
              onClick={() => onChangeViewMode('day_comparison')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                viewMode === 'day_comparison'
                  ? 'bg-card text-theme shadow-2xs'
                  : 'text-muted hover:text-theme'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5 text-blue-500" />
              <span>Comparativo D-1 vs D0</span>
            </button>

            <button
              type="button"
              onClick={() => onChangeViewMode('price_alerts')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                viewMode === 'price_alerts'
                  ? 'bg-card text-theme shadow-2xs'
                  : 'text-muted hover:text-theme'
              }`}
            >
              <Tag className="w-3.5 h-3.5 text-emerald-500" />
              <span>Preços (Alta/Baixa)</span>
            </button>

            <button
              type="button"
              onClick={() => onChangeViewMode('full_catalog')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                viewMode === 'full_catalog'
                  ? 'bg-card text-theme shadow-2xs'
                  : 'text-muted hover:text-theme'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5 text-slate-400" />
              <span>Catálogo Geral</span>
            </button>
          </div>

          {/* Right: Theme Switcher & Actions */}
          <div className="flex items-center space-x-1.5 sm:space-x-2">
            {/* Theme Selector (Chavinha Dark/Light + 6 Temas) */}
            <ThemeSelector currentTheme={currentTheme} onSelectTheme={onSelectTheme} />

            {/* Refresh button */}
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="p-1.5 sm:p-2 text-muted hover:text-theme rounded-lg transition-colors border border-theme bg-card hover-bg"
              title="Atualizar dados agora"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-accent' : ''}`} />
            </button>

            {/* Export data */}
            <button
              onClick={onExportData}
              className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-theme bg-card border border-theme hover-bg rounded-lg transition-colors"
              title="Exportar dados para CSV"
            >
              <Download className="w-3.5 h-3.5 text-muted" />
              <span className="hidden md:inline">Exportar</span>
            </button>

            {/* Settings */}
            <button
              onClick={onOpenSettings}
              className="p-1.5 sm:p-2 text-muted hover:text-theme rounded-lg transition-colors border border-theme bg-card hover-bg"
              title="Conexão e status da leitura"
            >
              <Settings className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Mobile View Mode Tabs */}
        <div className="flex lg:hidden overflow-x-auto py-2 gap-1.5 border-t border-theme text-xs">
          <button
            onClick={() => onChangeViewMode('decision_24h')}
            className={`px-3 py-1 rounded-md font-bold whitespace-nowrap ${
              viewMode === 'decision_24h' ? 'bg-accent text-white' : 'bg-card text-muted'
            }`}
          >
            Decisão 24h
          </button>
          <button
            onClick={() => onChangeViewMode('day_comparison')}
            className={`px-3 py-1 rounded-md font-bold whitespace-nowrap ${
              viewMode === 'day_comparison' ? 'bg-accent text-white' : 'bg-card text-muted'
            }`}
          >
            Comparativo D-1 vs D0
          </button>
          <button
            onClick={() => onChangeViewMode('price_alerts')}
            className={`px-3 py-1 rounded-md font-bold whitespace-nowrap ${
              viewMode === 'price_alerts' ? 'bg-accent text-white' : 'bg-card text-muted'
            }`}
          >
            Preços
          </button>
          <button
            onClick={() => onChangeViewMode('full_catalog')}
            className={`px-3 py-1 rounded-md font-bold whitespace-nowrap ${
              viewMode === 'full_catalog' ? 'bg-accent text-white' : 'bg-card text-muted'
            }`}
          >
            Catálogo Geral
          </button>
        </div>
      </div>
    </header>
  );
};
