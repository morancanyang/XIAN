import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Badge,
  Button,
  Card,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Field,
  Input,
  Pagination,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Switch,
  Textarea
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { ParticlesBackdrop } from '../../features/dashboard/components/ParticlesBackdrop';
import { AgentStatusBadge } from '../../components/ui/badges';
import { TableSkeleton } from '../../components/ui/Loading';
import { ErrorState } from '@xian/ui';
import { useAgents, useCreateAgent } from '../../lib/api/hooks';
import { errorHint, errorMessage } from '../../lib/api/errors';
import { useToast } from '../../components/layout/ToastHost';
import { fmtDateTime } from '../../lib/utils/format';
import { DataTable, type Column } from '@xian/ui';
import type { Agent, AgentStatus, BaselineDeclaration } from '@xian/types';

const STATUS_FILTERS: (AgentStatus | 'all')[] = ['all', 'unverified', 'active', 'testing', 'offline', 'archived'];

/** Agent 资产页：三步骤接入向导 + 资产列表（技术方案 8.4）。 */
export default function AgentsPage() {
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState<AgentStatus | 'all'>('all');
  const [createOpen, setCreateOpen] = useState(false);

  const query = useAgents({ page, size, keyword: keyword || undefined });
  const create = useCreateAgent();
  const toast = useToast();

  const rows = (query.data?.items ?? []).filter((a) => status === 'all' || a.status === status);

  const columns: Column<Agent>[] = [
    {
      key: 'name',
      header: '名称',
      render: (a) => (
        <Link to={`/agents/${a.id}`} className="text-blue-team hover:underline">
          {a.name}
        </Link>
      )
    },
    { key: 'access_type', header: '接入方式', render: (a) => <Badge>{a.access_type}</Badge> },
    {
      key: 'endpoint',
      header: '端点',
      render: (a) => <span className="font-mono text-xs text-content-muted">{a.endpoint}</span>
    },
    { key: 'ownership', header: '归属校验', render: (a) => (a.ownership_verified ? <Badge tone="success">已验证</Badge> : <Badge tone="warning">未验证</Badge>) },
    { key: 'status', header: '状态', render: (a) => <AgentStatusBadge status={a.status} /> },
    { key: 'created_at', header: '创建时间', render: (a) => <span className="text-xs">{fmtDateTime(a.created_at)}</span> }
  ];

  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-48 overflow-hidden">
        <ParticlesBackdrop />
      </div>
      <PageHeader
        title="Agent 资产"
        description="接入 → 归属校验 → 健康探测 → 演练。未完成归属校验的 Agent 不允许发起战役（PRD 3.2.1）。"
        actions={
          <Button onClick={() => setCreateOpen(true)}>接入 Agent</Button>
        }
      />

      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3">
          <Input
            placeholder="搜索名称 / 端点"
            value={keyword}
            onChange={(e) => {
              setKeyword(e.target.value);
              setPage(1);
            }}
            className="max-w-xs"
          />
          <Select value={status} onValueChange={(v) => setStatus(v as AgentStatus | 'all')}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_FILTERS.map((s) => (
                <SelectItem key={s} value={s}>
                  {s === 'all' ? '全部状态' : s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="ml-auto text-xs text-content-faint">共 {query.data?.total ?? 0} 条</span>
        </div>

        {query.isLoading ? (
          <TableSkeleton />
        ) : query.isError ? (
          <ErrorState message={errorMessage(query.error)} hint={errorHint(query.error)} onRetry={() => query.refetch()} />
        ) : (
          <>
            <DataTable columns={columns} rows={rows} rowKey={(a) => a.id} emptyTitle="还没有接入 Agent" />
            <Pagination
              page={query.data?.page ?? 1}
              size={query.data?.size ?? 20}
              total={query.data?.total ?? 0}
              onPageChange={setPage}
              onSizeChange={(s) => {
                setSize(s);
                setPage(1);
              }}
            />
          </>
        )}
      </Card>

      <CreateAgentDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={async (body) => {
          try {
            await create.mutateAsync(body);
            toast.success('已创建 Agent', '请继续完成归属校验');
            setCreateOpen(false);
          } catch (err) {
            toast.error('创建失败', errorMessage(err));
          }
        }}
        loading={create.isPending}
      />
    </div>
  );
}

function CreateAgentDialog({
  open,
  onOpenChange,
  onSubmit,
  loading
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSubmit: (body: {
    name: string;
    access_type: Agent['access_type'];
    endpoint: string;
    description?: string;
    baseline_declaration?: Partial<BaselineDeclaration>;
  }) => Promise<void>;
  loading: boolean;
}) {
  const [name, setName] = useState('');
  const [access, setAccess] = useState<Agent['access_type']>('http');
  const [endpoint, setEndpoint] = useState('');
  const [description, setDescription] = useState('');
  const [guardrail, setGuardrail] = useState(false);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>接入 Agent</DialogTitle>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={async (e) => {
            e.preventDefault();
            await onSubmit({
              name,
              access_type: access,
              endpoint,
              description,
              baseline_declaration: { has_guardrail: guardrail }
            });
          }}
        >
          <Field label="名称" required id="agent-name">
            <Input id="agent-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="接入方式" id="agent-access">
            <Select value={access} onValueChange={(v) => setAccess(v as Agent['access_type'])}>
              <SelectTrigger id="agent-access">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="http">HTTP 接口</SelectItem>
                <SelectItem value="sdk">SDK 接入</SelectItem>
                <SelectItem value="container">容器镜像</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="端点" required id="agent-endpoint" hint="HTTP 填完整 URL；容器填镜像引用。">
            <Input id="agent-endpoint" value={endpoint} onChange={(e) => setEndpoint(e.target.value)} required className="font-mono text-xs" />
          </Field>
          <Field label="描述" id="agent-desc">
            <Textarea id="agent-desc" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
          </Field>
          <label className="flex items-center gap-2 text-sm text-content-muted">
            <Switch checked={guardrail} onCheckedChange={setGuardrail} />
            已部署防护栏（guardrail）
          </label>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" loading={loading}>
              创建
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}