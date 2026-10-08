import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from './client';
import type {
  Agent,
  AgentProfile,
  AgentUpdate,
  AgentVersion,
  AttackCase,
  AttackCategory,
  AttackRecord,
  BaselineDeclaration,
  BattleCard,
  Budget,
  Campaign,
  CampaignCreate,
  CampaignPlan,
  CampaignUpdate,
  Finding,
  GateRule,
  HealthCheck,
  HintResult,
  InstanceCreate,
  Intensity,
  Level,
  LevelProgress,
  Member,
  Page,
  Report,
  Scenario,
  ScenarioInstance,
  ScenarioRecommendation,
  ScanJob,
  Score,
  Session,
  SessionCreate,
  SessionMessage,
  TrendPoint,
  AchievementOut,
  UserProfile,
  VerificationRecord,
  VerificationRequest
} from '@xian/types';
import { ROUTES } from '@xian/types';

/* ---------- Agent 资产 ---------- */

export function useAgents(params: { page?: number; size?: number; keyword?: string } = {}) {
  return useQuery({
    queryKey: ['agents', params],
    queryFn: () => api.get<Page<Agent>>(ROUTES.agents, params)
  });
}

export function useAgent(id: string | undefined) {
  return useQuery({
    queryKey: ['agent', id],
    queryFn: () => api.get<Agent>(ROUTES.agent(id!)),
    enabled: Boolean(id)
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      access_type: Agent['access_type'];
      endpoint: string;
      description?: string;
      baseline_declaration?: Partial<BaselineDeclaration>;
    }) => api.post<Agent>(ROUTES.agents, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] })
  });
}

export function useUpdateAgent(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentUpdate) => api.patch<Agent>(ROUTES.agent(id), body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent', id] });
      qc.invalidateQueries({ queryKey: ['agents'] });
    }
  });
}

export function useVerifyAgent(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: VerificationRequest) => api.post<VerificationRecord>(ROUTES.agentVerify(id), body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent', id] });
      qc.invalidateQueries({ queryKey: ['agents'] });
    }
  });
}

export function useAgentHealthcheck(id: string) {
  return useMutation({
    mutationFn: () => api.post<HealthCheck>(ROUTES.agentHealthcheck(id), {})
  });
}

export function useAgentVersions(id: string | undefined) {
  return useQuery({
    queryKey: ['agent-versions', id],
    queryFn: () => api.get<AgentVersion[]>(ROUTES.agentVersions(id!)),
    enabled: Boolean(id)
  });
}

export function useCreateAgentVersion(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      prompt_hash?: string;
      tools_snapshot?: Record<string, unknown>[];
      model_params?: Record<string, unknown>;
      source?: string;
    }) => api.post<AgentVersion>(ROUTES.agentVersions(id), body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agent-versions', id] })
  });
}

export function useAgentRecon(id: string) {
  return useMutation({ mutationFn: () => api.post<AgentProfile>(ROUTES.agentRecon(id), {}) });
}

export function useAgentRecommendations(id: string | undefined) {
  return useQuery({
    queryKey: ['agent-recommendations', id],
    queryFn: () => api.get<ScenarioRecommendation[]>(ROUTES.agentRecommendations(id!)),
    enabled: Boolean(id)
  });
}
/* ---------- 场景 ---------- */

export function useScenarios() {
  return useQuery({ queryKey: ['scenarios'], queryFn: () => api.get<Scenario[]>(ROUTES.scenarios) });
}

export function useScenario(code: string | undefined) {
  return useQuery({
    queryKey: ['scenario', code],
    queryFn: () => api.get<Scenario>(ROUTES.scenario(code!)),
    enabled: Boolean(code)
  });
}

export function useCreateScenarioInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: InstanceCreate) => api.post<ScenarioInstance>(ROUTES.scenarioInstances, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scenario-instances'] })
  });
}

export function useScenarioInstances() {
  return useQuery({
    queryKey: ['scenario-instances'],
    queryFn: () => api.get<ScenarioInstance[]>(ROUTES.scenarioInstances)
  });
}

export function useScanInstance(id: string) {
  return useMutation({ mutationFn: () => api.post<{ instance_id: string; status: string; exit_code: number }>(ROUTES.scenarioInstanceScan(id), {}) });
}

export function useDeleteScenarioInstance(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete<{ id: string; status: string }>(ROUTES.scenarioInstance(id)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scenario-instances'] })
  });
}

/* ---------- 战役（模式一） ---------- */

export function useCampaigns() {
  return useQuery({ queryKey: ['campaigns'], queryFn: () => api.get<Campaign[]>(ROUTES.campaigns) });
}

