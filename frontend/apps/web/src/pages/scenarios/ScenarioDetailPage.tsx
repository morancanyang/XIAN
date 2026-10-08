import { Link, useParams } from 'react-router-dom';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CodeBlock,
  EmptyState,
  ErrorState
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { CardSkeleton } from '../../components/ui/Loading';
import { useScenario } from '../../lib/api/hooks';
import { errorHint, errorMessage } from '../../lib/api/errors';
import { DIFFICULTY_LABEL } from '@xian/types';
import type { Difficulty, ScenarioTool } from '@xian/types';

/** 工具写权限 / 高危工具用红队色标出，只读工具保持中性。 */
const SCOPE_TONE: Record<string, 'danger' | 'warning' | 'neutral'> = {
  write: 'danger',
  exec: 'danger',
  read: 'neutral'
};

const RISK_TONE: Record<string, 'danger' | 'warning' | 'coach' | 'neutral'> = {
  critical: 'danger',
  high: 'danger',
  medium: 'warning',
  low: 'coach'
};

/**
 * 场景详情：把后端 /scenarios/{code} 的完整情报摆到台面上——
 * 剧本、工具风险面、监控面、典型攻击链、考点标签。
 */
export default function ScenarioDetailPage() {
  const { code = '' } = useParams();
  const scenario = useScenario(code);

  if (scenario.isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <CardSkeleton count={4} />
      </div>
    );
  }
  if (scenario.isError) {
    return <ErrorState message={errorMessage(scenario.error)} hint={errorHint(scenario.error)} onRetry={() => scenario.refetch()} />;
  }
  if (!scenario.data) {
    return <EmptyState title="场景不存在" description={`未找到编号为 ${code} 的靶场场景。`} />;
  }

  const s = scenario.data;

  return (
    <div>
      <PageHeader
        title={s.name}
        description={s.description || '靶场场景详情'}
        actions={
          <>
            <Button variant="outline" asChild>
              <Link to="/scenarios">返回场景市场</Link>
            </Button>
            <Button asChild>
              <Link to={`/campaigns/new?scenario=${s.id}`}>发起战役</Link>
            </Button>
          </>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Badge tone="blue">{s.code}</Badge>
        <Badge tone="coach">{DIFFICULTY_LABEL[s.difficulty as Difficulty] ?? s.difficulty}</Badge>
        <Badge>{s.category}</Badge>
        <span className="text-xs text-content-faint">Agent 形态：{s.agent_form || '-'}</span>
        <span className="text-xs text-content-faint">基线任务 {s.baseline_tasks ?? 0} 项</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>考点标签</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1">
              {(s.exam_tags ?? []).map((t) => (
                <Badge key={t} tone="blue">
                  {t}
                </Badge>
              ))}
              {(s.exam_tags ?? []).length === 0 ? (
                <span className="text-xs text-content-faint">该场景未标注考点。</span>
              ) : null}
            </div>
            <p className="mt-3 text-xs font-semibold text-content-muted">蜜标类型</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {(s.canary_types ?? []).map((c) => (
                <Badge key={c}>蜜标 {c}</Badge>
              ))}
              {(s.canary_types ?? []).length === 0 ? (
                <span className="text-xs text-content-faint">未配置蜜标。</span>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>典型攻击链</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-1">
              {(s.typical_attack_chain ?? []).map((stage, i) => (
                <span key={stage} className="flex items-center gap-1">
                  {i > 0 ? <span className="text-content-faint">→</span> : null}
                  <Badge tone="red">{stage}</Badge>
                </span>
              ))}
              {(s.typical_attack_chain ?? []).length === 0 ? (
                <span className="text-xs text-content-faint">未给出典型攻击链。</span>
              ) : null}
            </div>
            <p className="mt-3 text-xs font-semibold text-content-muted">监控面</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {(s.monitors ?? []).map((m) => (
                <Badge key={m}>{m}</Badge>
              ))}
              {(s.monitors ?? []).length === 0 ? (
                <span className="text-xs text-content-faint">未声明监控组件。</span>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>工具风险面</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(s.tools ?? []).map((t: ScenarioTool) => (
              <div key={t.name} className="rounded-control border border-border bg-elevated px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-content">{t.name}</span>
                  <Badge tone={SCOPE_TONE[t.scope] ?? 'neutral'}>权限 {t.scope}</Badge>
                  <Badge tone={RISK_TONE[t.risk_level] ?? 'neutral'}>{t.risk_level}</Badge>
                  {t.require_confirm ? <Badge tone="coach">需确认</Badge> : null}
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-content-muted">{t.description}</p>
              </div>
            ))}
            {(s.tools ?? []).length === 0 ? (
              <span className="text-xs text-content-faint">该场景未声明工具。</span>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>基线剧本</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-2">
              {(s.script ?? []).map((line, i) => (
                <li key={i} className="flex gap-2 text-xs leading-relaxed text-content-muted">
                  <span className="font-mono text-content-faint">{i + 1}.</span>
                  <span className="xian-cjk">{line}</span>
                </li>
              ))}
              {(s.script ?? []).length === 0 ? (
                <span className="text-xs text-content-faint">未提供基线剧本。</span>
              ) : null}
            </ol>
            {Object.keys(s.env_template ?? {}).length > 0 ? (
              <div className="mt-3">
                <p className="mb-1 text-xs font-semibold text-content-muted">环境变量</p>
                <CodeBlock>{JSON.stringify(s.env_template, null, 2)}</CodeBlock>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
