import * as React from 'react';
import { PulseDot } from '../motion/PulseDot';
import { useReducedMotion } from '../motion/useReducedMotion';
import { Lightning } from '../backgrounds/Lightning';
import { cn } from '../../lib/cn';

export interface AlertHostProps {
  /** 告警条内容；为空表示无告警 */
  alert: string | null;
  onDismiss?: () => void;
  className?: string;
}

/**
 * 全局告警条（黄金信号命中 / 环境异常 / 预算熔断）。
 * 语义动效只走 CSS keyframes 脉冲；命中瞬间由 Lightning 背景播放一次（8.6 / 8.7.1）。
 */
export function AlertHost({ alert, onDismiss, className }: AlertHostProps) {
  const reduced = useReducedMotion();
  const [flashing, setFlashing] = React.useState(false);

  React.useEffect(() => {
    if (!alert || reduced) return;
    setFlashing(true);
    const timer = window.setTimeout(() => setFlashing(false), 600);
    return () => window.clearTimeout(timer);
  }, [alert, reduced]);

  if (!alert) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'relative flex items-center gap-3 overflow-hidden rounded-card border border-red-team/50 bg-red-team/10 px-4 py-2.5',
        !reduced && 'animate-pulse',
        className
      )}
    >
      {flashing ? <Lightning active className="pointer-events-none absolute inset-0 h-full w-full opacity-70" /> : null}
      <PulseDot tone="red" />
      <span className="min-w-0 flex-1 truncate text-sm text-content">{alert}</span>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded px-2 py-0.5 text-xs text-content-muted hover:bg-white/10 hover:text-content"
        >
          关闭
        </button>
      ) : null}
    </div>
  );
}