export function useCampaign(id: string | undefined) {
  return useQuery({
    queryKey: ['campaign', id],
    queryFn: () => api.get<Campaign>(ROUTES.campaign(id!)),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === 'attacking' || s === 'preparing' || s === 'reporting' ? 2000 : false;
    }
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CampaignCreate) => api.post<Campaign>(ROUTES.campaigns, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] })
  });
}

export function useUpdateCampaign(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CampaignUpdate) => api.patch<Campaign>(ROUTES.campaign(id), body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaign', id] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    }
  });
}

/** 创建前预览 DAG：走 /campaigns/preview-plan，不依赖已存在的战役。 */
export function usePreviewCampaignPlan() {
  return useMutation({
    mutationFn: (body: { agent_id?: string; scope?: string[]; intensity?: Intensity; budget?: Budget }) =>
      api.post<CampaignPlan>(ROUTES.campaignPlanPreview, body)
  });
}

/** 为已创建的战役生成并落库 DAG 计划（PRD 3.3.5.8.1）。 */
export function useCampaignPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<CampaignPlan>(ROUTES.campaignPlan(id), {}),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['campaign', id] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    }
  });
}

export function useRunCampaign(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ status: string; executed?: number; success?: number }>(ROUTES.campaignRun(id), {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaign', id] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      /* 跑完必须刷新攻击记录，否则页面一直显示「暂无攻击记录」 */
      qc.invalidateQueries({ queryKey: ['campaign-records', id] });
    }
  });
}

export function useCampaignRecords(id: string | undefined, page = 1, size = 20) {
  return useQuery({
    queryKey: ['campaign-records', id, page, size],
    queryFn: () => api.get<Page<AttackRecord>>(ROUTES.campaignRecords(id!), { page, size }),
    enabled: Boolean(id)
  });
}

export function useRecordTrace(recordId: string | undefined) {
  return useQuery({
    queryKey: ['record-trace', recordId],
    queryFn: () => api.get<{ events: import('@xian/types').TraceEvent[] }>(ROUTES.recordTrace(recordId!)),
    enabled: Boolean(recordId)
  });
}

/* ---------- 模式二会话 ---------- */

export function useSessions() {
  return useQuery({ queryKey: ['sessions'], queryFn: () => api.get<Session[]>(ROUTES.sessions) });
}

export function useSession(id: string | undefined) {
  return useQuery({
    queryKey: ['session', id],
    queryFn: () => api.get<Session>(ROUTES.session(id!)),
    enabled: Boolean(id)
  });
}

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SessionCreate) => api.post<Session>(ROUTES.sessions, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] })
  });
}

export function useSessionMessages(id: string | undefined) {
  return useQuery({
    queryKey: ['session-messages', id],
    queryFn: () => api.get<SessionMessage[]>(ROUTES.sessionMessages(id!)),
    enabled: Boolean(id)
  });
}

export function useSendMessage() {
  const qc = useQueryClient();
  return useMutation({
    /* 会话 id 由调用方在 mutate 时传入：新建会话后 state 还没重渲染，
       闭包里捕获的旧 id 会是空串，拼出 /sessions//messages，
       被 buildRequestPath 的斜杠合并规则压成 /sessions/messages 而命中 405。 */
    mutationFn: (vars: { sessionId: string; body: { content: string; case_id?: string | null } }) =>
      api.post<SessionMessage>(ROUTES.sessionMessages(vars.sessionId), vars.body),
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ['session-messages', vars.sessionId] })
  });
}

export function useSessionCards(id: string | undefined) {
  return useQuery({
    queryKey: ['session-cards', id],
    queryFn: () => api.get<BattleCard[]>(ROUTES.sessionCards(id!)),
    enabled: Boolean(id)
  });
}

/* ---------- 攻击矩阵 ---------- */

export function useMatrixCategories() {
  return useQuery({ queryKey: ['matrix-categories'], queryFn: () => api.get<AttackCategory[]>(ROUTES.matrixCategories) });
}

export function useMatrixCases(category?: string) {
  return useQuery({
    queryKey: ['matrix-cases', category],
    queryFn: () => api.get<AttackCase[]>(ROUTES.matrixCases, category ? { category } : undefined)
  });
}

export function useMatrixOperators() {
  return useQuery({
    queryKey: ['matrix-operators'],
    queryFn: () => api.get<Record<string, unknown>[]>(ROUTES.matrixOperators)
  });
}

export function useMatrixStrategies() {
  return useQuery({
    queryKey: ['matrix-strategies'],
    queryFn: () => api.get<Record<string, unknown>[]>(ROUTES.matrixStrategies)
  });
}

export function useMatrixCoverage() {
  return useQuery({ queryKey: ['matrix-coverage'], queryFn: () => api.get<Record<string, unknown>>(ROUTES.matrixCoverage) });
}

