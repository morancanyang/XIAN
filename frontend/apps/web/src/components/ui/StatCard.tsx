import type { ReactNode } from 'react';
import { Card, CardContent } from '@xian/ui';
import { CountUp } from '@xian/ui';
import { cn } from '../../lib/utils/cn';

export interface StatCardProps {
  label: string;
  value: number | string;
  suffix?: string;
  hint?: string;
  trend?: number;
  tone?: 'blue' | 'red' | 'coach' | 'success';
  icon?: ReactNode;
  className?: string;
}

/** 顶部指标卡（驾驶舱，技术方案 8.4）：数字滚动 + 趋势。 */
export function StatCard({ label, value, suffix, hint, trend, tone = 'blue', icon, className }: StatCardProps) {
  const toneColor =
    tone === 'red'
      ? 'text-red-team'
      : tone === 'coach'
        ? 'text-coach'
        : tone === 'success'
          ? 'text-success'
          : 'text-blue-team';

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardContent className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-content-muted">{label}</p>
          <p className={cn('mt-1 font-mono text-2xl font-semibold tabular-nums', toneColor)}>
            {typeof value === 'number' ? <CountUp value={value} /> : value}
            {suffix ? <span className="ml-0.5 text-sm text-content-muted">{suffix}</span> : null}
          </p>
          {hint ? <p className="mt-1 text-[11px] text-content-faint">{hint}</p> : null}
          {trend !== undefined && trend !== 0 ? (
            <p className={cn('mt-1 text-[11px]', trend > 0 ? 'text-danger' : 'text-success')}>
              {trend > 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}
            </p>
          ) : null}
        </div>
        {icon ? <div className="shrink-0 text-content-faint">{icon}</div> : null}
      </CardContent>
    </Card>
  );
}