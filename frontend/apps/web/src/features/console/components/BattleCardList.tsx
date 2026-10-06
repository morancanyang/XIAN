import type { BusEvent } from '@xian/types';
import { Card, CardContent, Badge } from '@xian/ui';
import { SEVERITY_LABEL } from '@xian/types';
import { fmtClock } from '../../../lib/utils/format';
import { desensitize } from '../../../lib/utils/desensitize';

/** 战报卡片：命中即翻入（技术方案 8.4 模式二）。 */
export function BattleCardList({ cards }: { cards: BusEvent[] }) {
  if (cards.length === 0) return <p className="text-xs text-content-faint">暂无战报卡片。</p>;

  return (
    <div className="space-y-2">
      {cards.map((event, i) => {
        const payload = event.payload ?? {};
        const severity = String(payload.severity ?? 'high');
        return (
          <Card key={`${event.ts}-${i}`} className="xian-badge-pop border-red-team/40 bg-red-team/5">
            <CardContent className="space-y-1">
              <div className="flex items-center gap-2">
                <Badge tone="danger">{SEVERITY_LABEL[severity as keyof typeof SEVERITY_LABEL] ?? severity}</Badge>
                <span className="font-mono text-[11px] text-content">{String(payload.category_id ?? payload.category ?? '')}</span>
                <span className="ml-auto font-mono text-[10px] text-content-faint">{fmtClock(event.ts)}</span>
              </div>
              <p className="font-mono text-[11px] text-content-muted">{desensitize(String(payload.payload ?? ''))}</p>
              <p className="text-[11px] text-content-faint">{String(payload.evidence ?? event.message ?? '')}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}