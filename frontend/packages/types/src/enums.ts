/**
 * 与 `xian_core.schemas.common` 一一对应的枚举字面量联合类型。
 * 由 `openapi.generated.ts` 的 schema 派生，不在此处发明新取值。
 */

export type AccessType = 'http' | 'sdk' | 'container';

/** Agent 资产状态机（技术方案 2.2）：未验证 → 已归属验证 → 演练中 ⇄ 下线/已归档 */
export type AgentStatus = 'unverified' | 'active' | 'testing' | 'offline' | 'archived';

export type OwnershipMethod = 'dns_txt' | 'image_digest';

export type OwnershipResult = 'verified' | 'pending' | 'failed';

export type Intensity = 'recon' | 'standard' | 'deep';

export type JudgeMode = 'loose' | 'standard' | 'strict';

export type OutputMode = 'summary' | 'full' | 'reproducible';

/** PRD 2.2.4 战役状态机 */
export type CampaignStatus =
  | 'draft'
  | 'scheduled'
  | 'preparing'
  | 'attacking'
  | 'analyzing'
  | 'reporting'
  | 'completed'
  | 'cancelled'
  | 'tripped'
  | 'env_failed'
  | 'failed';

export type Verdict = 'success' | 'partial' | 'fail' | 'unavailable';

export type JudgeLevel = 'golden' | 'classifier' | 'llm';

export type SessionMode = 'console' | 'level' | 'defense';

export type SessionStatus = 'active' | 'archived';

export type Role = 'owner' | 'blue' | 'red' | 'analyst' | 'admin';

export type Severity = 'critical' | 'high' | 'medium' | 'low';

export type Difficulty = 'beginner' | 'easy' | 'low' | 'medium' | 'hard' | 'expert';

export type ToolScope = 'read' | 'write' | 'exec' | 'network';

export const AGENT_STATUS_LABEL: Record<AgentStatus, string> = {
  unverified: '未归属验证',
  active: '可演练',
  testing: '演练中',
  offline: '已下线',
  archived: '已归档'
};

export const CAMPAIGN_STATUS_LABEL: Record<CampaignStatus, string> = {
  draft: '草稿',
  scheduled: '已排期',
  preparing: '环境准备',
  attacking: '攻击中',
  analyzing: '分析中',
  reporting: '报告生成',
  completed: '已完成',
  cancelled: '已取消',
  tripped: '预算熔断',
  env_failed: '环境失败',
  failed: '执行失败'
};

export const VERDICT_LABEL: Record<Verdict, string> = {
  success: '命中',
  partial: '部分命中',
  fail: '未命中',
  unavailable: '不可判定'
};

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: '致命',
  high: '高危',
  medium: '中危',
  low: '低危'
};

export const DIFFICULTY_LABEL: Record<Difficulty, string> = {
  beginner: '入门',
  easy: '简单',
  low: '较低',
  medium: '中等',
  hard: '困难',
  expert: '专家'
};

export const ROLE_LABEL: Record<Role, string> = {
  owner: '负责人',
  blue: '蓝军',
  red: '红军',
  analyst: '分析师',
  admin: '管理员'
};
/** 九章报告目录（与 xian_core.reports.render.CHAPTERS 一致）。 */
export const CHAPTERS = [
  '执行摘要',
  'Agent 画像与攻击面清单',
  '攻击路径图',
  '分类别结果',
  '高危详情',
  '根因分析与修复建议',
  '整改清单',
  '复测对比',
  '合规映射'
] as const;

export type ChapterName = (typeof CHAPTERS)[number];