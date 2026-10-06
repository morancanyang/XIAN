/**
 * WS/SSE 事件契约（技术方案 6.6 / xian_core.schemas.events）。
 * 频道：`campaign:{id}` 与 `sessions:{id}` 复用同一 schema；
 * mode=console 时在 type 中扩展 battle_card / hint_used / energy / level_progress。
 */

export type EventType =
  | 'log'
  | 'tool_call'
  | 'verdict'
  | 'progress'
  | 'alert'
  | 'done'
  | 'battle_card'
  | 'hint_used'
  | 'energy'
  | 'level_progress';

export type EventRole =
  | 'commander'
  | 'recon'
  | 'payload'
  | 'attacker'
  | 'mutator'
  | 'judge'
  | 'reporter'
  | 'system';

export interface BusEvent {
  /** epoch millis */
  ts: number;
  type: EventType;
  role?: EventRole;
  message?: string;
  payload?: Record<string, unknown>;
  campaign_id?: string | null;
  session_id?: string | null;
}

export interface TraceEvent {
  id: string;
  tenant_id: string;
  subject_id: string;
  session_id?: string | null;
  event_type: 'llm_call' | 'tool_call' | 'output' | 'egress' | 'guardrail' | 'token';
  actor: string;
  name: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
  tokens: number;
  canary_hit: boolean;
  latency_ms: number;
  ts: string;
}

export const EVENT_ROLE_LABEL: Record<EventRole, string> = {
  commander: '指挥官',
  recon: '侦察兵',
  payload: '载荷构造',
  attacker: '攻击执行',
  mutator: '变形算子',
  judge: '裁判',
  reporter: '报告官',
  system: '系统'
};

export const EVENT_TYPE_LABEL: Record<EventType, string> = {
  log: '日志',
  tool_call: '工具调用',
  verdict: '判定结果',
  progress: '进度',
  alert: '告警',
  done: '完成',
  battle_card: '战报卡片',
  hint_used: '提示使用',
  energy: '能量变化',
  level_progress: '关卡进度'
};