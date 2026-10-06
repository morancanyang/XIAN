import { useCountUp } from './useReducedMotion';

export interface CountUpProps {
  value: number;
  durationMs?: number;
  className?: string;
  format?: (value: number) => string;
}

/** 数字滚动：分数 / ASR 等指标变化（技术方案 8.6「数字变化」600ms）。 */
export function CountUp({ value, durationMs = 600, className, format }: CountUpProps) {
  const current = useCountUp(value, durationMs);
  return <span className={className}>{format ? format(current) : Math.round(current).toString()}</span>;
}