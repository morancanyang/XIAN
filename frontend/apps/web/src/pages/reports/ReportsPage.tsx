import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Badge, Card, DataTable, Pagination, type Column, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { TableSkeleton } from '../../components/ui/Loading';
import { ErrorState } from '@xian/ui';
import { useReports } from '../../lib/api/hooks';
import { errorHint, errorMessage } from '../../lib/api/errors';
import { fmtDateTime } from '../../lib/utils/format';
import type { Report } from '@xian/types';

/** 报告中心列表。 */
export default function ReportsPage() {
  const [page, setPage] = useState(1);
  const [kind, setKind] = useState<'all' | 'campaign' | 'agent'>('all');
  const reports = useReports();

  const rows = (reports.data ?? []).filter((r) => kind === 'all' || r.subject_type === kind);

  const columns: Column<Report>[] = [
    {
      key: 'id',
      header: '报告 ID',
      render: (r) => (
        <Link to={`/reports/${r.id}`} className="font-mono text-xs text-blue-team hover:underline">
          {r.id.slice(0, 12)}
        </Link>
      )
    },
    { key: 'type', header: '类型', render: (r) => <Badge tone={r.subject_type === 'campaign' ? 'blue' : 'coach'}>{r.subject_type}</Badge> },
    { key: 'subject', header: '对象', render: (r) => <span className="font-mono text-xs">{r.subject_id.slice(0, 8)}</span> },
    {
      key: 'score',
      header: 'SecScore',
      render: (r) => (
        <span className={r.sec_score >= 80 ? 'font-mono text-success' : r.sec_score >= 60 ? 'font-mono text-coach' : 'font-mono text-danger'}>
          {r.sec_score} ({r.grade})
        </span>
      )
    },
    { key: 'version', header: '版本', render: (r) => `v${r.version}` },
    { key: 'created', header: '生成时间', render: (r) => <span className="text-xs">{fmtDateTime(r.created_at)}</span> }
  ];

  return (
    <div>
      <PageHeader title="报告中心" description="九章报告 · 多格式导出 · 脱敏分享（PRD 3.8.4）。" />
      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3">
          <Select value={kind} onValueChange={(v) => setKind(v as 'all' | 'campaign' | 'agent')}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              <SelectItem value="campaign">战役报告</SelectItem>
              <SelectItem value="agent">资产报告</SelectItem>
            </SelectContent>
          </Select>
          <span className="ml-auto text-xs text-content-faint">共 {rows.length} 份</span>
        </div>
        {reports.isLoading ? (
          <TableSkeleton />
        ) : reports.isError ? (
          <ErrorState message={errorMessage(reports.error)} hint={errorHint(reports.error)} onRetry={() => reports.refetch()} />
        ) : (
          <>
            <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} emptyTitle="还没有报告" />
            <Pagination page={page} size={20} total={rows.length} onPageChange={setPage} />
          </>
        )}
      </Card>
    </div>
  );
}