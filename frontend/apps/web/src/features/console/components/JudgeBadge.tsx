import { Badge } from '@xian/ui';
import { cn } from '../../../lib/utils/cn';

export interface JudgeBadgeProps {
  verdict: string;
  confidence?: number;
  reason?: string;
  className?: string;
}

/** 判定徽标：黄金信号命中时红色脉冲（技术方案 8.4）。 */
export function JudgeBadge({ verdict, confidence, reason, className }: JudgeBadgeProps) {
  const tone = verdict === 'success' ? 'danger' : verdict === 'partial' ? 'warning' : verdict === 'fail' ? 'success' : 'neutral';
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <Badge tone={tone} className={verdict === 'success' ? 'xian-badge-pop' : undefined}>
        {verdict === 'success' ? '命中' : verdict === 'partial' ? '部分命中' : verdict === 'fail' ? '未命中' : verdict}
      </Badge>
      {confidence !== undefined ? (
        <span className="font-mono text-[10px] text-content-faint">c={confidence.toFixed(2)}</span>
      ) : null}
      {reason ? <span className="text-[11px] text-content-muted">{reason}</span> : null}
    </span>
  );
}