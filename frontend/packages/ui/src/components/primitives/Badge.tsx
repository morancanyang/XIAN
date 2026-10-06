import * as React from 'react';
import { cn } from '../../lib/cn';

export type BadgeTone = 'neutral' | 'red' | 'blue' | 'coach' | 'success' | 'danger' | 'warning';

const toneClass: Record<BadgeTone, string> = {
  neutral: 'border-border text-content-muted bg-white/5',
  red: 'border-red-team/40 text-red-team bg-red-team/10',
  blue: 'border-blue-team/40 text-blue-team bg-blue-team/10',
  coach: 'border-coach/40 text-coach bg-coach/10',
  success: 'border-success/40 text-success bg-success/10',
  danger: 'border-danger/40 text-danger bg-danger/10',
  warning: 'border-warning/40 text-warning bg-warning/10'
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

export function Badge({ className, tone = 'neutral', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-pill border px-2 py-0.5 text-xs font-medium',
        toneClass[tone],
        className
      )}
      {...props}
    />
  );
}