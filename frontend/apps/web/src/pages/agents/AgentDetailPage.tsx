import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CodeBlock,
  Progress,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Field,
  Input,
  ScrollArea
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { AgentStatusBadge } from '../../components/ui/badges';
import { ErrorState, EmptyState } from '@xian/ui';
import { useToast } from '../../components/layout/ToastHost';
import {
  useAgent,
  useAgentHealthcheck,
  useAgentRecon,
  useAgentRecommendations,
  useAgentVersions,
  useCreateAgentVersion,
  useUpdateAgent,
  useVerifyAgent
} from '../../lib/api/hooks';
import { errorHint, errorMessage } from '../../lib/api/errors';
import { fmtDateTime } from '../../lib/utils/format';
import { RadarScore } from '@xian/ui';

/** 从 Agent 端点取主机名，作为 DNS TXT 校验的默认目标；解析不了时退回占位域名。 */
function hostOf(endpoint: string): string {
  const raw = (endpoint || '').trim();
  if (!raw) return 'agent.example.com';
  try {
    return new URL(raw).hostname || 'agent.example.com';
  } catch {
    return raw.replace(/^[a-z][a-z0-9+.-]*:\/\//i, '').split('/')[0] || 'agent.example.com';
  }
}

/** Agent 详情：三步骤（归属校验 / 健康探测 / 侦察画像）+ 版本与场景推荐。 */
export default function AgentDetailPage() {
  const { agentId = '' } = useParams();
  const agent = useAgent(agentId);
  const verify = useVerifyAgent(agentId);
  const health = useAgentHealthcheck(agentId);
  const recon = useAgentRecon(agentId);
  const versions = useAgentVersions(agentId);
  const recommendations = useAgentRecommendations(agentId);
  const createVersion = useCreateAgentVersion(agentId);
  const update = useUpdateAgent(agentId);
  const toast = useToast();

  const [method, setMethod] = useState<'dns_txt' | 'image_digest'>('dns_txt');
  const [target, setTarget] = useState('');
  const [targetTouched, setTargetTouched] = useState(false);

  if (agent.isLoading) return <p className="text-sm text-content-muted">加载中…</p>;
  if (agent.isError) return <ErrorState message={errorMessage(agent.error)} hint={errorHint(agent.error)} onRetry={() => agent.refetch()} />;
  if (!agent.data) return <EmptyState title="Agent 不存在" glitch />;

  const a = agent.data;

  // 校验目标默认取 Agent 端点主机名。原先硬编码占位域名 agent.example.com，
  // 用户照着实测必然失败：那个域名既没有对应 TXT 记录，也不属于被接入的 Agent。
  // 用户手动改过就以用户为准（targetTouched）；镜像摘要方式不预填。
  const effectiveTarget = targetTouched ? target : method === 'dns_txt' ? hostOf(a.endpoint) : '';

  return (
    <div>
      <PageHeader
        title={a.name}
        description={`${a.access_type} · ${a.endpoint}`}
        actions={<AgentStatusBadge status={a.status} />}
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>接入向导</CardTitle>
            <p className="text-xs text-content-muted">三步完成：归属校验 → 健康探测 → 侦察画像</p>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="verify">
              <TabsList>
                <TabsTrigger value="verify">1. 归属校验</TabsTrigger>
                <TabsTrigger value="health">2. 健康探测</TabsTrigger>
                <TabsTrigger value="recon">3. 侦察画像</TabsTrigger>
              </TabsList>

              <TabsContent value="verify">
                <div className="space-y-4">
                  <Field label="校验方式" id="v-method">
                    <Select value={method} onValueChange={(v) => setMethod(v as 'dns_txt' | 'image_digest')}>
                      <SelectTrigger id="v-method">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="dns_txt">DNS TXT 记录</SelectItem>
                        <SelectItem value="image_digest">镜像摘要 image@sha256:...</SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field label="目标" id="v-target" hint="DNS 填域名；镜像填 digest 引用。">
                    <Input
                      id="v-target"
                      value={effectiveTarget}
                      onChange={(e) => {
                        setTargetTouched(true);
                        setTarget(e.target.value);
                      }}
                      className="font-mono text-xs"
                    />
                  </Field>
                  <CodeBlock>
                    {method === 'dns_txt'
                      ? verify.data?.nonce
                        ? `# 在域名解析中添加下面这条 TXT 记录，保存后重新点「开始校验」
${effectiveTarget}.  IN TXT  "xian-verify=${verify.data.nonce}"`
                        : '# 先点下方「开始校验」生成一次性校验值，再按这里给出的记录去配 DNS'
                      : `# 提供镜像 ${effectiveTarget || '<image>'} 的不可变摘要
image@sha256:<64位十六进制>`}
                  </CodeBlock>
                  <Button
                    loading={verify.isPending}
                    onClick={async () => {
                      try {
                        const rec = await verify.mutateAsync({ method, target: effectiveTarget });
                        toast.success('校验完成', rec.detail);
                        agent.refetch();
                      } catch (e) {
                        toast.error('校验失败', errorMessage(e));
                      }
                    }}
                  >
                    开始校验
                  </Button>
                  {verify.data ? (
                    <div className="rounded-control border border-border bg-elevated p-3 text-xs">
                      <p>
                        结果：<Badge tone={verify.data.result === 'verified' ? 'success' : 'warning'}>{verify.data.result}</Badge>
                      </p>
                      <p className="mt-1 text-content-muted">{verify.data.detail}</p>
                      {verify.data.result !== 'verified' ? (
                        <p className="mt-1 text-content-faint">
                          校验值不会变：补齐记录后重新点一次「开始校验」即可。
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </TabsContent>

              <TabsContent value="health">
                <div className="space-y-3">
                  <Button
                    variant="outline"
                    loading={health.isPending}
                    onClick={async () => {
                      try {
                        await health.mutateAsync();
                        toast.success('探测完成');
                      } catch (e) {
                        toast.error('探测失败', errorMessage(e));
                      }
                    }}
                  >
                    发起健康探测
                  </Button>
                  {health.data ? (
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div className="rounded-control border border-border bg-elevated p-3">
                        <p className="text-content-faint">延迟 P50</p>
                        <p className="font-mono text-lg">{health.data.latency_ms} ms</p>
                      </div>
                      <div className="rounded-control border border-border bg-elevated p-3">
                        <p className="text-content-faint">结果</p>
                        <p className="font-mono text-lg">{health.data.result}</p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-content-faint">尚未探测。健康探测会打点延迟与最小可用样本。</p>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="recon">
                <div className="space-y-3">
                  <Button
                    variant="outline"
                    loading={recon.isPending}
                    onClick={async () => {
                      try {
                        await recon.mutateAsync();
                        toast.success('侦察完成', '已生成六件套画像');
                      } catch (e) {
                        toast.error('侦察失败', errorMessage(e));
                      }
                    }}
                  >
                    运行侦察兵（六件套）
                  </Button>
                  {recon.data ? (
                    <div className="grid gap-4 md:grid-cols-[1fr_260px]">
                      <ScrollArea className="h-64 rounded-control border border-border bg-sunken p-3">
                        <p className="mb-2 text-xs text-content-faint">工具清单（{recon.data.tools.length}）</p>
                        <ul className="space-y-1 font-mono text-[11px] text-content-muted">
                          {recon.data.tools.map((t, i) => (
                            <li key={i}>{JSON.stringify(t)}</li>
                          ))}
                        </ul>
                        <p className="mb-2 mt-3 text-xs text-content-faint">拒答边界</p>
                        <p className="text-xs text-content">{recon.data.refusal_boundary || '未探测到明确边界'}</p>
                      </ScrollArea>
                      <div className="flex flex-col items-center justify-center">
                        <RadarScore data={Object.fromEntries(Object.entries(recon.data.risk_levels).map(([k, v]) => [k, v === 'high' ? 90 : v === 'medium' ? 60 : 30]))} size={220} />
                        <p className="mt-2 text-[11px] text-content-faint">P50 {recon.data.latency_p50}ms · P99 {recon.data.latency_p99}ms</p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-content-faint">尚未侦察。侦察会抽取工具清单、风险分级与拒答边界。</p>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>画像摘要</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div>
                <p className="text-content-faint">防护基线</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {Object.entries(a.baseline_declaration).map(([k, v]) => (
                    <Badge key={k} tone={v ? 'success' : 'neutral'}>
                      {k}: {String(v)}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-content-faint">创建时间</p>
                <p>{fmtDateTime(a.created_at)}</p>
              </div>
              <div>
                <p className="text-content-faint">版本数</p>
                <p>{versions.data?.length ?? 0}</p>
              </div>
              <div>
                <p className="text-content-faint">状态推进</p>
                <Progress value={a.ownership_verified ? 66 : 33} tone={a.ownership_verified ? 'success' : 'coach'} />
                <p className="mt-1 text-content-faint">{a.ownership_verified ? '归属校验已通过' : '等待归属校验'}</p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  try {
                    await createVersion.mutateAsync({ source: 'manual', prompt_hash: `manual-${Date.now()}` });
                    toast.success('已登记版本');
                  } catch (e) {
                    toast.error('登记失败', errorMessage(e));
                  }
                }}
              >
                登记新版本
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>场景推荐</CardTitle>
              <p className="text-xs text-content-muted">按 match_score 排序，matched_tools 命中画像工具</p>
            </CardHeader>
            <CardContent>
              {recommendations.data?.length ? (
                <ul className="space-y-2">
                  {recommendations.data.map((r) => (
                    <li key={r.scenario_id} className="rounded-control border border-border bg-elevated p-2">
                      <div className="flex items-center justify-between gap-2">
                        <Link to="/scenarios" className="text-xs text-blue-team hover:underline">
                          {r.name}
                        </Link>
                        <Badge tone="blue">{Math.round(r.match_score * 100)}%</Badge>
                      </div>
                      <p className="mt-1 text-[11px] text-content-faint">{r.reason}</p>
                      <p className="mt-1 font-mono text-[10px] text-content-faint">{r.matched_tools.join(', ')}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-content-faint">完成侦察后可获得场景推荐。</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>状态流转</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2">
          {(['unverified', 'active', 'testing', 'offline', 'archived'] as const)
            .filter((s) => s !== 'unverified' || !a.ownership_verified)
            .map((s) => (
              <Button
                key={s}
                size="sm"
                variant={a.status === s ? 'primary' : 'outline'}
                onClick={async () => {
                  try {
                    await update.mutateAsync({ status: s });
                    toast.success('状态已更新', s);
                  } catch (e) {
                    toast.error('更新失败', errorMessage(e));
                  }
                }}
              >
                {s}
              </Button>
            ))}
        </CardContent>
      </Card>
    </div>
  );
}