/**
 * 与 `xian_core.schemas` 一一对应的领域模型。
 * 所有字段名与后端 Pydantic 模型完全一致（snake_case），不做任何改写。
 */
import type {
  AccessType,
  AgentStatus,
  CampaignStatus,
  Difficulty,
  JudgeLevel,
  JudgeMode,
  Intensity,
  OutputMode,
  OwnershipMethod,
  OwnershipResult,
  Role,
  SessionMode,
  SessionStatus,
  Severity,
  ToolScope,
  Verdict
} from './enums';

export interface Uuid extends String {}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface PageParams {
  page?: number;
  size?: number;
  keyword?: string;
  sort_by?: string;
  sort_desc?: boolean;
}

/* ---------- Agent 资产（PRD 3.2） ---------- */

export interface BaselineDeclaration {
  has_guardrail: boolean;
  guardrail_vendor: string;
  tool_scope: string;
  network_enabled: boolean;
  has_rag: boolean;
  has_long_term_memory: boolean;
}

export interface Agent {
  id: string;
  tenant_id: string;
  name: string;
  access_type: AccessType;
  endpoint: string;
  description: string;
  ownership_verified: boolean;
  ownership_method: OwnershipMethod | null;
  baseline_declaration: Record<string, unknown>;
  status: AgentStatus;
  created_at: string;
  updated_at?: string | null;
}

export interface AgentCreate {
  name: string;
  access_type: AccessType;
  endpoint: string;
  description?: string;
  baseline_declaration?: Partial<BaselineDeclaration>;
}

export interface AgentUpdate {
  name?: string;
  endpoint?: string;
  description?: string;
  baseline_declaration?: Partial<BaselineDeclaration>;
  status?: AgentStatus;
}

export interface VerificationRequest {
  method: OwnershipMethod;
  target: string;
}

export interface VerificationRecord {
  id: string;
  agent_id: string;
  method: OwnershipMethod;
  target: string;
  nonce: string;
  result: OwnershipResult;
  detail: string;
  ts: string;
}

export interface HealthCheck {
  id: string;
  agent_id: string;
  latency_ms: number;
  trace_sample: Record<string, unknown>[];
  result: string;
  ts: string;
}

export interface AgentVersion {
  id: string;
  agent_id: string;
  prompt_hash: string;
  tools_snapshot: Record<string, unknown>[];
  model_params: Record<string, unknown>;
  diff_summary: Record<string, unknown>;
  source: string;
  created_at: string;
}

export interface AgentProfile {
  id: string;
  agent_id: string;
  tools: Record<string, unknown>[];
  risk_levels: Record<string, string>;
  refusal_boundary: string;
  prompt_fragments: string[];
  fingerprint: Record<string, unknown>;
  latency_p50: number;
  latency_p99: number;
  lang_prefs: string[];
  created_at: string;
}

export interface ChangeSignal {
  id: string;
  agent_id: string;
  kind: string;
  diff_preview: Record<string, unknown>;
  handled: boolean;
  ts: string;
}

export interface ScenarioRecommendation {
  scenario_id: string;
  scenario_code: string;
  name: string;
  difficulty: Difficulty;
  match_score: number;
  matched_tools: string[];
  reason: string;
}

/* ---------- 战役（PRD 3.3） ---------- */

export interface Budget {
  token: number;
  cases: number;
  minutes: number;
}

export interface DagNode {
  id: string;
  /** 攻击类别编码 XM-xx，与矩阵类别表的 code 对应 */
  category_code: string;
  /** kill chain 阶段：recon / initial_exec / payload_delivery / privilege_escalation / exfiltration / impact */
  stage: string;
  case_ids: string[];
  budget_split: Record<string, number>;
  depends_on: string[];
  weight: number;
}

export interface CampaignPlan {
  dag_nodes?: DagNode[];
  edges: [string, string][];
  budget_split: Record<string, Record<string, number>>;
  constraints: Record<string, unknown>;
}

