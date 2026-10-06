import * as React from 'react';
import { cn } from '../../lib/cn';

export interface TimelineItem {
  id: string;
  ts?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  tone?: 'default' | 'red' | 'blue' | 'coach' | 'success';
  badge?: React.ReactNode;
}

export interface TimelineProps {
  items: TimelineItem[];
  className?: string;
}

const dotTone: Record<NonNullable<TimelineItem['tone']>, string> = {
  default: 'border-border bg-elevated',
  red: 'border-red-team bg-red-team/20',
  blue: 'border-blue-team bg-blue-team/20',
  coach: 'border-coach bg-coach/20',
  success: 'border-success bg-success/20'
};

/** 观测 / 命中 / 复测时间线。 */
export function Timeline({ items, className }: TimelineProps) {
  return (
    <ol className={cn('relative space-y-4 pl-6', className)}>
      <span aria-hidden="true" className="absolute left-[9px] top-1 bottom-1 w-px bg-border" />
      {items.map((item) => (
        <li key={item.id} className="relative">
          <span
            aria-hidden="true"
            className={cn(
              'absolute -left-6 top-1 h-[10px] w-[10px] rounded-full border-2',
              dotTone[item.tone ?? 'default']
            )}
          />
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-content">{item.title}</span>
            {item.badge}
            {item.ts ? <span className="font-mono text-[11px] text-content-faint">{item.ts}</span> : null}
          </div>
          {item.description ? (
            <div className="mt-1 text-xs leading-relaxed text-content-muted">{item.description}</div>
          ) : null}
        </li>
      ))}
    </ol>
  );
}