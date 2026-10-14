import React from 'react';
import { X, ExternalLink, Truck, Hash } from 'lucide-react';
import { ProductRecord } from '../types/wedrop';
import { formatDateTimeBR, getStatusBucket, WITHOUT_STATUS_HELP } from '../utils/status';

interface ProductDetailModalProps {
  product: ProductRecord | null;
  onClose: () => void;
}

export const ProductDetailModal: React.FC<ProductDetailModalProps> = ({
  product,
  onClose,
}) => {
  if (!product) return null;

  const status = getStatusBucket(product.is_active, product.availability);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-card rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden border border-theme max-h-[90vh] flex flex-col text-theme">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-theme bg-card-secondary">
          <div>
            <span className="text-xs font-bold text-accent uppercase tracking-wider">
              {product.category}
            </span>
            <h2 className="text-base font-bold text-theme mt-0.5 leading-snug">
              {product.name}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-muted hover:text-theme p-1 rounded-md shrink-0 ml-2"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs">
          {/* Key Indicators Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-card-secondary p-3 rounded-lg border border-theme">
              <span className="text-[11px] text-muted uppercase font-semibold">Preço Atual</span>
              <div className="text-base font-black text-theme mt-0.5">{product.price || '—'}</div>
              {product.previous_price && (
                <div className="text-[10px] text-muted line-through">
                  Anterior: {product.previous_price}
                </div>
              )}
            </div>

            <div className="bg-card-secondary p-3 rounded-lg border border-theme">
              <span className="text-[11px] text-muted uppercase font-semibold">Situação</span>
              <div className="mt-0.5">
                {status === 'Ativos' ? (
                  <span className="inline-block font-bold text-emerald-700 bg-emerald-100/70 dark:bg-emerald-950/40 dark:text-emerald-300 px-2 py-0.5 rounded text-[11px]">
                    Disponível (Ativo)
                  </span>
                ) : status === 'Sem status' ? (
                  <span
                    className="inline-block font-bold text-amber-700 bg-amber-100/70 dark:bg-amber-950/40 dark:text-amber-300 px-2 py-0.5 rounded text-[11px]"
                    title={WITHOUT_STATUS_HELP}
                  >
                    Sem status
                  </span>
                ) : (
                  <span className="inline-block font-bold text-muted bg-card px-2 py-0.5 rounded text-[11px] border border-theme">
                    Indisponível (Inativo)
                  </span>
                )}
              </div>
            </div>

            <div className="bg-card-secondary p-3 rounded-lg border border-theme">
              <span className="text-[11px] text-muted uppercase font-semibold">Estoque Atual</span>
              <div className="text-base font-black text-theme mt-0.5">{product.stock || '0'}</div>
            </div>

            <div className="bg-card-secondary p-3 rounded-lg border border-theme">
              <span className="text-[11px] text-muted uppercase font-semibold">Saldo Real</span>
              <div className="text-base font-black text-theme mt-0.5">{product.real_balance || '0'}</div>
            </div>
          </div>

          {/* Logistics & Identifiers */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-card-secondary p-3.5 rounded-lg border border-theme space-y-2">
              <div className="font-bold text-theme flex items-center gap-1.5 pb-1 border-b border-theme">
                <Hash className="w-3.5 h-3.5 text-accent" />
                <span>Identificadores Fiscais & SKU</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">ID do Produto:</span>
                <span className="font-mono text-theme">{product.product_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">SKU:</span>
                <span className="font-mono text-theme">{product.sku || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">EAN:</span>
                <span className="font-mono text-theme">{product.ean || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">NCM:</span>
                <span className="font-mono text-theme">{product.ncm || '—'}</span>
              </div>
            </div>

            <div className="bg-card-secondary p-3.5 rounded-lg border border-theme space-y-2">
              <div className="font-bold text-theme flex items-center gap-1.5 pb-1 border-b border-theme">
                <Truck className="w-3.5 h-3.5 text-accent" />
                <span>Fornecedor & Logística</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Fornecedor:</span>
                <span className="font-semibold text-theme">{product.supplier || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">CNPJ Fornecedor:</span>
                <span className="font-mono text-theme">{product.cnpj || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Origem (UF):</span>
                <span className="text-theme">{product.origin_state || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Peso / Dimensões:</span>
                <span className="text-theme">
                  {product.weight ? `${product.weight} kg` : '—'} ·{' '}
                  {product.height || '0'}x{product.width || '0'}x{product.length || '0'} cm
                </span>
              </div>
            </div>
          </div>

          {/* Description */}
          {product.description && (
            <div className="space-y-1.5">
              <span className="font-bold text-theme">Descrição do Produto</span>
              <p className="text-muted bg-card-secondary p-3 rounded-lg border border-theme leading-relaxed whitespace-pre-line">
                {product.description}
              </p>
            </div>
          )}

          <div className="text-[11px] text-muted">
            Última leitura pelo scraper: {formatDateTimeBR(product.updated_at)}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-theme bg-card-secondary">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-muted hover:text-theme rounded-lg transition-colors"
          >
            Fechar
          </button>

          <a
            href={product.url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-accent bg-accent-hover rounded-lg shadow-xs transition-colors"
          >
            <span>Abrir Produto na Minha Loja / WeDrop</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
};
