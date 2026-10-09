import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Checkbox,
  Field,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { PlanPreview } from '../../features/campaign/components/PlanPreview';
import { ErrorState } from '@xian/ui';
import { TableSkeleton } from '../../components/ui/Loading';
import {
  useAgents,
  useCampaignPlan,
  useCreateCampaign,
  useMatrixCategories,
  usePreviewCampaignPlan,
  useScenarioInstances
} from '../../lib/api/hooks';
import { errorHint, errorMessage } from '../../lib/api/errors';
import { useToast } from '../../components/layout/ToastHost';
import { useSessionStore } from '../../store/sessionStore';
import type { Budget, CampaignPlan, Intensity, JudgeMode, OutputMode } from '@xian/types';

/** 模式一配置页：勾选攻击类别、强度、预算、裁判与产出模式（PRD 3.3.1）。 */
export default function CampaignCreatePage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const toast = useToast();
  const activeAgentId = useSessionStore((s) => s.activeAgentId);
  const setActiveCampaign = useSessionStore((s) => s.setActiveCampaign);

  const agents = useAgents({ page: 1, size: 100 });
  const categories = useMatrixCategories();
  const instances = useScenarioInstances();

  const [agentId, setAgentId] = useState(activeAgentId ?? '');
  const [scenarioId, setScenarioId] = useState(params.get('scenario') ?? '');
  const [scope, setScope] = useState<string[]>([]);
  const [intensity, setIntensity] = useState<Intensity>('standard');
  const [judgeMode, setJudgeMode] = useState<JudgeMode>('standard');
  const [outputMode, setOutputMode] = useState<OutputMode>('summary');
  const [budget, setBudget] = useState<Budget>({ token: 200_000, cases: 60, minutes: 30 });
  // 层内并发度：同一依赖层里互不依赖的用例并行投放（后端默认 4，夹在 1~16）
  const [concurrency, setConcurrency] = useState(4);
  const [plan, setPlan] = useState<CampaignPlan | null>(null);

  const create = useCreateCampaign();
  const previewPlan = usePreviewCampaignPlan();
  const planFor = useCampaignPlan();

  const selectedAgent = useMemo(
    () => agents.data?.items.find((a) => a.id === agentId),
    [agents.data, agentId]
  );

  const verified = Boolean(selectedAgent?.ownership_verified);

  function toggleScope(code: string) {
    setScope((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));
  }

  return (
    <div>
      <PageHeader title="模式一 · 发起战役" description="勾选攻击类别、强度与预算，指挥官会产出 DAG 计划与预算分配。" />

      <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>目标与范围</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {agents.isLoading ? (
                <TableSkeleton rows={3} />
              ) : (
                <Field label="目标 Agent" required id="camp-agent">
                  <Select value={agentId} onValueChange={setAgentId}>
                    <SelectTrigger id="camp-agent">
                      <SelectValue placeholder="选择 Agent" />
                    </SelectTrigger>
                    <SelectContent>
                      {agents.data?.items.map((a) => (
                        <SelectItem key={a.id} value={a.id}>
                          {a.name} {a.ownership_verified ? '· 已验证' : '· 未验证'}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              )}

              <Field label="关联场景实例" id="camp-instance" hint="留空表示直连目标 Agent（HTTP/SDK 接入方式）。">
                <Select value={scenarioId} onValueChange={setScenarioId}>
                  <SelectTrigger id="camp-instance">
                    <SelectValue placeholder="不关联" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">不关联</SelectItem>
                    {(instances.data ?? []).map((i) => (
                      <SelectItem key={i.id} value={i.id}>
                        {i.scenario_name || i.scenario_code || i.id.slice(0, 8)}（{i.status}）
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              {selectedAgent && !verified ? (
                <div className="rounded-control border border-danger/40 bg-danger/10 p-3 text-xs text-danger">
                  该 Agent 尚未完成归属校验，无法发起战役。请先在资产页完成 DNS TXT 或镜像摘要校验。
                </div>
              ) : null}

              <div>
                <p className="mb-2 text-sm font-medium text-content-muted">
                  攻击类别（已选 {scope.length} / {categories.data?.length ?? 0}）
                </p>
                <div className="grid max-h-56 gap-2 overflow-y-auto rounded-control border border-border bg-sunken p-3 xian-scrollbar sm:grid-cols-2">
                  {categories.data?.map((c) => (
                    <label key={c.id} className="flex cursor-pointer items-center gap-2 text-xs">
                      <Checkbox checked={scope.includes(c.code)} onCheckedChange={() => toggleScope(c.code)} />
                      <span className="font-mono text-content">{c.code}</span>
                      <span className="truncate text-content-muted">{c.name}</span>
                    </label>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>预算与判定</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <Field label="强度" id="c-intensity">
                <Select value={intensity} onValueChange={(v) => setIntensity(v as Intensity)}>
                  <SelectTrigger id="c-intensity">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="recon">侦察</SelectItem>
                    <SelectItem value="standard">标准</SelectItem>
                    <SelectItem value="deep">深度</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="裁判模式" id="c-judge">
                <Select value={judgeMode} onValueChange={(v) => setJudgeMode(v as JudgeMode)}>
                  <SelectTrigger id="c-judge">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="loose">宽松</SelectItem>
                    <SelectItem value="standard">标准</SelectItem>
                    <SelectItem value="strict">严格</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="产出模式" id="c-output">
                <Select value={outputMode} onValueChange={(v) => setOutputMode(v as OutputMode)}>
                  <SelectTrigger id="c-output">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="summary">摘要</SelectItem>
                    <SelectItem value="full">全量</SelectItem>
                    <SelectItem value="reproducible">可复现</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Token 预算" id="b-token">
                <Input
                  id="b-token"
                  type="number"
                  value={budget.token}
                  onChange={(e) => setBudget((b) => ({ ...b, token: Number(e.target.value) }))}
                />
              </Field>
              <Field label="用例数上限" id="b-cases">
                <Input
                  id="b-cases"
                  type="number"
                  value={budget.cases}
                  onChange={(e) => setBudget((b) => ({ ...b, cases: Number(e.target.value) }))}
                />
              </Field>
              <Field label="时长上限（分钟）" id="b-minutes">
                <Input
                  id="b-minutes"
                  type="number"
                  value={budget.minutes}
                  onChange={(e) => setBudget((b) => ({ ...b, minutes: Number(e.target.value) }))}
                />
              </Field>
              <Field
                label="并发投放数"
                id="b-concurrency"
                hint="同一依赖层内互不依赖的用例并行执行；跨层仍按 kill chain 顺序等待前序上下文"
              >
                <Input
                  id="b-concurrency"
                  type="number"
                  min={1}
                  max={16}
                  value={concurrency}
                  onChange={(e) => setConcurrency(Math.max(1, Math.min(16, Number(e.target.value) || 1)))}
                />
              </Field>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>战役计划预览</CardTitle>
              <Badge tone={scope.length ? 'blue' : 'neutral'}>{scope.length} 个类别</Badge>
            </CardHeader>
            <CardContent>
              <PlanPreview plan={plan} />
              <Button
                variant="outline"
                className="mt-3 w-full"
                disabled={!agentId || scope.length === 0}
                loading={previewPlan.isPending}
                onClick={async () => {
                  try {
                    const p = await previewPlan.mutateAsync({ agent_id: agentId, scope, budget });
                    setPlan(p);
                    toast.success('计划已生成', `${p.dag_nodes?.length ?? 0} 个节点`);
                  } catch (e) {
                    toast.error('计划生成失败', errorMessage(e));
                  }
                }}
              >
                生成 DAG 计划
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-3">
              <Button
                className="w-full"
                disabled={!agentId || scope.length === 0 || !verified}
                loading={create.isPending}
                onClick={async () => {
                  try {
                    const campaign = await create.mutateAsync({
                      agent_id: agentId,
                      scenario_id: scenarioId || null,
                      scope,
                      intensity,
                      budget,
                      constraints: { concurrency },
                      judge_mode: judgeMode,
                      output_mode: outputMode
                    });
                    setActiveCampaign(campaign.id);
                    toast.success('战役已创建', '可立即执行');
                    // 立即落库 DAG 计划，详情页一进来就能看到节点与预算分配
                    try {
                      setPlan(await planFor.mutateAsync(campaign.id));
                    } catch {
                      /* 计划失败不阻塞跳转，执行时会自动补齐 */
                    }
                    navigate(`/campaigns/${campaign.id}`);
                  } catch (e) {
                    toast.error('创建失败', errorMessage(e));
                  }
                }}
              >
                创建战役
              </Button>
              {!verified && selectedAgent ? (
                <p className="text-center text-[11px] text-danger">Agent 未归属校验，创建按钮已禁用</p>
              ) : null}
              {errorHint(create.error) ? <p className="text-[11px] text-danger">{errorHint(create.error)}</p> : null}
              {create.isError ? <ErrorState message={errorMessage(create.error)} /> : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}