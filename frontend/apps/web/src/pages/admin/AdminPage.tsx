import { useState } from 'react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  DataTable,
  Field,
  Input,
  Switch,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  type Column
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { TableSkeleton } from '../../components/ui/Loading';
import { ErrorState } from '@xian/ui';
import { useGateRules, useMembers, useScanJobs } from '../../lib/api/hooks';
import { errorHint, errorMessage } from '../../lib/api/errors';
import { ROLE_LABEL } from '@xian/types';
import type { GateRule, Member, ScanJob } from '@xian/types';
import { api } from '../../lib/api/client';
import { ROUTES } from '@xian/types';
import { useToast } from '../../components/layout/ToastHost';
import { useQuery } from '@tanstack/react-query';
import { LlmGatewayCard } from './LlmGatewayCard';

/** 管理后台：成员 / 门禁规则 / 扫描任务 / 审计检索（技术方案 8.4）。 */
export default function AdminPage() {
  const members = useMembers();
  const gates = useGateRules();
  const jobs = useScanJobs();
  const toast = useToast();
  const [auditAction, setAuditAction] = useState('');

  const audit = useQuery({
    queryKey: ['audit-logs', auditAction],
    queryFn: () => api.get<Record<string, unknown>[]>(ROUTES.adminAuditLogs, { action: auditAction || undefined })
  });

  const memberCols: Column<Member>[] = [
    { key: 'email', header: '邮箱', render: (m) => m.email },
    { key: 'name', header: '姓名', render: (m) => m.name },
    { key: 'role', header: '角色', render: (m) => <Badge tone={m.role === 'admin' ? 'danger' : 'blue'}>{ROLE_LABEL[m.role]}</Badge> },
    { key: 'status', header: '状态', render: (m) => <Badge tone={m.status === 'active' ? 'success' : 'neutral'}>{m.status}</Badge> }
  ];

  const gateCols: Column<GateRule>[] = [
    { key: 'drop', header: '最大允许跌幅', render: (g) => <span className="font-mono">{g.max_score_drop}</span> },
    { key: 'severity', header: '阻断等级', render: (g) => <Badge tone="danger">{g.block_on_severity}</Badge> },
    {
      key: 'enabled',
      header: '启用',
      render: (g) => <Switch checked={g.enabled} onCheckedChange={() => toast.info('规则更新需走服务端保存')} />
    }
  ];

  const jobCols: Column<ScanJob>[] = [
    { key: 'id', header: '任务 ID', render: (j) => <span className="font-mono text-xs">{j.id.slice(0, 12)}</span> },
    { key: 'agent', header: 'Agent', render: (j) => <span className="font-mono text-xs">{j.agent_id.slice(0, 8)}</span> },
    { key: 'trigger', header: '触发方式', render: (j) => j.trigger },
    { key: 'status', header: '状态', render: (j) => <Badge tone={j.status === 'done' ? 'success' : j.status === 'failed' ? 'danger' : 'coach'}>{j.status}</Badge> },
    { key: 'verdict', header: '结论', render: (j) => j.verdict ?? '—' },
    { key: 'exit', header: '退出码', render: (j) => <span className="font-mono">{j.exit_code ?? '—'}</span> },
    { key: 'pipeline', header: 'CI 流水线', render: (j) => (j.pipeline_url ? <a className="text-xs text-blue-team" href={j.pipeline_url} target="_blank" rel="noreferrer">查看</a> : '—') }
  ];

  return (
    <div>
      <PageHeader title="管理后台" description="成员与权限、CI 门禁规则、扫描任务与审计检索（PRD 3.9）。" />

      <div className="mb-4">
        <LlmGatewayCard />
      </div>

      <Card>
        <CardContent>
          <Tabs defaultValue="members">
            <TabsList>
              <TabsTrigger value="members">成员</TabsTrigger>
              <TabsTrigger value="gate">门禁规则</TabsTrigger>
              <TabsTrigger value="jobs">扫描任务</TabsTrigger>
              <TabsTrigger value="audit">审计检索</TabsTrigger>
            </TabsList>

            <TabsContent value="members">
              {members.isLoading ? (
                <TableSkeleton />
              ) : members.isError ? (
                <ErrorState message={errorMessage(members.error)} hint={errorHint(members.error)} onRetry={() => members.refetch()} />
              ) : (
                <DataTable columns={memberCols} rows={members.data ?? []} rowKey={(m) => m.id} emptyTitle="暂无成员" />
              )}
            </TabsContent>

            <TabsContent value="gate">
              {gates.isLoading ? (
                <TableSkeleton />
              ) : (
                <DataTable columns={gateCols} rows={gates.data ?? []} rowKey={(g) => g.id} emptyTitle="暂无门禁规则" />
              )}
              <p className="mt-3 text-[11px] text-content-faint">
                AC-11：SecScore 相对基线跌幅 &gt; {gates.data?.[0]?.max_score_drop ?? 5} 分即判 fail，CI 阻断合并。
              </p>
            </TabsContent>

            <TabsContent value="jobs">
              {jobs.isLoading ? (
                <TableSkeleton />
              ) : (
                <DataTable columns={jobCols} rows={jobs.data ?? []} rowKey={(j) => j.id} emptyTitle="暂无扫描任务" />
              )}
            </TabsContent>

            <TabsContent value="audit" className="space-y-3">
              <div className="flex flex-wrap items-end gap-3">
                <Field label="按动作检索" id="audit-action" className="w-72">
                  <Input id="audit-action" value={auditAction} onChange={(e) => setAuditAction(e.target.value)} placeholder="如 agent.create / report.export" />
                </Field>
                <Button variant="outline" onClick={() => audit.refetch()}>
                  检索
                </Button>
              </div>
              <pre className="max-h-80 overflow-auto rounded-control border border-border bg-sunken p-3 font-mono text-[11px]">
                {JSON.stringify(audit.data ?? [], null, 2)}
              </pre>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}