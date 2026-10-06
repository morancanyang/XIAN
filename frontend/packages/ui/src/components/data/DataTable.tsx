import * as React from 'react';
import { Table, TBody, TD, TH, THead, TR } from '../primitives/Table';
import { EmptyState } from '../feedback/EmptyState';
import { Skeleton } from '../primitives/Misc';
import { cn } from '../../lib/cn';

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  render: (row: T, index: number) => React.ReactNode;
  className?: string;
  width?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string;
  loading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
  onRowClick?: (row: T) => void;
  className?: string;
  /** 超过该行数后不再渲染底部提示，交由分页组件处理 */
  maxRows?: number;
}

/** 通用表格：为空/加载态/空状态插画统一处理（PRD 2.3.2、2.3.3）。 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  emptyTitle,
  emptyDescription,
  emptyAction,
  onRowClick,
  className,
  maxRows = 1000
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div className={cn('space-y-2 p-4', className)}>
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-9 w-full" />
        ))}
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        action={emptyAction}
        className={className}
      />
    );
  }

  return (
    <Table className={className}>
      <THead>
        <TR className="hover:bg-transparent">
          {columns.map((col) => (
            <TH key={col.key} style={col.width ? { width: col.width } : undefined} className={col.className}>
              {col.header}
            </TH>
          ))}
        </TR>
      </THead>
      <TBody>
        {rows.slice(0, maxRows).map((row, i) => (
          <TR
            key={rowKey(row, i)}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            className={onRowClick ? 'cursor-pointer' : undefined}
          >
            {columns.map((col) => (
              <TD key={col.key} className={col.className}>
                {col.render(row, i)}
              </TD>
            ))}
          </TR>
        ))}
      </TBody>
    </Table>
  );
}

export interface PaginationProps {
  page: number;
  size: number;
  total: number;
  onPageChange: (page: number) => void;
  onSizeChange?: (size: number) => void;
}

const SIZES = [10, 20, 50, 100];

/** PRD 2.3.2：默认 20 条，可调 10/50/100。 */
export function Pagination({ page, size, total, onPageChange, onSizeChange }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-3 py-2 text-xs text-content-muted">
      <span>
        共 {total} 条 · 第 {page}/{pages} 页
      </span>
      <div className="flex items-center gap-2">
        {onSizeChange ? (
          <label className="flex items-center gap-1">
            每页
            <select
              value={size}
              onChange={(e) => onSizeChange(Number(e.target.value))}
              className="rounded border border-border bg-base px-1.5 py-1 text-xs"
            >
              {SIZES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <button
          type="button"
          className="rounded border border-border px-2 py-1 enabled:hover:bg-white/10 disabled:opacity-40"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          上一页
        </button>
        <button
          type="button"
          className="rounded border border-border px-2 py-1 enabled:hover:bg-white/10 disabled:opacity-40"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          下一页
        </button>
      </div>
    </div>
  );
}