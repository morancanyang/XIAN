import * as React from 'react';
import { cn } from '../../lib/cn';

export interface TreeNode {
  id: string;
  label: React.ReactNode;
  badge?: React.ReactNode;
  meta?: string;
  children?: TreeNode[];
}

export interface TreeProps {
  nodes: TreeNode[];
  className?: string;
  defaultExpandedIds?: string[];
  onSelect?: (node: TreeNode) => void;
  selectedId?: string | null;
}

export function Tree({ nodes, className, defaultExpandedIds = [], onSelect, selectedId }: TreeProps) {
  const [expanded, setExpanded] = React.useState<Set<string>>(() => new Set(defaultExpandedIds));

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const renderNodes = (list: TreeNode[], depth: number): React.ReactNode =>
    list.map((node) => {
      const hasChildren = Boolean(node.children?.length);
      const isOpen = expanded.has(node.id) || (hasChildren && depth === 0 && !expanded.has(node.id) && defaultExpandedIds.length === 0);
      return (
        <li key={node.id}>
          <div
            className={cn(
              'flex cursor-pointer items-center gap-2 rounded-[6px] px-2 py-1.5 text-sm',
              selectedId === node.id ? 'bg-white/10 text-content' : 'text-content-muted hover:bg-white/5 hover:text-content'
            )}
            style={{ paddingLeft: 4 + depth * 14 }}
            onClick={() => (hasChildren ? toggle(node.id) : onSelect?.(node))}
          >
            {hasChildren ? (
              <button
                type="button"
                aria-label={isOpen ? '收起' : '展开'}
                aria-expanded={isOpen}
                className="flex h-4 w-4 items-center justify-center text-content-faint"
                onClick={(e) => {
                  e.stopPropagation();
                  toggle(node.id);
                }}
              >
                <svg viewBox="0 0 24 24" className={cn('h-3 w-3 transition-transform', isOpen && 'rotate-90')} fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </button>
            ) : (
              <span aria-hidden="true" className="h-4 w-4" />
            )}
            <span className="truncate">{node.label}</span>
            {node.badge}
            {node.meta ? <span className="ml-auto font-mono text-[11px] text-content-faint">{node.meta}</span> : null}
          </div>
          {hasChildren && isOpen ? <ul className="mt-0.5">{renderNodes(node.children!, depth + 1)}</ul> : null}
        </li>
      );
    });

  return <ul className={cn('select-none text-sm', className)}>{renderNodes(nodes, 0)}</ul>;
}