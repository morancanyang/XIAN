import { Badge } from '@xian/ui';
import type { AttackRecord, Verdict } from '@xian/types';

/** 判定徽标（技术方案 8.6：命中时弹入）。 */
export function VerdictBadgeLazy({ verdict }: { verdict: Verdict }) {
  const tone = verdict === 'success' ? 'danger' : verdict === 'partial' ? 'warning' : verdict === 'fail' ? 'success' : 'neutral';
  const label = verdict === 'success' ? '命中' : verdict === 'partial' ? '部分命中' : verdict === 'fail' ? '未命中' : '不可判定';
  return (
    <Badge tone={tone} className="xian-badge-pop">
      {label}
    </Badge>
  );
}

/** 把判定依据压成一句可读文案：离线本地裁判也要能解释"为什么是这个结论"。 */
export function recordEvidence(record: AttackRecord): string {
  const fromRules = (record.rule_hits ?? [])
    .map((h) => String((h as { detail?: string }).detail ?? ''))
    .filter(Boolean)
    .join('；');
  if (fromRules) return fromRules;
  const fromEvidence = (record.evidence ?? []).map((e) => {
    const rec = e as Record<string, unknown>;
    if (typeof rec.matched_text === 'string' && rec.matched_text) return `命中 ${rec.pattern ?? ''} → ${rec.matched_text}`;
    if (typeof rec.similarity === 'number') return `与载荷相似度 ${rec.similarity.toFixed(2)}（回声应答）`;
    if (typeof rec.marker === 'string') return rec.marker;
    if (typeof rec.tool === 'string') return rec.tool;
    return '';
  });
  return fromEvidence.filter(Boolean).join('；') || '—';
}

export { Badge };
export { VirtualList, DataTable, Pagination } from '@xian/ui';