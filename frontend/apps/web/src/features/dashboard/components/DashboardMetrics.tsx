import { useQuery } from '@tanstack/react-query';
import { StatCard } from '../../../components/ui/StatCard';
import { api } from '../../../lib/api/client';
import { ROUTES } from '@xian/types';
import { useAgents, useCampaigns, useReports } from '../../../lib/api/hooks';

/** 驾驶舱四项核心指标（技术方案 8.4：顶部 4 指标卡）。 */
export function DashboardMetrics() {
  const agents = useAgents({ page: 1, size: 1 });
  const campaigns = useCampaigns();
  const reports = useReports();
  const scenarios = useQuery({ queryKey: ['scenarios'], queryFn: () => api.get<unknown[]>(ROUTES.scenarios) });

  const totalAgents = agents.data?.total ?? 0;
  const verified = agents.data?.items.filter((a) => a.ownership_verified).length ?? 0;
  const active = campaigns.data?.filter((c) => c.status === 'attacking' || c.status === 'preparing').length ?? 0;
  const latest = reports.data?.[0];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        label="纳管 Agent"
        value={totalAgents}
        suffix="个"
        hint={`其中 ${verified} 个已完成归属校验`}
        tone="blue"
      />
      <StatCard label="进行中战役" value={active} suffix="场" hint="模式一自动化演练" tone="red" />
      <StatCard
        label="最新 SecScore"
        value={latest?.sec_score ?? 0}
        suffix={` / ${latest?.grade ?? '—'}`}
        hint={latest ? `报告 ${shortId(latest.id)}` : '尚无报告'}
        tone={latest && latest.sec_score >= 80 ? 'success' : latest && latest.sec_score >= 60 ? 'coach' : 'red'}
      />
      <StatCard label="靶场场景" value={scenarios.data?.length ?? 0} suffix="套" hint="六要素场景模板" tone="coach" />
    </div>
  );
}

function shortId(id: string): string {
  return id.length > 8 ? id.slice(0, 8) : id;
}