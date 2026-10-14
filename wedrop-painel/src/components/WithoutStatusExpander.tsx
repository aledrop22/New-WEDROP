import React, { useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { ProductRecord } from '../types/wedrop';
import { formatInt, WITHOUT_STATUS_HELP, formatDateTimeBR } from '../utils/status';

interface WithoutStatusExpanderProps {
  products: ProductRecord[];
  forceOpen?: boolean;
}

export const WithoutStatusExpander: React.FC<WithoutStatusExpanderProps> = ({
  products,
  forceOpen = false,
}) => {
  const [isOpen, setIsOpen] = useState(forceOpen);

  if (products.length === 0) return null;

  return (
    <div className="mb-6 border border-amber-300 dark:border-amber-800 bg-amber-50/40 dark:bg-amber-950/20 rounded-lg overflow-hidden shadow-2xs">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3.5 text-left bg-amber-100/40 dark:bg-amber-950/40 hover:bg-amber-100/60 transition-colors"
      >
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
          <span className="font-bold text-amber-800 dark:text-amber-300 text-xs sm:text-sm">
            Auditoria: Quais são os {formatInt(products.length)} produtos sem status?
          </span>
        </div>
        <div className="flex items-center gap-1 text-xs text-amber-700 dark:text-amber-400 font-semibold">
          <span>{isOpen ? 'Ocultar tabela' : 'Exibir tabela'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-4 bg-card border-t border-amber-200 dark:border-amber-800 space-y-3">
          <p className="text-xs text-muted leading-relaxed bg-card-secondary p-2.5 rounded border border-theme">
            {WITHOUT_STATUS_HELP}
          </p>

          <div className="overflow-x-auto max-h-72 border border-theme rounded-lg">
            <table className="w-full text-xs text-left">
              <thead className="bg-card-secondary text-muted uppercase font-semibold border-b border-theme sticky top-0">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Produto</th>
                  <th className="px-3 py-2">Categoria</th>
                  <th className="px-3 py-2">Fornecedor</th>
                  <th className="px-3 py-2 text-right">Estoque</th>
                  <th className="px-3 py-2">Lido em</th>
                  <th className="px-3 py-2 text-center">Ação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-theme text-theme">
                {products.map((p) => (
                  <tr key={p.product_id} className="hover-bg">
                    <td className="px-3 py-2 font-mono text-[11px] text-muted">{p.product_id}</td>
                    <td className="px-3 py-2 font-medium text-theme max-w-xs truncate" title={p.name}>
                      {p.name}
                    </td>
                    <td className="px-3 py-2 text-muted">{p.category}</td>
                    <td className="px-3 py-2 text-muted">{p.supplier || '—'}</td>
                    <td className="px-3 py-2 text-right font-medium text-theme">{p.stock || '0'}</td>
                    <td className="px-3 py-2 text-muted">{formatDateTimeBR(p.updated_at)}</td>
                    <td className="px-3 py-2 text-center">
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-accent hover:opacity-80 font-bold text-[11px]"
                      >
                        <span>Abrir na Loja</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
