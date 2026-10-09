import { Badge } from '@xian/ui';
import { cn } from '../../../lib/utils/cn';

export interface JudgeBadgeProps {
  verdict: string;
  confidence?: number;
  reason?: string;
  /** 裁判降级标记：LLM judge 不可用时结论来自离线启发式，须与真实判定区分开。 */
  degraded?: boolean;
  judgeModel?: string;
  className?: string;
}

/** 判定徽标：黄金信号命中时红色脉冲（技术方案 8.4）。 */
export function JudgeBadge({
  verdict,
  confidence,
  reason,
  degraded,
  judgeModel,
  className,
}: JudgeBadgeProps) {
  const tone = verdict === 'success' ? 'danger' : verdict === 'partial' ? 'warning' : verdict === 'fail' ? 'success' : 'neutral';
  return (
    <span className={cn('inline-flex flex-wrap items-center gap-2', className)}>
      <Badge tone={tone} className={verdict === 'success' ? 'xian-badge-pop' : undefined}>
        {verdict === 'success' ? '命中' : verdict === 'partial' ? '部分命中' : verdict === 'fail' ? '未命中' : verdict}
      </Badge>
      {degraded ? (
        <Badge tone="warning" title="LLM judge 不可用，本条结论由离线启发式裁判给出，置信度不可与在线判定直接比较">
          离线判定
        </Badge>
      ) : null}
      {confidence !== undefined ? (
        <span className="font-mono text-[10px] text-content-faint">c={confidence.toFixed(2)}</span>
      ) : null}
      {judgeModel ? <span className="font-mono text-[10px] text-content-faint">{judgeModel}</span> : null}
      {reason ? <span className="text-[11px] text-content-muted">{reason}</span> : null}
    </span>
  );
}