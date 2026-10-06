import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, Card, DataTable, Pagination, type Column } from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { CampaignStatusBadge } from '../../components/ui/badges';
import { TableSkeleton } from '../../components/ui/Loading';
import { useCampaigns } from '../../lib/api/hooks';
import { fmtDateTime } from '../../lib/utils/format';
import type { Campaign, CampaignStatus } from '@xian/types';

/** 战役列表页。 */
export default function CampaignsPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<CampaignStatus | 'all'>('all');
  const campaigns = useCampaigns();
  const rows = (campaigns.data ?? []).filter((c) => status === 'all' || c.status === status);

  const columns: Column<Campaign>[] = [
    {
      key: 'id',
      header: '战役 ID',
      render: (c) => (
        <Link to={`/campaigns/${c.id}`} className="font-mono text-xs text-blue-team hover:underline">
          {c.id.slice(0, 12)}
        </Link>
      )
    },
    { key: 'agent', header: 'Agent', render: (c) => <span className="font-mono text-xs">{c.agent_id.slice(0, 8)}</span> },
    { key: 'scope', header: '类别数', render: (c) => c.scope.length },
    { key: 'intensity', header: '强度', render: (c) => <span className="text-xs">{c.intensity}</span> },
    { key: 'status', header: '状态', render: (c) => <CampaignStatusBadge status={c.status} /> },
    { key: 'sec_score', header: 'SecScore', render: (c) => <span className="font-mono">{c.sec_score ?? '—'}</span> },
    { key: 'progress', header: '进度', render: (c) => `${c.progress}%` },
    { key: 'created', header: '创建时间', render: (c) => <span className="text-xs">{fmtDateTime(c.created_at)}</span> }
  ];

  const statuses: CampaignStatus[] = ['draft', 'preparing', 'attacking', 'analyzing', 'reporting', 'completed', 'cancelled', 'tripped', 'env_failed', 'scheduled'];

  return (
    <div>
      <PageHeader
        title="模式一 · 战役"
        description="自动化红蓝对抗：DAG 编排 → 环境准备 → 攻击执行 → 判定 → 报告。"
        actions={
          <Button asChild>
            <Link to="/campaigns/new">发起战役</Link>
          </Button>
        }
      />

      <Card>
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3">
          {(['all', ...statuses] as const).map((s) => (
            <button
              key={s}
              type="button"
              className={`rounded-pill border px-2.5 py-1 text-xs ${
                status === s ? 'border-blue-team text-blue-team' : 'border-border text-content-muted hover:text-content'
              }`}
              onClick={() => setStatus(s)}
            >
              {s === 'all' ? '全部' : s}
            </button>
          ))}
        </div>
        {campaigns.isLoading ? (
          <TableSkeleton />
        ) : (
          <>
            <DataTable columns={columns} rows={rows} rowKey={(c) => c.id} emptyTitle="还没有战役" />
            <Pagination page={page} size={20} total={rows.length} onPageChange={setPage} />
          </>
        )}
      </Card>
    </div>
  );
}