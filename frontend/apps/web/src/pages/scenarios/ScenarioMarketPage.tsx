import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Badge,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Field,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Switch,
  FadeIn
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { CardSkeleton } from '../../components/ui/Loading';
import { ErrorState } from '@xian/ui';
import { useScenarios, useCreateScenarioInstance, useScenarioInstances } from '../../lib/api/hooks';
import { useAgents } from '../../lib/api/hooks';
import { errorHint, errorMessage } from '../../lib/api/errors';
import { useToast } from '../../components/layout/ToastHost';
import { DIFFICULTY_LABEL } from '@xian/types';
import type { Difficulty, Scenario } from '@xian/types';
import { useSessionStore } from '../../store/sessionStore';

/** 场景市场：卡片网格 + 筛选 + 实例化弹窗（技术方案 8.4）。 */
export default function ScenarioMarketPage() {
  const scenarios = useScenarios();
  const instances = useScenarioInstances();
  const agents = useAgents({ page: 1, size: 100 });
  const create = useCreateScenarioInstance();
  const toast = useToast();
  const activeAgentId = useSessionStore((s) => s.activeAgentId);

  const [keyword, setKeyword] = useState('');
  const [difficulty, setDifficulty] = useState<Difficulty | 'all'>('all');
  const [target, setTarget] = useState<Scenario | null>(null);

  const rows = (scenarios.data ?? []).filter(
    (s) =>
      (difficulty === 'all' || s.difficulty === difficulty) &&
      (keyword === '' || s.name.includes(keyword) || s.code.toLowerCase().includes(keyword.toLowerCase()))
  );

  return (
    <div>
      <PageHeader
        title="靶场场景"
        description="六要素场景：compose + 假数据 + 工具权限 + 蜜标 + 监控点 + 剧本（PRD 3.1.1）。"
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Input placeholder="搜索场景名称 / 编号" value={keyword} onChange={(e) => setKeyword(e.target.value)} className="max-w-xs" />
        <Select value={difficulty} onValueChange={(v) => setDifficulty(v as Difficulty | 'all')}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部难度</SelectItem>
            {(Object.keys(DIFFICULTY_LABEL) as Difficulty[]).map((d) => (
              <SelectItem key={d} value={d}>
                {DIFFICULTY_LABEL[d]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="ml-auto text-xs text-content-faint">已有实例 {instances.data?.length ?? 0} 个</span>
      </div>

      {scenarios.isLoading ? (
        <CardSkeleton count={6} />
      ) : scenarios.isError ? (
        <ErrorState message={errorMessage(scenarios.error)} hint={errorHint(scenarios.error)} onRetry={() => scenarios.refetch()} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((s, i) => (
            <FadeIn key={s.id} delay={i * 0.04} as="div">
              <Card className="h-full">
                <CardContent className="flex h-full flex-col gap-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-mono text-[11px] text-blue-team">{s.code}</p>
                      <h3 className="text-sm font-semibold">{s.name}</h3>
                    </div>
                    <Badge tone="coach">{DIFFICULTY_LABEL[s.difficulty]}</Badge>
                  </div>
                  <p className="text-xs text-content-muted">类别：{s.category}</p>
                  <div className="flex flex-wrap gap-1">
                    {s.canary_types.map((c) => (
                      <Badge key={c}>蜜标 {c}</Badge>
                    ))}
                  </div>
                  <div className="mt-auto flex gap-2">
                    <Button size="sm" onClick={() => setTarget(s)}>
                      实例化
                    </Button>
                    <Button size="sm" variant="outline" asChild>
                      <Link to={`/scenarios/${s.code}`}>详情</Link>
                    </Button>
                    <Button size="sm" variant="outline" asChild>
                      <Link to={`/campaigns/new?scenario=${s.id}`}>发起战役</Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </FadeIn>
          ))}
        </div>
      )}

      <InstanceDialog
        scenario={target}
        agentId={activeAgentId ?? agents.data?.items[0]?.id ?? ''}
        onClose={() => setTarget(null)}
        onSubmit={async (body) => {
          try {
            const instance = await create.mutateAsync(body);
            toast.success('实例已创建', `实例 ID ${instance.id.slice(0, 8)}`);
            setTarget(null);
            instances.refetch();
          } catch (e) {
            toast.error('实例化失败', errorMessage(e));
          }
        }}
        loading={create.isPending}
      />

      {instances.data && instances.data.length > 0 ? (
        <Card className="mt-4">
          <CardContent className="space-y-2">
            <div className="flex flex-wrap items-baseline gap-x-3">
              <p className="text-xs font-semibold text-content">最近实例</p>
              <p className="text-[11px] text-content-faint">
                实例是已经拉起的靶场环境（假数据 + 蜜标 + 监控探针）。点场景名直接用它开打，或进场景详情查看。
              </p>
            </div>
            {instances.data.slice(0, 5).map((i) => (
              <div
                key={i.id}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-control border border-border bg-elevated px-3 py-2 text-xs"
              >
                <Link
                  to={`/console?instance=${i.id}`}
                  className="font-medium text-content transition-colors hover:text-coach"
                >
                  {i.scenario_name || i.scenario_code || '未标记场景'}
                </Link>
                <span className="font-mono text-content-faint">{i.scenario_code || i.id.slice(0, 8)}</span>
                <span className="text-content-faint">{new Date(i.created_at).toLocaleString('zh-CN', { hour12: false })}</span>
                <span className="ml-auto flex items-center gap-3">
                  <Badge tone={i.status === 'ready' ? 'success' : 'coach'}>{i.status}</Badge>
                  {i.scenario_code ? (
                    <Link to={`/scenarios/${i.scenario_code}`} className="text-content-muted transition-colors hover:text-content">
                      场景详情
                    </Link>
                  ) : null}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function InstanceDialog({
  scenario,
  agentId,
  onClose,
  onSubmit,
  loading
}: {
  scenario: Scenario | null;
  agentId: string;
  onClose: () => void;
  onSubmit: (body: { scenario_id: string; data_scale: number; canary_enhanced: boolean; run_baseline: boolean }) => Promise<void>;
  loading: boolean;
}) {
  const [dataScale, setDataScale] = useState(200);
  const [canary, setCanary] = useState(true);
  const [baseline, setBaseline] = useState(true);

  return (
    <Dialog open={Boolean(scenario)} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>实例化场景：{scenario?.name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <Field label="假数据规模" id="scale" hint="1 ~ 10000 条；影响-canary 种植密度与可用性基线耗时。">
            <Input id="scale" type="number" min={1} max={10000} value={dataScale} onChange={(e) => setDataScale(Number(e.target.value))} />
          </Field>
          <label className="flex items-center gap-2 text-sm text-content-muted">
            <Switch checked={canary} onCheckedChange={setCanary} />
            蜜标增强（额外生成诱导型假凭证）
          </label>
          <label className="flex items-center gap-2 text-sm text-content-muted">
            <Switch checked={baseline} onCheckedChange={setBaseline} />
            运行可用性基线（跑完基线任务才算 ready）
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            loading={loading}
            disabled={!scenario || !agentId}
            onClick={() =>
              scenario &&
              onSubmit({
                scenario_id: scenario.id,
                data_scale: dataScale,
                canary_enhanced: canary,
                run_baseline: baseline
              })
            }
          >
            创建实例
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}