export function useMatrixFrameworks() {
  return useQuery({ queryKey: ['matrix-frameworks'], queryFn: () => api.get<Record<string, unknown>[]>(ROUTES.matrixFrameworks) });
}

/** 用例评审流水线（PRD 3.5.5.8.1）：submitted → auto_test → review → published。
 *  注意：后端只按「当前状态 + 是否通过」推算下一状态，不落库，
 *  所以推进结果只在本页会话内有效，UI 上需如实标注。 */
export function useReviewCase() {
  return useMutation({
    mutationFn: (vars: { caseId: string; status: string; passed: boolean }) =>
      api.post<{ case_id: string; status: string }>(ROUTES.matrixCaseReview(vars.caseId), {
        status: vars.status,
        passed: vars.passed
      })
  });
}

/* ---------- 关卡 ---------- */

export function useLevels() {
  return useQuery({ queryKey: ['levels'], queryFn: () => api.get<Level[]>(ROUTES.levels) });
}

export function useLevelProgress() {
  return useQuery({ queryKey: ['level-progress'], queryFn: () => api.get<LevelProgress[]>(ROUTES.levelProgress) });
}

export function useStartLevel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => api.post<LevelProgress>(ROUTES.levelStart(code), {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['level-progress'] })
  });
}

export function useHint() {
  return useMutation({
    mutationFn: (body: { code: string; hint_level: string }) =>
      api.post<HintResult>(ROUTES.levelHint(body.code), { hint_level: body.hint_level })
  });
}

export function useSubmitLevel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown> & { code: string }) =>
      api.post<LevelProgress>(ROUTES.levelSubmit(body.code), body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['level-progress'] });
      qc.invalidateQueries({ queryKey: ['profile'] });
    }
  });
}

export function useLevelHardening(code: string) {
  return useQuery({
    queryKey: ['level-hardening', code],
    queryFn: () => api.get<Record<string, unknown>>(ROUTES.levelHardening(code)),
    enabled: Boolean(code)
  });
}

export function useProfile() {
  return useQuery({ queryKey: ['profile'], queryFn: () => api.get<UserProfile>(ROUTES.profile) });
}

export function useAchievements() {
  return useQuery({ queryKey: ['achievements'], queryFn: () => api.get<AchievementOut[]>(ROUTES.achievements) });
}
/* ---------- 报告 ---------- */

export function useReports() {
  return useQuery({ queryKey: ['reports'], queryFn: () => api.get<Report[]>(ROUTES.reports) });
}

export function useReport(id: string | undefined) {
  return useQuery({
    queryKey: ['report', id],
    queryFn: () => api.get<Record<string, unknown>>(ROUTES.report(id!)),
    enabled: Boolean(id)
  });
}

export function useCreateCampaignReport(campaignId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Report>(ROUTES.reportByCampaign(campaignId), {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports'] })
  });
}

export function useExportReport(id: string) {
  return useMutation({
    mutationFn: (body: { format: string; desensitize_level?: string }) =>
      api.post<{ id: string; format: string; file_ref: string }>(ROUTES.reportExport(id), body)
  });
}

export function useShareReport(id: string) {
  return useMutation({
    mutationFn: (body?: { desensitize_level?: string; expires_in_hours?: number }) =>
      api.post<{ token: string; url: string }>(ROUTES.reportShare(id), body ?? {})
  });
}

export function useScore(campaignId: string) {
  return useQuery({
    queryKey: ['score', campaignId],
    queryFn: () => api.get<Score>(ROUTES.campaign(campaignId)),
    enabled: Boolean(campaignId)
  });
}

/* ---------- 管理 ---------- */

export function useMembers() {
  return useQuery({ queryKey: ['members'], queryFn: () => api.get<Member[]>(ROUTES.adminMembers) });
}

export function useGateRules() {
  return useQuery({ queryKey: ['gate-rules'], queryFn: () => api.get<GateRule[]>(ROUTES.adminGateRules) });
}

export function useScanJobs() {
  return useQuery({ queryKey: ['scan-jobs'], queryFn: () => api.get<ScanJob[]>(ROUTES.adminScanJobs) });
}

/** 分数趋势：由报告列表按 created_at 升序聚合（PRD 3.8.5 分数趋势）。 */
export function useTrend(agentId?: string) {
  return useQuery({
    queryKey: ['trend', agentId],
    queryFn: async (): Promise<TrendPoint[]> => {
      const reports = await api.get<Report[]>(ROUTES.reports);
      return reports
        .filter((r) => (agentId ? r.subject_id === agentId : true))
        .sort((a, b) => a.created_at.localeCompare(b.created_at))
        .map((r) => ({
          agent_id: r.subject_id,
          version_id: r.id,
          sec_score: r.sec_score,
          ts: r.created_at
        }));
    }
  });
}

