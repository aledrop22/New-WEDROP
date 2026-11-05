import React from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';

export type SortDirection = 'asc' | 'desc';

export interface TableSortState {
  key: string;
  direction: SortDirection;
}

export type SortValue = string | number | null | undefined;

interface SortableTableHeaderProps {
  sortKey: string;
  sortState: TableSortState | null;
  onSort: (key: string) => void;
  className?: string;
  align?: 'left' | 'center' | 'right';
  children: React.ReactNode;
}

export const SortableTableHeader: React.FC<SortableTableHeaderProps> = ({
  sortKey,
  sortState,
  onSort,
  className = '',
  align = 'left',
  children,
}) => {
  const active = sortState?.key === sortKey;
  const ariaSort = active
    ? sortState.direction === 'asc'
      ? 'ascending'
      : 'descending'
    : 'none';
  const label = typeof children === 'string' ? children : sortKey;
  const nextDirection = active && sortState.direction === 'asc' ? 'descending' : 'ascending';
  const Icon = active
    ? sortState.direction === 'asc'
      ? ArrowUp
      : ArrowDown
    : ArrowUpDown;
  const alignment =
    align === 'right'
      ? 'justify-end text-right'
      : align === 'center'
        ? 'justify-center text-center'
        : 'text-left';

  return (
    <th className={className} aria-sort={ariaSort}>
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        aria-label={`Ordenar por ${label} em ordem ${nextDirection}`}
        title={`Ordenar por ${label} (${nextDirection})`}
        className={`inline-flex w-full items-center gap-1 hover:text-theme focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${alignment}`}
      >
        <span>{children}</span>
        <Icon aria-hidden="true" className={`h-3 w-3 shrink-0 ${active ? 'text-accent' : 'opacity-50'}`} />
      </button>
    </th>
  );
};

export function nextTableSort(current: TableSortState | null, key: string): TableSortState {
  if (current?.key === key) {
    return { key, direction: current.direction === 'asc' ? 'desc' : 'asc' };
  }
  return { key, direction: 'asc' };
}

export function sortTableRows<T>(
  rows: readonly T[],
  sortState: TableSortState | null,
  getValue: (row: T, key: string) => SortValue,
): T[] {
  if (!sortState) return [...rows];

  const direction = sortState.direction === 'asc' ? 1 : -1;
  return rows
    .map((row, index) => ({ row, index, value: getValue(row, sortState.key) }))
    .sort((left, right) => {
      const leftMissing = left.value === null || left.value === undefined || (typeof left.value === 'number' && Number.isNaN(left.value));
      const rightMissing = right.value === null || right.value === undefined || (typeof right.value === 'number' && Number.isNaN(right.value));
      if (leftMissing || rightMissing) {
        return leftMissing === rightMissing ? left.index - right.index : leftMissing ? 1 : -1;
      }

      const comparison =
        typeof left.value === 'number' && typeof right.value === 'number'
          ? left.value - right.value
          : String(left.value).localeCompare(String(right.value), 'pt-BR', {
              numeric: true,
              sensitivity: 'base',
            });
      return comparison === 0 ? left.index - right.index : comparison * direction;
    })
    .map(({ row }) => row);
}

export function parseSortNumber(value: string | number | null | undefined): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (!value) return null;
  const normalized = value
    .trim()
    .replace(/\s/g, '')
    .replace(/[^\d,.-]/g, '')
    .replace(/\.(?=.*[,])/g, '')
    .replace(',', '.')
    .replace(/\.(?=\d{3}(?:\.|$))/g, '');
  const number = Number(normalized);
  return Number.isFinite(number) ? number : null;
}
