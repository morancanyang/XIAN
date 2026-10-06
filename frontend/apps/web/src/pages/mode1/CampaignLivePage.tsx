import { Link, useParams } from 'react-router-dom';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ErrorState,
  MetricRing,
  Progress
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { CampaignStatusBadge } from '../../components/ui/badges';
import { RadarBackdrop } from '../../features/campaign/components/RadarBackdrop';
import { PlanPreview } from '../../features/campaign/components/PlanPreview';
import { RoleActivityFeed } from '../../features/campaign/components/RoleActivityFeed';
import { AttackRecordList } from '../../features/campaign/components/AttackRecordList';
import {
  useCampaign,
  useCampaignPlan,
  useCampaignRecords,
  useCreateCampaignReport,
  useRunCampaign
} from '../../lib/api/hooks';
import { useCampaignStream } from '../../lib/ws/useCampaignStream';
import { useToast } from '../../components/layout/ToastHost';
import { errorMessage } from '../../lib/api/errors';
import { fmtDateTime } from '../../lib/utils/format';
import type { CampaignPlan } from '@xian/types';

/** 模式一 CampaignLive（技术方案 8.4）：顶部进度/预算 + 角色活动流 + 攻击记录。 */
export default function CampaignLivePage() {
  const { campaignId = '' } = useParams();
  const campaign = useCampaign(campaignId);
  /* 汇总 token 消耗需要全量记录，不能只取第一页 */
  const records = useCampaignRecords(campaignId, 1, 100);
  const run = useRunCampaign(campaignId);
  const makeReport = useCreateCampaignReport(campaignId);
  const planMut = useCampaignPlan();
  const toast = useToast();
  useCampaignStream(campaignId);

  if (campaign.isLoading) return <p className="text-sm text-content-muted">加载中…</p>;
  if (campaign.isError) return <ErrorState message={errorMessage(campaign.error)} onRetry={() => campaign.refetch()} />;
  if (!campaign.data) return <p className="text-sm text-content-muted">战役不存在</p>;

  const c = campaign.data;
  const plan = c.plan_dag as unknown as CampaignPlan | null;
  const budget = c.budget as { token?: number; cases?: number; minutes?: number };
  const attacking = c.status === 'attacking' || c.status === 'preparing';

  const totalTokens = records.data?.items.reduce((sum, r) => sum + r.tokens, 0) ?? 0;

  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-40 overflow-hidden">
        <RadarBackdrop attacking={attacking} />
      </div>

      <div className="relative">
        <PageHeader
          title={`战役 ${c.id.slice(0, 12)}`}
          description={`Agent ${c.agent_id.slice(0, 8)} · ${c.judge_mode} 裁判 · ${c.output_mode} 产出`}
          actions={
            <>
              <CampaignStatusBadge status={c.status} />
              <Button
                loading={run.isPending}
                disabled={c.status === 'completed'}
                onClick={async () => {
                  try {
                    const res = await run.mutateAsync();
                    toast.success('战役已执行完成', `命中 ${res.success ?? 0} / ${res.executed ?? 0}`);
                    campaign.refetch();
                  } catch (e) {
                    toast.error('执行失败', errorMessage(e));
                  }
                }}
              >
                {c.status === 'draft' ? '一键执行' : '重新执行'}
              </Button>
              <Button
                variant="outline"
                loading={makeReport.isPending}
                onClick={async () => {
                  try {
                    const report = await makeReport.mutateAsync();
                    toast.success('报告已生成', 'SecScore ' + report.sec_score);
                  } catch (e) {
                    toast.error('报告生成失败', errorMessage(e));
                  }
                }}
              >
                生成九章报告
              </Button>
              <Button variant="ghost" asChild>
                <Link to="/campaigns">返回列表</Link>
              </Button>
            </>
          }
        />

        <div className="grid gap-4 lg:grid-cols-4">
          <Card className="lg:col-span-3">
            <CardContent className="flex flex-wrap items-center gap-6">
              <MetricRing value={c.progress} label="战役进度" tone="blue" />
              <div className="min-w-[180px] flex-1">
                <p className="mb-1 text-xs text-content-faint">执行进度</p>
                <Progress value={c.progress} tone={c.status === 'attacking' ? 'red' : 'blue'} />
                <p className="mt-2 text-xs text-content-muted">
                  已消耗 token {totalTokens} / 预算 {budget.token ?? '—'}
                </p>
                <p className="mt-1 text-[11px] text-content-faint">
                  {c.started_at ? `开始 ${fmtDateTime(c.started_at)}` : '未开始'}
                  {c.ended_at ? ` · 结束 ${fmtDateTime(c.ended_at)}` : ''}
                </p>
              </div>
              {c.sec_score !== null ? (
                <MetricRing value={c.sec_score} label={`SecScore ${c.grade ?? ''}`} tone={c.sec_score >= 80 ? 'success' : c.sec_score >= 60 ? 'coach' : 'red'} />
              ) : null}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>攻击类别</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-1">
              {c.scope.length === 0 ? <span className="text-xs text-content-faint">未选择</span> : null}
              {c.scope.map((s) => (
                <Badge key={s} tone="blue">
                  {s}
                </Badge>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_360px]">
          <Card>
            <CardHeader>
              <CardTitle>DAG 计划</CardTitle>
              <Badge tone={plan?.dag_nodes?.length ? 'blue' : 'neutral'}>{plan?.dag_nodes?.length ?? 0} 节点</Badge>
            </CardHeader>
            <CardContent>
              <PlanPreview plan={plan} />
              {plan?.dag_nodes?.length ? null : (
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3 w-full"
                  loading={planMut.isPending}
                  onClick={async () => {
                    try {
                      await planMut.mutateAsync(campaignId);
                      toast.success('计划已生成', 'DAG 已落库，可开始执行');
                    } catch (e) {
                      toast.error('计划生成失败', errorMessage(e));
                    }
                  }}
                >
                  生成 DAG 计划
                </Button>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>角色活动流</CardTitle>
              <Badge tone={attacking ? 'red' : 'neutral'}>{attacking ? 'running' : 'idle'}</Badge>
            </CardHeader>
            <CardContent>
              <RoleActivityFeed />
            </CardContent>
          </Card>
        </div>

        <Card className="mt-4">
          <CardHeader>
            <CardTitle>攻击记录</CardTitle>
          </CardHeader>
          <CardContent>
            <AttackRecordList campaignId={campaignId} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}