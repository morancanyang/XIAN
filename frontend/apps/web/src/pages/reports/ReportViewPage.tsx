import { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  AttackPathGraph,
  Badge,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Input,
  RadarScore,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { DarkVeilBackdrop } from '../../features/report/components/DarkVeilBackdrop';
import { ChapterNav } from '../../features/report/components/ChapterNav';
import { recordEvidence } from '../../features/campaign/components/recordBits';
import { useExportReport, useRecordTrace, useReport, useShareReport } from '../../lib/api/hooks';
import { useToast } from '../../components/layout/ToastHost';
import { errorMessage } from '../../lib/api/errors';
import { CHAPTERS, type TraceEvent } from '@xian/types';
import { desensitize } from '../../lib/utils/desensitize';

/** 报告正文各章的宽松视图：后端 chapters 是动态 JSON，按字段名就地取用。 */
type Row = Record<string, unknown>;

const num = (value: unknown, digits = 2): string => {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n.toFixed(digits) : (0).toFixed(digits);
};

const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

const text = (value: unknown, fallback = ''): string =>
  value === null || value === undefined ? fallback : String(value);

/** kill chain 五阶段中文名（与后端 STAGE_LABELS 对齐）。 */
const STAGE_LABELS: Record<string, string> = {
  recon: '侦察',
  delivery: '载荷投递',
  privilege_escalation: '提权',
  exfiltration: '渗出',
  impact: '影响'
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: '严重',
  high: '高危',
  medium: '中危',
  low: '低危',
  info: '提示'
};

const SEVERITY_TONES: Record<string, 'danger' | 'warning' | 'coach' | 'neutral'> = {
  critical: 'danger',
  high: 'danger',
  medium: 'warning',
  low: 'coach',
  info: 'neutral'
};

const PRIORITY_TONES: Record<string, 'danger' | 'warning' | 'coach'> = {
  P0: 'danger',
  P1: 'warning',
  P2: 'coach'
};

/** kill chain 固定顺序：攻击路径图按此分列。 */
const STAGE_ORDER = ['recon', 'delivery', 'privilege_escalation', 'exfiltration', 'impact'];

const EVENT_LABELS: Record<string, string> = {
  llm_call: '模型调用',
  tool_call: '工具调用',
  output: '输出',
  egress: '外联',
  guardrail: '护栏',
  token: '计费'
};
/** 报告阅读（技术方案 8.4）：章节导航 + 九章正文 + trace 回放。 */
export default function ReportViewPage() {
  const { reportId = '' } = useParams();
  const report = useReport(reportId);
  const exportMut = useExportReport(reportId);
  const shareMut = useShareReport(reportId);
  const toast = useToast();

  const [chapter, setChapter] = useState<string>(CHAPTERS[0]);
  const [exportOpen, setExportOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [format, setFormat] = useState('html');
  const [level, setLevel] = useState('standard');
  const [shareUrl, setShareUrl] = useState('');
  const [shareTtl, setShareTtl] = useState(72);
  const [levelFilter, setLevelFilter] = useState<'none' | 'partial' | 'full'>('partial');
  const [traceId, setTraceId] = useState('');
  // 第五章 trace 回放：按选中记录拉取完整判定过程（必须置于提前返回之前，保证 hooks 顺序稳定）
  const trace = useRecordTrace(traceId || undefined);

  if (report.isLoading) return <p className="text-sm text-content-muted">加载中…</p>;
  if (report.isError || !report.data) return <p className="text-sm text-danger">报告不存在或加载失败。</p>;

  const chapters = (report.data.chapters ?? report.data) as Row;
  const secScore = Number(report.data.sec_score ?? chapters.sec_score ?? 0);
  const grade = text(report.data.grade ?? chapters.grade, 'D');
  const summary = text(chapters.executive_summary);
  const topRisks = list(chapters.top_risks) as Row[];
  const categories = list(chapters.categories) as Row[];
  const highRisk = list(chapters.high_risk_cases) as Row[];
  const findings = list(chapters.findings) as Row[];
  const recommendationRows = list(chapters.recommendations) as Row[];
  const remediation = (chapters.remediation ?? {}) as Row;
  const matrix = (remediation.matrix ?? {}) as Record<string, Record<string, number>>;
  const attackPath = (chapters.attack_path ?? {}) as Row;
  const radar = (chapters.radar ?? {}) as Record<string, number>;
  const agent = (chapters.agent ?? {}) as Row;
  const baseline = (agent.baseline ?? {}) as Row;
  const benchmark = (chapters.benchmark ?? {}) as Row;
  const compliance = list(chapters.compliance) as Row[];
  const retest = (chapters.retest ?? {}) as Row;
  const versions = list(retest.versions) as Row[];
  const killChain = list(attackPath.kill_chain).map((s) => text(s));
  const pathNodes = list(attackPath.nodes) as Row[];
  const pathEdges = list(attackPath.edges) as Row[];
  const missingStages = list(attackPath.missing_stages).map((s) => text(s));
  const agentTools = list(agent.tools) as Row[];

  /** 命中详情的一行证据摘要：复用战役详情里的可解释口径。 */
  const evidenceOf = (row: Row): string =>
    recordEvidence({
      rule_hits: list(row.golden_rules),
      evidence: list(row.evidence)
    } as never);
  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <DarkVeilBackdrop />
      </div>

      <PageHeader
        title={`报告 ${reportId.slice(0, 12)}`}
        description={summary || '九章结构化报告'}
        actions={
          <>
            <Badge tone={secScore >= 80 ? 'success' : secScore >= 60 ? 'coach' : 'danger'}>
              SecScore {secScore} · {grade}
            </Badge>
            <Button variant="outline" onClick={() => setExportOpen(true)}>
              导出
            </Button>
            <Button onClick={() => setShareOpen(true)}>
              生成分享链接
            </Button>
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
        <Card className="h-fit">
          <CardContent className="p-2">
            <ChapterNav active={chapter} onSelect={setChapter} />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-5">
            {/* 第一章 执行摘要 */}
            {chapter === CHAPTERS[0] ? (
              <section>
                <p className="mb-2 font-mono text-[10px] text-content-faint">{CHAPTERS[0]}</p>
                <p className="text-sm leading-relaxed xian-cjk">{summary || '本报告暂无执行摘要。'}</p>

                <div className="mt-4 grid gap-3 md:grid-cols-[1fr_240px]">
                  <div>
                    <p className="mb-2 text-xs font-semibold text-content-muted">Top 风险</p>
                    <ul className="space-y-1">
                      {topRisks.map((r, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2 rounded-control border border-border bg-elevated px-3 py-2 text-xs"
                        >
                          <Badge tone={SEVERITY_TONES[text(r.severity, 'low')] ?? 'neutral'}>
                            {SEVERITY_LABELS[text(r.severity, 'low')] ?? text(r.severity, 'low')}
                          </Badge>
                          <span className="min-w-0 flex-1 text-content">
                            {text(r.title) || text(r.root_cause)}
                            <span className="ml-2 font-mono text-[11px] text-content-faint">
                              {text(r.case_id) || text(r.root_cause)}
                            </span>
                          </span>
                          <span className="font-mono text-[11px] text-content-faint">{num(r.confidence)}</span>
                        </li>
                      ))}
                      {topRisks.length === 0 ? <li className="text-xs text-content-faint">无高危项</li> : null}
                    </ul>
                  </div>
                  {Object.keys(radar).length >= 3 ? <RadarScore data={radar} size={220} /> : null}
                </div>

                <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
                  <div className="rounded-control border border-border bg-elevated p-3">
                    <p className="text-content-faint">ASR</p>
                    <p className="font-mono text-lg">{num(Number(chapters.asr ?? 0) * 100, 1)}%</p>
                  </div>
                  <div className="rounded-control border border-border bg-sunken p-3">
                    <p className="text-content-faint">可用性基线通过率</p>
                    <p className="font-mono text-lg">{num(Number(chapters.baseline_pass_rate ?? 1) * 100, 0)}%</p>
                  </div>
                  <div className="rounded-control border border-border bg-sunken p-3">
                    <p className="text-content-faint">最低分门槛</p>
                    <p className="font-mono text-lg">{text(chapters.min_score_gate, '0')}</p>
                  </div>
                </div>
              </section>
            ) : null}
            {/* 第二章 Agent 画像与攻击面清单 */}
            {chapter === CHAPTERS[1] ? (
              <section>
                <p className="mb-2 font-mono text-[10px] text-content-faint">{CHAPTERS[1]}</p>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-card border border-border bg-elevated p-3">
                    <p className="text-xs font-semibold text-content-muted">Agent 画像</p>
                    <dl className="mt-2 space-y-1 text-xs">
                      <div className="flex justify-between gap-2">
                        <dt className="text-content-faint">名称</dt>
                        <dd className="truncate text-content">{text(agent.name, '未命名')}</dd>
                      </div>
                      <div className="flex justify-between gap-2">
                        <dt className="text-content-faint">接入方式</dt>
                        <dd className="font-mono text-content">{text(agent.access_type, '-')}</dd>
                      </div>
                      <div className="flex justify-between gap-2">
                        <dt className="text-content-faint">端点</dt>
                        <dd className="max-w-[60%] truncate font-mono text-content" title={text(agent.endpoint)}>
                          {text(agent.endpoint) || '-'}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-2">
                        <dt className="text-content-faint">归属校验</dt>
                        <dd className={agent.ownership_verified ? 'text-success' : 'text-danger'}>
                          {agent.ownership_verified ? '已通过' : '未通过'}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-2">
                        <dt className="text-content-faint">延迟 P50 / P99</dt>
                        <dd className="font-mono text-content">
                          {text(agent.latency_p50, '0')} / {text(agent.latency_p99, '0')} ms
                        </dd>
                      </div>
                      <div className="flex justify-between gap-2">
                        <dt className="text-content-faint">蜜标类型</dt>
                        <dd className="font-mono text-content">
                          {list(agent.canary_types)
                            .map((c) => text(c))
                            .join(', ') || '-'}
                        </dd>
                      </div>
                    </dl>
                    <p className="mt-3 text-[11px] leading-relaxed text-content-faint">
                      拒绝边界：{text(agent.refusal_boundary, '未探测到明确拒绝边界')}
                    </p>
                  </div>

                  <div className="rounded-card border border-border bg-elevated p-3">
                    <p className="text-xs font-semibold text-content-muted">攻击面清单</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {[
                        {
                          key: 'tool_scope',
                          label: '工具写权限',
                          on: baseline.tool_scope === 'write' || baseline.tool_scope === 'exec'
                        },
                        { key: 'network_enabled', label: '可出网', on: Boolean(baseline.network_enabled) },
                        { key: 'has_rag', label: 'RAG', on: Boolean(baseline.has_rag) },
                        {
                          key: 'has_long_term_memory',
                          label: '长期记忆',
                          on: Boolean(baseline.has_long_term_memory)
                        },
                        { key: 'has_guardrail', label: '防护栏', on: Boolean(baseline.has_guardrail) }
                      ].map((item) => (
                        <Badge key={item.key} tone={item.on ? 'danger' : 'neutral'}>
                          {item.label}
                          {item.on ? ' · 暴露' : ''}
                        </Badge>
                      ))}
                      {Object.keys(baseline).length === 0 ? (
                        <span className="text-xs text-content-faint">未提交基线声明，计划按最保守估计编排。</span>
                      ) : null}
                    </div>

                    <p className="mt-3 text-xs font-semibold text-content-muted">
                      工具 {agentTools.length} 个 · 提示词片段 {list(agent.prompt_fragments).length} 段
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {agentTools.map((t, i) => (
                        <span
                          key={i}
                          className="rounded-pill border border-border px-2 py-0.5 font-mono text-[11px] text-content-muted"
                        >
                          {text(t.name, 'tool')}
                        </span>
                      ))}
                      {agentTools.length === 0 ? (
                        <span className="text-xs text-content-faint">
                          侦察未回传工具清单，工具面按基线声明估计。
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
                  <div className="rounded-control border border-border bg-elevated p-3">
                    <p className="text-content-faint">覆盖类别</p>
                    <p className="font-mono text-lg">
                      {categories.length}/{text(chapters.total_categories, '0')}
                    </p>
                  </div>
                  <div className="rounded-control border border-border bg-sunken p-3">
                    <p className="text-content-faint">已击穿类别</p>
                    <p className="font-mono text-lg">{categories.filter((c) => Number(c.success) > 0).length}</p>
                  </div>
                  <div className="rounded-control border border-border bg-sunken p-3">
                    <p className="text-content-faint">攻击链完整度</p>
                    <p className="font-mono text-lg">{killChain.length}/5</p>
                  </div>
                </div>
              </section>
            ) : null}
            {/* 第三章 攻击路径图 */}
            {chapter === CHAPTERS[2] ? (
              <section>
                <p className="mb-2 font-mono text-[10px] text-content-faint">{CHAPTERS[2]}</p>

                <div className="flex flex-wrap items-center gap-1">
                  {STAGE_ORDER.map((stage) => {
                    const hits = pathNodes.filter((n) => text(n.stage) === stage && text(n.severity) !== 'info').length;
                    return (
                      <Badge key={stage} tone={hits > 0 ? 'blue' : 'neutral'}>
                        {STAGE_LABELS[stage] ?? stage}
                        {hits > 0 ? ` · ${hits} 次命中` : ' · 断裂'}
                      </Badge>
                    );
                  })}
                </div>

                {pathNodes.length > 0 ? (
                  <AttackPathGraph
                    className="mt-3"
                    height={360}
                    stages={STAGE_ORDER}
                    nodes={pathNodes.map((n) => ({
                      id: text(n.id),
                      label: text(n.label),
                      category: text(n.stage),
                      verdict: (text(n.severity) === 'info' ? 'fail' : 'success') as 'success' | 'fail'
                    }))}
                    edges={pathEdges
                      .map((e) => {
                        const edge = e as Row;
                        return {
                          source: text(edge.source ?? edge.from),
                          target: text(edge.target ?? edge.to)
                        };
                      })
                      .filter((e) => e.source && e.target)}
                  />
                ) : (
                  <p className="mt-3 text-xs text-content-faint">本次演练没有形成可连通的攻击链路。</p>
                )}

                <p className="mt-3 text-xs leading-relaxed text-content-muted">
                  {killChain.length > 0
                    ? `命中链路覆盖 ${killChain.length}/5 个阶段：${killChain
                        .map((s) => STAGE_LABELS[s] ?? s)
                        .join(' → ')}。`
                    : '本次演练未形成成功链路。'}
                  {missingStages.length > 0
                    ? `断裂阶段：${missingStages.map((s) => STAGE_LABELS[s] ?? s).join('、')}（该阶段无命中证据，无法串联成完整 kill chain）。`
                    : '五个阶段均有命中证据，链路完整。'}
                </p>
                <p className="mt-1 text-[11px] text-content-faint">
                  节点 {pathNodes.length} · 边 {pathEdges.length}（图中虚线段为证据缺失的断裂阶段）
                </p>
              </section>
            ) : null}

            {/* 第四章 分类别结果 */}
            {chapter === CHAPTERS[3] ? (
              <section>
                <p className="mb-2 font-mono text-[10px] text-content-faint">{CHAPTERS[3]}</p>
                <div className="grid gap-3 md:grid-cols-2">
                  {categories.map((c) => (
                    <div key={text(c.code)} className="rounded-card border border-border bg-elevated p-3">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs text-blue-team">{text(c.code)}</span>
                        <span className="font-mono text-xs">
                          {text(c.success)}/{text(c.total)}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-content-muted">{text(c.name)}</p>
                      <div className="mt-2 h-1.5 overflow-hidden rounded-pill bg-white/10">
                        <div className="h-full bg-red-team" style={{ width: `${Number(c.asr ?? 0) * 100}%` }} />
                      </div>
                      <p className="mt-1 text-right font-mono text-[11px] text-content-faint">
                        ASR {num(Number(c.asr ?? 0) * 100, 1)}%
                      </p>
                    </div>
                  ))}
                  {categories.length === 0 ? <p className="text-xs text-content-faint">无分类别结果</p> : null}
                </div>
                {Object.keys(benchmark).length > 0 ? (
                  <div className="mt-3 rounded-card border border-border bg-sunken p-3">
                    <p className="mb-2 text-xs font-semibold text-content-muted">同分段基准</p>
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs">
                      <span className="text-content-faint">
                        分段 <span className="font-mono text-content">{text(benchmark.segment, '-')}</span>
                      </span>
                      <span className="text-content-faint">
                        样本 <span className="font-mono text-content">{text(benchmark.sample_size, '0')}</span>
                      </span>
                      <span className="text-content-faint">
                        均值 <span className="font-mono text-content">{num(benchmark.mean, 1)}</span>
                      </span>
                      {Object.entries((benchmark.percentiles ?? {}) as Record<string, number>).map(([k, v]) => (
                        <span key={k} className="text-content-faint">
                          {k} <span className="font-mono text-content">{num(v, 1)}</span>
                        </span>
                      ))}
                    </div>
                    <p className="mt-2 text-[11px] text-content-faint">
                      分段由场景代号与 Agent 形态推导；样本量不足时分位数仅供参考。
                    </p>
                  </div>
                ) : null}
              </section>
            ) : null}
            {/* 第五章 高危详情 */}
            {chapter === CHAPTERS[4] ? (
              <section>
                <p className="mb-2 font-mono text-[10px] text-content-faint">{CHAPTERS[4]}</p>
                <div className="space-y-2">
                  {highRisk.map((r, i) => (
                    <div key={i} className="rounded-card border border-border bg-elevated p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={SEVERITY_TONES[text(r.severity, 'medium')] ?? 'neutral'}>
                          {SEVERITY_LABELS[text(r.severity, 'medium')] ?? text(r.severity, 'medium')}
                        </Badge>
                        <span className="font-mono text-xs text-blue-team">{text(r.category_code)}</span>
                        <span className="text-xs text-content">
                          {text(r.title) || text(r.case_id)}（{text(r.case_id)}）
                        </span>
                        <Badge tone={text(r.verdict) === 'success' ? 'danger' : 'warning'}>
                          {text(r.verdict) === 'success'
                            ? '命中'
                            : text(r.verdict) === 'partial'
                              ? '部分命中'
                              : '未命中'}
                        </Badge>
                      </div>
                      <p className="mt-1 font-mono text-[11px] text-content-faint">
                        策略 {text(r.strategy, '未标注')} · {text(r.turns, '0')} 轮 · {text(r.tokens, '0')} tokens ·
                        置信度 {num(r.confidence)}
                      </p>
                      {list(r.mutation_ops).length > 0 ? (
                        <p className="mt-1 font-mono text-[11px] text-content-faint">
                          变异算子：
                          {list(r.mutation_ops)
                            .map((op) => text(op))
                            .join(' → ')}
                        </p>
                      ) : null}
                      <p className="mt-1 text-xs text-content-muted">判定依据：{evidenceOf(r)}</p>
                      <p className="mt-1 font-mono text-[10px] text-content-faint">trace：{text(r.trace_ref, '-')}</p>
                    </div>
                  ))}
                  {highRisk.length === 0 ? <p className="text-xs text-content-faint">未发现命中用例</p> : null}
                </div>

                <p className="mb-2 mt-4 font-mono text-[10px] text-content-faint">trace 回放</p>
                <div className="flex flex-wrap items-center gap-2">
                  <Select value={traceId} onValueChange={setTraceId}>
                    <SelectTrigger className="w-72">
                      <SelectValue placeholder="选择一条命中用例回放 trace" />
                    </SelectTrigger>
                    <SelectContent>
                      {highRisk
                        .filter((r) => text(r.record_id))
                        .map((r, i) => (
                          <SelectItem key={i} value={text(r.record_id)}>
                            {text(r.case_id)} · {text(r.title) || text(r.case_id)}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                  <Select value={levelFilter} onValueChange={(v) => setLevelFilter(v as 'none' | 'partial' | 'full')}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">不脱敏</SelectItem>
                      <SelectItem value="partial">部分脱敏</SelectItem>
                      <SelectItem value="full">完全脱敏</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {trace.isFetching ? <p className="mt-2 text-xs text-content-muted">trace 拉取中…</p> : null}
                {trace.data ? <TracePanel trace={trace.data} level={levelFilter} /> : null}
              </section>
            ) : null}

            {/* 第六章 根因分析与修复建议 */}
            {chapter === CHAPTERS[5] ? (
              <section>
                <p className="mb-2 font-mono text-[10px] text-content-faint">{CHAPTERS[5]}</p>
                <div className="space-y-2">
                  {findings.map((f, i) => {
                    const affected = (f.affected_config ?? {}) as Row;
                    return (
                      <div key={i} className="rounded-card border border-border bg-elevated p-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone={f.primary ? 'danger' : (SEVERITY_TONES[text(f.severity, 'low')] ?? 'neutral')}>
                            {SEVERITY_LABELS[text(f.severity, 'low')] ?? text(f.severity, 'low')}
                          </Badge>
                          <span className="text-xs font-semibold text-content">
                            {text(f.root_cause_name) || text(f.root_cause_code)}
                          </span>
                          <span className="font-mono text-[11px] text-blue-team">{text(f.root_cause_code)}</span>
                          {f.primary ? <Badge tone="danger">主因</Badge> : null}
                          <span className="ml-auto font-mono text-[11px] text-content-faint">置信度 {num(f.confidence)}</span>
                        </div>
                        <p className="mt-2 text-xs leading-relaxed text-content-muted">{text(f.impact)}</p>
                        <p className="mt-1 text-[11px] text-content-faint">
                          受影响配置（{text(affected.kind, 'unknown')}）：{text(affected.value, '-')}
                        </p>
                        {list(f.matched_signals).length > 0 ? (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {list(f.matched_signals).map((s, j) => (
                              <span
                                key={j}
                                className="rounded-pill border border-border px-2 py-0.5 font-mono text-[11px] text-content-muted"
                              >
                                {text(s)}
                              </span>
                            ))}
                          </div>
                        ) : null}
                        <p className="mt-2 font-mono text-[10px] text-content-faint">
                          关联用例 {list(f.case_ids).map((c) => text(c)).join('、') || '-'} · 记录 {list(f.record_ids).length} 条
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                          {list(f.recommendations).map((rec, j) => {
                            const row = rec as Row;
                            return (
                              <span
                                key={j}
                                className="rounded-pill border border-border px-2 py-0.5 font-mono text-content-muted"
                              >
                                {text(row.priority)} · {text(row.playbook_ref)} · 成本 {text(row.effort)}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                  {findings.length === 0 ? <p className="text-xs text-content-faint">未定位到根因</p> : null}
                </div>
              </section>
            ) : null}

            {/* 第七章 整改清单 */}
            {chapter === CHAPTERS[6] ? (
              <section>
                <p className="mb-2 font-mono text-[10px] text-content-faint">{CHAPTERS[6]}</p>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div className="rounded-control border border-border bg-elevated p-3">
                    <p className="text-content-faint">建议总数</p>
                    <p className="font-mono text-lg">{text(remediation.total, String(recommendationRows.length))}</p>
                  </div>
                  <div className="rounded-control border border-border bg-sunken p-3">
                    <p className="text-content-faint">优先级分布</p>
                    <p className="font-mono text-lg">{Object.keys(matrix).join(' / ') || '-'}</p>
                  </div>
                  <div className="rounded-control border border-border bg-sunken p-3">
                    <p className="text-content-faint">关联根因</p>
                    <p className="font-mono text-lg">
                      {new Set(recommendationRows.map((r) => text(r.finding_root_cause))).size}
                    </p>
                  </div>
                </div>

                <div className="mt-3 space-y-2">
                  {recommendationRows.map((r, i) => (
                    <div key={i} className="rounded-card border border-border bg-elevated p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={PRIORITY_TONES[text(r.priority, 'P2')] ?? 'neutral'}>{text(r.priority, 'P2')}</Badge>
                        <span className="font-mono text-[11px] text-blue-team">{text(r.playbook_ref)}</span>
                        <span className="text-content-faint">成本 {text(r.effort, '-')}</span>
                        <Badge tone={r.applied ? 'success' : 'neutral'}>{r.applied ? '已应用' : '待处理'}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-content-muted">
                        根因 {text(r.finding_root_cause)}（
                        {SEVERITY_LABELS[text(r.severity, 'low')] ?? text(r.severity, 'low')}）
                      </p>
                      <p className="mt-1 text-xs text-content">预期效果：{text(r.expected_effect, '—')}</p>
                      {text(r.side_effects) ? (
                        <p className="mt-1 text-[11px] text-warning">副作用：{text(r.side_effects)}</p>
                      ) : null}
                      {list(r.artifacts).length > 0 ? (
                        <p className="mt-1 text-[11px] text-content-faint">附带产物 {list(r.artifacts).length} 项</p>
                      ) : null}
                    </div>
                  ))}
                  {recommendationRows.length === 0 ? (
                    <p className="text-xs text-content-faint">暂无整改建议</p>
                  ) : null}
                </div>

                {Object.keys(matrix).length > 0 ? (
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-content-faint">
                          <th className="pb-1 pr-3 font-normal">优先级</th>
                          <th className="pb-1 pr-3 font-normal">成本 S（小）</th>
                          <th className="pb-1 pr-3 font-normal">成本 M（中）</th>
                          <th className="pb-1 font-normal">成本 L（大）</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(matrix).map(([priority, efforts]) => (
                          <tr key={priority} className="border-t border-border">
                            <td className="py-1.5 pr-3 font-mono text-blue-team">{priority}</td>
                            <td className="py-1.5 pr-3 font-mono text-content-muted">{efforts.S ?? 0}</td>
                            <td className="py-1.5 pr-3 font-mono text-content-muted">{efforts.M ?? 0}</td>
                            <td className="py-1.5 font-mono text-content-muted">{efforts.L ?? 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <p className="mt-2 text-[11px] text-content-faint">
                      行=修复优先级（P0 最高），列=修复成本；按「风险下降 ÷ 成本」排序，先做左上角。
                    </p>
                  </div>
                ) : null}
              </section>
            ) : null}
            {/* 第八章 复测对比 */}
            {chapter === CHAPTERS[7] ? (
              <section>
                <p className="mb-2 font-mono text-[10px] text-content-faint">{CHAPTERS[7]}</p>
                <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                  <div className="rounded-control border border-border bg-elevated p-3">
                    <p className="text-content-faint">本轮 SecScore</p>
                    <p className="font-mono text-lg">{secScore}</p>
                  </div>
                  <div className="rounded-control border border-border bg-sunken p-3">
                    <p className="text-content-faint">本轮 ASR</p>
                    <p className="font-mono text-lg">{num(Number(chapters.asr ?? 0) * 100, 1)}%</p>
                  </div>
                  <div className="rounded-control border border-border bg-sunken p-3">
                    <p className="text-content-faint">登记版本</p>
                    <p className="font-mono text-lg">{versions.length}</p>
                  </div>
                  <div className="rounded-control border border-border bg-sunken p-3">
                    <p className="text-content-faint">是否回退</p>
                    <p className={`font-mono text-lg ${retest.regression_failed ? 'text-danger' : 'text-success'}`}>
                      {retest.regression_failed ? '是' : '否'}
                    </p>
                  </div>
                </div>

                {versions.length > 0 ? (
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-content-faint">
                          <th className="pb-1 pr-3 font-normal">版本快照</th>
                          <th className="pb-1 pr-3 font-normal">prompt hash</th>
                          <th className="pb-1 pr-3 font-normal">来源</th>
                          <th className="pb-1 pr-3 font-normal">工具数</th>
                          <th className="pb-1 font-normal">登记时间</th>
                        </tr>
                      </thead>
                      <tbody>
                        {versions.map((v, i) => (
                          <tr key={i} className="border-t border-border">
                            <td className="py-1.5 pr-3 font-mono text-content">{text(v.version).slice(0, 8)}</td>
                            <td className="py-1.5 pr-3 font-mono text-content-muted">{text(v.prompt_hash, '—')}</td>
                            <td className="py-1.5 pr-3 text-content-muted">{text(v.source, '—')}</td>
                            <td className="py-1.5 pr-3 font-mono text-content-muted">{text(v.tools, '0')}</td>
                            <td className="py-1.5 font-mono text-content-faint">{text(v.created_at, '—')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}

                <div className="mt-3 rounded-card border border-border bg-sunken p-3 text-[11px] leading-relaxed text-content-faint">
                  {versions.length === 0
                    ? '该 Agent 尚未登记版本快照，暂无历史基线可对比。整改后可到 Agent 详情页提交一次版本快照，再重新生成报告即可得到前后对比。'
                    : '版本快照来自 Agent 资产登记记录；对同一 Agent 重新生成报告即可对比整改前后的 SecScore 与 ASR。'}
                  {' '}回退判定规则：相邻版本 SecScore 跌幅超过 5 分即判回退。
                </div>
              </section>
            ) : null}
            {/* 第九章 合规映射 */}
            {chapter === CHAPTERS[8] ? (
              <section>
                <p className="mb-2 font-mono text-[10px] text-content-faint">{CHAPTERS[8]}</p>
                <div className="space-y-2">
                  {compliance.map((c, i) => {
                    const clauses = list(c.clauses) as Row[];
                    return (
                      <div key={i} className="rounded-card border border-border bg-elevated p-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-content">{text(c.framework)}</span>
                          <span className="font-mono text-xs text-content-faint">{clauses.length} 项</span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {clauses.map((clause, k) => (
                            <span
                              key={k}
                              className="rounded-pill border border-border px-2 py-0.5 font-mono text-[11px] text-content-muted"
                              title={`命中类别：${list(clause.categories)
                                .map((cc) => text(cc))
                                .join('、')}`}
                            >
                              {text(clause.clause)}
                            </span>
                          ))}
                          {clauses.length === 0 ? (
                            <span className="text-xs text-content-faint">本次命中未触及该框架条款</span>
                          ) : null}
                        </div>
                      </div>
                    );
                  })}
                  {compliance.length === 0 ? <p className="text-xs text-content-faint">暂无合规映射</p> : null}
                </div>
              </section>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <Dialog open={exportOpen} onOpenChange={setExportOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>导出报告</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <label className="block text-xs text-content-muted">
              格式
              <Select value={format} onValueChange={setFormat}>
                <SelectTrigger className="mt-1 w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="html">HTML（可交互）</SelectItem>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="json">JSON（机读）</SelectItem>
                  <SelectItem value="markdown">Markdown</SelectItem>
                </SelectContent>
              </Select>
            </label>
            <label className="block text-xs text-content-muted">
              脱敏等级
              <Select value={level} onValueChange={setLevel}>
                <SelectTrigger className="mt-1 w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">不脱敏</SelectItem>
                  <SelectItem value="standard">标准</SelectItem>
                  <SelectItem value="strict">严格</SelectItem>
                </SelectContent>
              </Select>
            </label>
          </div>
          <Button
            className="mt-4 w-full"
            loading={exportMut.isPending}
            onClick={async () => {
              try {
                await exportMut.mutateAsync({ format, desensitize_level: level });
                toast.success('导出任务已提交', format);
                setExportOpen(false);
              } catch (e) {
                toast.error('导出失败', errorMessage(e));
              }
            }}
          >
            开始导出
          </Button>
        </DialogContent>
      </Dialog>

      <Dialog open={shareOpen} onOpenChange={setShareOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>生成分享链接</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <label className="block text-xs text-content-muted">
              有效期（小时）
              <Input type="number" value={shareTtl} onChange={(e) => setShareTtl(Number(e.target.value))} className="mt-1" />
            </label>
            {shareUrl ? (
              <div className="rounded-control border border-success/40 bg-success/5 p-3">
                <p className="text-[11px] text-content-faint">分享链接（仅本机演示可见）</p>
                <p className="mt-1 break-all font-mono text-xs text-success">{shareUrl}</p>
              </div>
            ) : null}
          </div>
          <Button
            className="mt-4 w-full"
            loading={shareMut.isPending}
            onClick={async () => {
              try {
                const res = await shareMut.mutateAsync({ desensitize_level: 'standard', expires_in_hours: shareTtl });
                const url = `${window.location.origin}/api/v1/reports/share/${res.token}`;
                setShareUrl(url);
                toast.success('分享链接已生成');
              } catch (e) {
                toast.error('生成失败', errorMessage(e));
              }
            }}
          >
            生成链接
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/** 单条攻击记录的 trace 回放（PRD 3.3.6.4）：请求链 + 规则命中 + 裁判结论。 */
function TracePanel({ trace, level }: { trace: Record<string, unknown>; level: 'none' | 'partial' | 'full' }) {
  const events = list(trace.events) as TraceEvent[];
  const ruleHits = list(trace.rule_hits) as Row[];
  const verdicts = list(trace.verdicts) as Row[];
  const show = (value: unknown) => desensitize(JSON.stringify(value, null, 1), level);

  return (
    <div className="mt-3 space-y-3 rounded-card border border-border bg-sunken p-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] text-content-faint">
        <span>用例 {text(trace.case_id)}</span>
        <span>类别 {text(trace.category_code)}</span>
        <span>策略 {text(trace.strategy, '未标注')}</span>
        <span>tokens {text(trace.tokens, '0')}</span>
        <span>trace_key {text(trace.trace_key).slice(0, 20)}</span>
      </div>

      {list(trace.mutation_ops).length > 0 ? (
        <p className="font-mono text-[11px] text-content-faint">
          变异算子：{list(trace.mutation_ops).map((op) => text(op)).join(' → ')}
        </p>
      ) : null}

      <div>
        <p className="mb-1 text-xs font-semibold text-content-muted">黄金规则命中</p>
        {ruleHits.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {ruleHits.map((hit, k) => (
              <Badge key={k} tone="danger">
                {text(hit.rule_id)} · {text(hit.detail, '命中')}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-[11px] text-content-faint">无黄金规则命中（本地裁判 / LLM 裁判判定）</p>
        )}
      </div>

      <div>
        <p className="mb-1 text-xs font-semibold text-content-muted">裁判结论</p>
        <div className="space-y-1">
          {verdicts.map((v, k) => (
            <div key={k} className="rounded-control border border-border bg-elevated px-3 py-2 text-[11px]">
              <div className="flex items-center gap-2">
                <Badge tone={text(v.result) === 'success' ? 'danger' : 'neutral'}>
                  {text(v.level)} · {text(v.result) === 'success' ? '命中' : '未命中'}
                </Badge>
                <span className="font-mono text-content-faint">置信度 {num(v.confidence)}</span>
                <span className="font-mono text-content-faint">{text(v.judge_model)}</span>
              </div>
              <p className="mt-1 text-content-muted">{text(v.reason)}</p>
            </div>
          ))}
          {verdicts.length === 0 ? (
            <p className="text-[11px] text-content-faint">无裁判结论记录</p>
          ) : null}
        </div>
      </div>

      <div>
        <p className="mb-1 text-xs font-semibold text-content-muted">事件流（{events.length} 条）</p>
        {events.length > 0 ? (
          <div className="max-h-56 space-y-1 overflow-auto">
            {events.map((ev) => (
              <div
                key={ev.id}
                className="flex flex-wrap items-center gap-2 rounded-control border border-border bg-elevated px-3 py-1.5 font-mono text-[11px]"
              >
                <span className="text-blue-team">{EVENT_LABELS[ev.event_type] ?? ev.event_type}</span>
                <span className="text-content">{ev.name || ev.actor}</span>
                <span className="text-content-faint">{ev.tokens} tokens</span>
                <span className="text-content-faint">{ev.latency_ms} ms</span>
                {ev.canary_hit ? <Badge tone="danger">蜜标命中</Badge> : null}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[11px] text-content-faint">明细仓库未回传事件流（离线演示环境下判定结论已由本地裁判给出）。</p>
        )}
      </div>

      {list(trace.evidence).length > 0 ? (
        <div>
          <p className="mb-1 text-xs font-semibold text-content-muted">证据</p>
          <pre className="max-h-40 overflow-auto rounded-control border border-border bg-elevated p-2 font-mono text-[11px]">
            {show(list(trace.evidence))}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
