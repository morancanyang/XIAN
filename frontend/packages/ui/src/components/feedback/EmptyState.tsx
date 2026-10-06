import * as React from 'react';
import { cn } from '../../lib/cn';
import { LetterGlitch } from '../backgrounds/LetterGlitch';

export interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  /* 列表空状态是否挂 LetterGlitch 背景（技术方案 8.7.1：空状态插画下层） */
  glitch?: boolean;
  className?: string;
}

/** 空状态插画位（PRD 2.3.3）。 */
export function EmptyState({
  title = '暂无数据',
  description = '换个筛选条件，或先创建一条记录。',
  icon,
  action,
  glitch = false,
  className
}: EmptyStateProps) {
  return (
    <div className={cn('relative flex flex-col items-center justify-center gap-3 overflow-hidden px-6 py-12 text-center', className)}>
      {glitch ? (
        <LetterGlitch className="pointer-events-none absolute -inset-8 opacity-20" glitchSpeed={150} />
      ) : null}
      <div
        aria-hidden="true"
        className="flex h-14 w-14 items-center justify-center rounded-full border border-border bg-white/5 text-content-faint"
      >
        {icon ?? (
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
        )}
      </div>
      <p className="text-sm font-medium text-content">{title}</p>
      <p className="max-w-sm text-xs text-content-muted">{description}</p>
      {action}
    </div>
  );
}