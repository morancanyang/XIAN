import { AttackPathGraph, EmptyState } from '@xian/ui';
import type { CampaignPlan, Verdict } from '@xian/types';
import { useMatrixCategories } from '../../../lib/api/hooks';

/** kill chain 阶段顺序：一列一个阶段，链路从左到右（与后端 STAGE_ORDER 一致）。 */
const STAGE_ORDER = [
  'recon',
  'initial_exec',
  'payload_delivery',
  'privilege_escalation',
  'exfiltration',
  'impact'
];

const STAGE_LABELS: Record<string, string> = {
  recon: '侦察',
  initial_exec: '初始执行',
  payload_delivery: '载荷投递',
  privilege_escalation: '权限提升',
  exfiltration: '数据渗出',
  impact: '影响破坏'
};

/**
 * DAG 预览图（技术方案 8.4 模式一 CampaignLive / 创建页计划预览）。
 *
 * 每个节点是一个攻击类别：列 = kill chain 阶段，行内并列的节点可并发执行；
 * 箭头表示依赖（提权/渗出要等前序上下文泄露）。节点上的小字是该类别分到的
 * 用例数与 token 预算，判定徽标来自该类别已跑出来的攻击记录。
 */
export function PlanPreview({
  plan,
  verdicts
}: {
  plan: CampaignPlan | null;
  verdicts?: Record<string, Verdict>;
}) {
  const categories = useMatrixCategories();
  const nameOf = (code: string) => categories.data?.find((c) => c.code === code)?.name;

  if (!plan || (plan.dag_nodes?.length ?? 0) === 0) {
    return (
      <EmptyState
        title="暂无战役计划"
        description="先选择攻击类别并生成计划，指挥官会产出 DAG 与预算分配。"
      />
    );
  }

  const nodes = (plan.dag_nodes ?? []).map((n) => {
    const cases = n.case_ids?.length ?? 0;
    const tokens = n.budget_split?.token ?? 0;
    return {
      id: n.id,
      label: nameOf(n.category_code) ?? n.category_code,
      category: n.stage,
      verdict: verdicts?.[n.category_code] ?? verdicts?.[n.id],
      meta: `${cases || '—'} 例 · ${Math.round(tokens / 1000)}k token`
    };
  });

  return (
    <div className="space-y-2">
      <AttackPathGraph
        height={300}
        nodes={nodes}
        edges={(plan.edges ?? []).map(([source, target]) => ({ source, target }))}
        stages={STAGE_ORDER}
      />
      <p className="text-[11px] text-content-faint">
        列 = kill chain 阶段（{STAGE_ORDER.map((s) => STAGE_LABELS[s]).join(' → ')}）；
        箭头 = 依赖关系（提权/渗出需等待前序上下文泄露），无箭头的节点并发执行。
        节点小字为该类别分到的用例数与 token 预算。
      </p>
    </div>
  );
}
