import React from 'react';
import { X, Database, CheckCircle2, AlertTriangle, RefreshCw, Lock } from 'lucide-react';
import { DataSourceConfig } from '../types/wedrop';
import { formatDateTimeBR, formatInt } from '../utils/status';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: DataSourceConfig;
  lastCollectionAt: string | null;
  categoriesCount: number;
  productsCount: number;
  eventsCount: number;
  onRefresh: () => Promise<void>;
  isRefreshing: boolean;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  config,
  lastCollectionAt,
  categoriesCount,
  productsCount,
  eventsCount,
  onRefresh,
  isRefreshing,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-card rounded-xl shadow-2xl w-full max-w-xl overflow-hidden border border-theme text-theme">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-theme bg-card-secondary">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-accent" />
            <h2 className="text-base font-bold text-theme">Conexão e status da leitura</h2>
          </div>
          <button onClick={onClose} className="text-muted hover:text-theme p-1 rounded-md">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          <div className="p-3 bg-card-secondary border border-theme rounded-lg text-xs space-y-2">
            <div className="flex justify-between text-muted">
              <span>Fonte:</span>
              <span className="font-semibold text-theme">Supabase (lido pelo servidor)</span>
            </div>
            <div className="flex justify-between text-muted">
              <span>Situação:</span>
              <span
                className={`font-bold flex items-center gap-1 ${
                  config.isConnected ? 'text-emerald-500' : 'text-red-500'
                }`}
              >
                {config.isConnected ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                )}
                {config.isConnected ? 'Conectado' : 'Sem conexão'}
              </span>
            </div>
            <div className="flex justify-between text-muted">
              <span>Última leitura do painel:</span>
              <span className="font-semibold text-theme">{config.lastFetchedAt || '—'}</span>
            </div>
            <div className="flex justify-between text-muted">
              <span>Última coleta gravada:</span>
              <span className="font-semibold text-theme">{formatDateTimeBR(lastCollectionAt)}</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center text-xs">
            <div className="p-3 bg-card-secondary border border-theme rounded-lg">
              <div className="text-muted font-bold uppercase text-[10px]">Categorias</div>
              <div className="text-lg font-bold text-theme">{formatInt(categoriesCount)}</div>
            </div>
            <div className="p-3 bg-card-secondary border border-theme rounded-lg">
              <div className="text-muted font-bold uppercase text-[10px]">Produtos</div>
              <div className="text-lg font-bold text-theme">{formatInt(productsCount)}</div>
            </div>
            <div className="p-3 bg-card-secondary border border-theme rounded-lg">
              <div className="text-muted font-bold uppercase text-[10px]">Movimentações</div>
              <div className="text-lg font-bold text-theme">{formatInt(eventsCount)}</div>
            </div>
          </div>

          <div className="p-3 bg-card-secondary border border-theme rounded-lg flex items-start gap-2 text-[11px] text-muted leading-relaxed">
            <Lock className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
            <span>
              A chave do Supabase fica nas variáveis de ambiente da Vercel e nunca chega ao navegador.
              A coleta do catálogo continua rodando no computador pelo projeto Python (pasta Drop).
            </span>
          </div>

          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              disabled={isRefreshing}
              onClick={onRefresh}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-theme bg-card-secondary hover-bg border border-theme rounded-md transition-colors disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-accent' : ''}`} />
              <span>{isRefreshing ? 'Lendo Supabase...' : 'Testar conexão e reler'}</span>
            </button>
            <span className={`text-xs font-bold ${config.isConnected ? 'text-emerald-500' : 'text-red-500'}`}>
              {config.statusMessage}
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-theme bg-card-secondary">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-bold text-white bg-accent bg-accent-hover rounded-lg shadow-xs transition-colors cursor-pointer"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
};
