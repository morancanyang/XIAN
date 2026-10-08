import { useReducedMotion, useCountUp } from '../motion/useReducedMotion';
import { cn } from '../../lib/cn';

export interface MetricRingProps {
  value: number;
  max?: number;
  label?: string;
  unit?: string;
  tone?: 'blue' | 'red' | 'coach' | 'success';
  size?: number;
  className?: string;
}

/** 环形指标：预算消耗 / ASR / SecScore（技术方案 8.4 预算环形进度）。 */
export function MetricRing({
  value,
  max = 100,
  label,
  unit = '',
  tone = 'blue',
  size = 120,
  className
}: MetricRingProps) {
  const reduced = useReducedMotion();
  const animated = useCountUp(value, 600);
  const shown = reduced ? value : animated;
  const ratio = Math.min(1, Math.max(0, shown / max));

  const stroke =
    tone === 'blue'
      ? 'var(--color-blue-team)'
      : tone === 'red'
        ? 'var(--color-red-team)'
        : tone === 'coach'
          ? 'var(--color-coach)'
          : 'var(--color-success)';

  const r = size / 2 - 8;
  const c = 2 * Math.PI * r;

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth="6" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - ratio)}
          style={{ transition: reduced ? undefined : 'stroke-dashoffset 100ms linear' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-lg font-semibold text-content">
          {Math.round(shown)}
          {unit}
        </span>
        {label ? <span className="text-[10px] text-content-faint">{label}</span> : null}
      </div>
    </div>
  );
}