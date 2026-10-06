import * as React from 'react';
import { Virtuoso } from 'react-virtuoso';
import { cn } from '../../lib/cn';

export interface VirtualListProps<T> {
  items: T[];
  rowKey: (item: T, index: number) => string;
  renderRow: (item: T, index: number) => React.ReactNode;
  className?: string;
  height?: number | string;
  emptyState?: React.ReactNode;
}

/**
 * 长列表虚拟化（技术方案 8.1「长列表一律虚拟化」）。
 * 攻击记录 / trace 事件规模可达十万级，必须走虚拟滚动。
 */
export function VirtualList<T>({
  items,
  rowKey,
  renderRow,
  className,
  height = 480,
  emptyState
}: VirtualListProps<T>) {
  if (items.length === 0 && emptyState) {
    return <div className={className}>{emptyState}</div>;
  }

  return (
    <Virtuoso
      data={items}
      className={cn('xian-scrollbar', className)}
      style={{ height }}
      itemContent={(index: number, item: T) => (
        <div key={rowKey(item, index)}>{renderRow(item, index)}</div>
      )}
    />
  );
}