export interface Campaign {
  id: string;
  tenant_id: string;
  agent_id: string;
  agent_version_id: string | null;
  scenario_instance_id: string | null;
  scope: string[];
  intensity: Intensity;
  budget: Record<string, unknown>;
  constraints: Record<string, unknown>;
  judge_mode: JudgeMode;
  output_mode: OutputMode;
  preset_id: string;
  status: CampaignStatus;
  sec_score: number | null;
  grade: string | null;
  plan_dag: Record<string, unknown>;
  progress: number;
  created_by: string | null;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

export interface CampaignCreate {
  agent_id: string;
  scenario_id?: string | null;
  agent_version_id?: string | null;
  scope?: string[];
  intensity?: Intensity;
  budget?: Budget;
  constraints?: Record<string, unknown>;
  judge_mode?: JudgeMode;
  output_mode?: OutputMode;
  preset_id?: string;
}

export interface CampaignUpdate {
  scope?: string[];
  intensity?: Intensity;
  budget?: Budget;
  constraints?: Record<string, unknown>;
  judge_mode?: JudgeMode;
  output_mode?: OutputMode;
  status?: CampaignStatus;
}

/* ---------- 攻击记录与判定（PRD 3.3.5 / 3.6） ---------- */

export interface AttackRecord {
  id: string;
  tenant_id: string;
  agent_id: string;
  agent_version_id: string | null;
  campaign_id: string | null;
  session_id: string | null;
  case_id: string;
  category_code: string;
  strategy: string;
  mutation_ops: string[];
  turns: number;
  verdict: Verdict;
  confidence: number;
  rule_hits: Record<string, unknown>[];
  evidence: Record<string, unknown>[];
  tokens: number;
  cost: number;
  trace_key: string;
  created_at: string;
}

export interface VerdictRecord {
  id: string;
  record_id: string;
  level: JudgeLevel;
  result: Verdict;
  confidence: number;
  rule_hits: Record<string, unknown>[];
  evidence: Record<string, unknown>[];
  judge_model: string;
  reason: string;
  ts: string;
}

/* ---------- 场景与蜜标（PRD 3.1） ---------- */

export interface ScenarioTool {
  name: string;
  scope: ToolScope;
  risk_level: string;
  require_confirm: boolean;
  description: string;
}

export interface Scenario {
  id: string;
  code: string;
  name: string;
  category: string;
  difficulty: Difficulty;
  description: string;
  agent_form: string;
  baseline_tasks: number;
  script: string[];
  default_difficulty: string;
  tools: ScenarioTool[];
  canary_types: string[];
  monitors: string[];
  exam_tags: string[];
  typical_attack_chain: string[];
  env_template: Record<string, unknown>;
  status: string;
}

export interface ScenarioInstance {
  id: string;
  scenario_id: string;
  tenant_id: string;
  seed_data_snapshot: Record<string, unknown>;
  status: string;
  created_at: string;
  expired_at: string | null;
}

export interface InstanceCreate {
  scenario_id: string;
  data_scale?: number;
  language?: string;
  canary_enhanced?: boolean;
  run_baseline?: boolean;
}

/* ---------- 模式二会话（PRD 3.4.4） ---------- */

export interface SessionCreate {
  agent_id: string;
  scenario_instance_id?: string | null;
  mode?: SessionMode;
  level_id?: string | null;
  goal?: string;
}

export interface Session {
  id: string;
  user_id: string;
  tenant_id: string;
  agent_id: string;
  scenario_instance_id: string | null;
  mode: SessionMode;
  level_id: string | null;
  goal: string;
  status: SessionStatus;
  started_at: string;
  ended_at: string | null;
}

export interface SessionMessage {
  id: string;
  session_id: string;
  role: string;
  content: string;
  payload_ref: string | null;
  trace_ref: string | null;
  ts: string;
}

export interface BattleCard {
  id: string;
  session_id: string;
  category_id: string;
  severity: Severity;
  evidence: Record<string, unknown>[];
  payload: string;
  created_at: string;
}

/* ---------- 关卡（PRD 3.4.5） ---------- */

export interface Level {
  id: string;
  name: string;
  scenario_code: string;
  goal: string;
  pass_criteria: Record<string, unknown>;
  techniques: string[];
  hints: Record<string, string>;
  unlock_rule: string;
  difficulty: Difficulty;
}

export interface LevelProgress {
  id: string;
  user_id: string;
  level_id: string;
  status: string;
  score: number;
  time_used: number;
  hints_used: string[];
  energy_left: number;
  dimension_coverage: Record<string, number>;
  badge: string | null;
}

export interface HintResult {
  level: string;
  content: string;
  energy_cost: number;
  energy_left: number;
}

export interface UserProfile {
  user_id: string;
  radar: Record<string, number>;
  points: number;
  tier: string;
  badges: string[];
}

/* ---------- 攻击矩阵（PRD 3.5.4） ---------- */

export interface AttackCategory {
  id: string;
  code: string;
  name: string;
  stage: string;
  attack_surface: string;
  difficulty: Difficulty;
  impact: string;
  techniques: string[];
  detection_signals: string[];
  owasp_ref: string[];
  atlas_ref: string[];
}

export interface AttackCase {
  id: string;
  category_id: string;
  title: string;
  payload_template: string;
  variables: string[];
  scenario_tags: string[];
  difficulty: Difficulty;
  severity: Severity;
  success_criteria: Record<string, unknown>;
  judge_prompt: string;
  success_rate: number;
  status: string;
  version: number;
  contributor: string;
}

export interface MutationOpSpec {
  name: string;
  type: string;
  semantics_safe: boolean;
  success_rate: number;
  description: string;
}

/* ---------- 报告 / 修复 / 门禁（PRD 3.7 / 3.8） ---------- */

export interface DimensionScore {
  score: number;
  weight: number;
  sample_sufficient: boolean;
  categories: Record<string, number>;
}

export interface Score {
  id: string;
  subject_type: string;
  subject_id: string;
  sec_score: number;
  grade: string;
  dimension_scores: Record<string, DimensionScore>;
  category_asr: Record<string, number>;
  percentile: number | null;
  segment: string;
  computed_at: string;
}

export interface Report {
  id: string;
  subject_type: string;
  subject_id: string;
  version: number;
  sec_score: number;
  grade: string;
  chapters: Record<string, unknown>;
  object_keys: Record<string, string>;
  share: Record<string, unknown>;
  created_at: string;
}

export interface RootCause {
  code: string;
  name: string;
  category: string;
  fix_playbook_ref: string;
}

export interface Finding {
  id: string;
  campaign_id: string;
  record_ids: string[];
  root_cause_code: string;
  severity: Severity;
  affected_config: Record<string, unknown>;
  impact: string;
  trace_refs: string[];
  evidence: Record<string, unknown>[];
}

export interface Recommendation {
  id: string;
  finding_id: string;
  type: string;
  priority: string;
  effort: string;
  diff_payload: Record<string, unknown>;
  playbook_ref: string;
  expected_effect: string;
  side_effects: string;
  applied: boolean;
}

export interface RemediationRun {
  id: string;
  recommendation_id: string;
  applied_at: string;
  before_sec_score: number;
  after_sec_score: number;
  before_asr: number;
  after_asr: number;
  regression_pass_rate: number;
  status: string;
}

export interface GateRule {
  id: string;
  tenant_id: string;
  max_score_drop: number;
  block_on_severity: string;
  enabled: boolean;
}

export interface ScanJob {
  id: string;
  agent_id: string;
  trigger: string;
  status: string;
  verdict: Verdict | null;
  ci_context: Record<string, unknown>;
  pipeline_url: string;
  exit_code: number | null;
}

export interface TrendPoint {
  agent_id: string;
  version_id: string;
  sec_score: number;
  ts: string;
}

export interface Member {
  id: string;
  tenant_id: string;
  user_id: string;
  email: string;
  name: string;
  role: Role;
  status: string;
}

export interface AuditLog {
  id: string;
  tenant_id: string;
  user_id: string;
  action: string;
  resource: string;
  resource_id: string;
  detail: Record<string, unknown>;
  ts: string;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  user: { id: string; email: string; name: string; role: Role };
}

export interface Me {
  id: string;
  email: string;
  name: string;
  role: Role;
  tenant_id: string;
}

export interface AchievementOut {
  id: string;
  name: string;
  condition: string;
  rarity: string;
}
