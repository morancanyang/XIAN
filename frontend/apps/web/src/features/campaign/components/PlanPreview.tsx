import { AttackPathGraph } from '@xian/ui';
import type { CampaignPlan } from '@xian/types';
import { EmptyState } from '@xian/ui';

/** DAG 预览图（技术方案 8.4 模式一 CampaignLive）。 */
export function PlanPreview({ plan }: { plan: CampaignPlan | null }) {
  if (!plan || (plan.dag_nodes?.length ?? 0) === 0) {
    return (
      <EmptyState
        title="暂无战役计划"
        description="先选择攻击类别并生成计划，指挥官会产出 DAG 与预算分配。"
      />
    );
  }

  const verdictByNode = (plan.constraints?.verdicts as Record<string, string> | undefined) ?? {};

  return (
    <AttackPathGraph
      height={300}
      nodes={(plan.dag_nodes ?? []).map((n) => ({
        id: n.id,
        label: n.title,
        category: n.category,
        verdict: verdictByNode[n.id] as 'success' | 'partial' | 'fail' | 'unavailable' | undefined
      }))}
      edges={plan.edges.map(([source, target]) => ({ source, target }))}
    />
  );
}