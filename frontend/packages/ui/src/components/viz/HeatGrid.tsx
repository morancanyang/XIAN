import * as React from 'react';
import { cn } from '../../lib/cn';

export interface HeatCell {
  x: string;
  y: string;
  value: number;
  hint?: string;
}

export interface HeatGridProps {
  xLabels: string[];
  yLabels: string[];
  cells: HeatCell[];
  className?: string;
  onCellClick?: (cell: HeatCell) => void;
}

/** 类别 × 阶段热力网格（攻击矩阵页，技术方案 8.4）。格子 hover 涟漪。 */
export function HeatGrid({ xLabels, yLabels, cells, className, onCellClick }: HeatGridProps) {
  const lookup = React.useMemo(() => {
    const map = new Map<string, HeatCell>();
    for (const c of cells) map.set(`${c.x}||${c.y}`, c);
    return map;
  }, [cells]);

  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="border-collapse text-[11px]">
        <thead>
          <tr>
            <th className="p-1" />
            {xLabels.map((x) => (
              <th key={x} className="p-1 text-left font-medium text-content-faint">
                {x}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {yLabels.map((y) => (
            <tr key={y}>
              <td className="whitespace-nowrap p-1 pr-2 text-content-muted">{y}</td>
              {xLabels.map((x) => {
                const cell = lookup.get(`${x}||${y}`);
                const v = cell?.value ?? 0;
                return (
                  <td key={x} className="p-0.5">
                    <button
                      type="button"
                      title={cell?.hint ?? `${y} × ${x}`}
                      onClick={() => cell && onCellClick?.(cell)}
                      className={cn(
                        'flex h-8 w-full min-w-[64px] items-center justify-center rounded border border-border font-mono',
                        'transition-transform duration-fast ease-out hover:scale-105',
                        v === 0 && 'bg-white/[0.02] text-content-faint',
                        v > 0 && v < 0.34 && 'bg-blue-team/10 text-blue-team',
                        v >= 0.34 && v < 0.67 && 'bg-coach/15 text-coach',
                        v >= 0.67 && 'bg-red-team/20 text-red-team'
                      )}
                    >
                      {v === 0 ? '—' : `${Math.round(v * 100)}%`}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}