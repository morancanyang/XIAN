import { cn } from '../../lib/cn';

export interface PulseDotProps {
  tone?: 'red' | 'blue' | 'coach' | 'success';
  size?: number;
  className?: string;
  active?: boolean;
}

/** 告警 / 命中脉冲点（技术方案 8.6「告警」CSS keyframes 1s 无限）。 */
export function PulseDot({ tone = 'red', size = 8, className, active = true }: PulseDotProps) {
  const color =
    tone === 'red'
      ? 'var(--color-red-team)'
      : tone === 'blue'
        ? 'var(--color-blue-team)'
        : tone === 'coach'
          ? 'var(--color-coach)'
          : 'var(--color-success)';
  return (
    <span
      aria-hidden="true"
      className={cn('relative inline-flex shrink-0', className)}
      style={{ width: size, height: size }}
    >
      <span
        className={cn('absolute inset-0 rounded-full', active && 'animate-pulse')}
        style={{ backgroundColor: color, opacity: active ? 0.75 : 0.35 }}
      />
      <span className="absolute inset-0 rounded-full" style={{ backgroundColor: color }} />
    </span>
  );
}