export interface ReportChapters {
  title?: string;
  sec_score?: number;
  grade?: string;
  asr?: number;
  baseline_pass_rate?: number;
  executive_summary?: string;
  top_risks?: { severity: string; title: string; root_cause: string; case_id?: string; confidence?: number }[];
  agent?: Record<string, unknown>;
  attack_path?: Record<string, unknown>;
  categories?: Record<string, unknown>[];
  total_categories?: number;
  high_risk_cases?: Record<string, unknown>[];
  findings?: Finding[];
  recommendations?: Record<string, unknown>[];
  radar?: Record<string, number>;
  stage_labels?: Record<string, string>;
  remediation?: { matrix: Record<string, Record<string, number>>; total: number };
  retest?: { versions: Record<string, unknown>[]; regression_failed: boolean };
  compliance?: Record<string, unknown>;
  benchmark?: Record<string, unknown>;
  coverage_pct?: number;
}

/** 九章报告正文：Report.chapters 即 build_report_payload 的产物（PRD 3.8.4.1）。 */
export function useReportChapters(campaignId: string | undefined) {
  return useQuery({
    queryKey: ['report-chapters', campaignId],
    queryFn: async (): Promise<ReportChapters | null> => {
      if (!campaignId) return null;
      const reports = await api.get<Report[]>(ROUTES.reports);
      const report = reports.find((r) => r.subject_id === campaignId);
      if (!report) return null;
      return { ...(report.chapters as ReportChapters), sec_score: report.sec_score, grade: report.grade };
    },
    enabled: Boolean(campaignId)
  });
}

/** 高危详情 + 分类别结果 + 根因（九章第 3/4/5 章数据源）。 */
export function useFindings(campaignId: string | undefined) {
  return useQuery({
    queryKey: ['findings', campaignId],
    queryFn: async (): Promise<Finding[]> => {
      const reports = await api.get<Report[]>(ROUTES.reports);
      const report = reports.find((r) => r.subject_id === campaignId);
      const raw = (report?.chapters as ReportChapters | undefined)?.findings ?? [];
      return Array.isArray(raw) ? raw : [];
    },
    enabled: Boolean(campaignId)
  });
}
/* ---------- 通用：轮询 ---------- */

/* ---------- 大模型接入（技术方案 7.2） ---------- */

/** 网关快照：是否在线、四角色模型路由、熔断状态、成本账。 */
export interface LlmStatus {
  provider: string;
  base_url: string;
  api_key: string;
  models: Record<'redteam' | 'target' | 'judge' | 'embedding', string>;
  configured: boolean;
  offline: boolean;
  circuit_open: boolean;
  last_error: string;
  timeout_s: number;
  max_retries: number;
  calls: number;
  online_calls: number;
  tokens: number;
  cost: number;
}

export interface LlmProviderPreset {
  name: string;
  base_url: string;
  models: Record<'redteam' | 'target' | 'judge' | 'embedding', string>;
}

export interface LlmProbe {
  ok: boolean;
  latency_ms: number;
  detail: string;
  models: string[];
}

export function useLlmStatus() {
  return useQuery({
    queryKey: ['llm-status'],
    queryFn: () => api.get<LlmStatus>(ROUTES.llmStatus),
    refetchInterval: 30_000,
    retry: false
  });
}

export function useLlmProviders() {
  return useQuery({
    queryKey: ['llm-providers'],
    queryFn: async (): Promise<LlmProviderPreset[]> => {
      const body = await api.get<{ providers: LlmProviderPreset[] }>(ROUTES.llmProviders);
      return body.providers ?? [];
    },
    staleTime: 5 * 60_000
  });
}

export function useLlmProbe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<LlmProbe>(ROUTES.llmProbe, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['llm-status'] })
  });
}

export function useLlmConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      provider?: string;
      base_url?: string;
      api_key?: string;
      redteam_model?: string;
      target_model?: string;
      judge_model?: string;
      embedding_model?: string;
    }) => api.post<LlmStatus & { probe: LlmProbe }>(ROUTES.llmConfig, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['llm-status'] })
  });
}

export function usePolling(effect: () => void, intervalMs: number, enabled = true): void {
  const ref = useRef(effect);
  ref.current = effect;
  useEffect(() => {
    if (!enabled) return;
    const id = window.setInterval(() => ref.current(), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs, enabled]);
}

export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

export function useLocalToggle(key: string, initial = false): [boolean, (v: boolean) => void] {
  const [value, setValue] = useState(() => {
    if (typeof window === 'undefined') return initial;
    return window.localStorage.getItem(key) === '1';
  });
  const set = useCallback(
    (v: boolean) => {
      setValue(v);
      window.localStorage.setItem(key, v ? '1' : '0');
    },
    [key]
  );
  return [value, set];
}
