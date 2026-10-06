import Dexie, { type Table } from 'dexie';

/**
 * 前端本地库（技术方案 6.5，Dexie / IndexedDB，与后端库完全分离）。
 * 仅存放可重建的本地缓存：草稿战役、离线 trace、最近告警。
 */

export interface DraftCampaign {
  id: string;
  agent_id: string;
  scope: string[];
  intensity: string;
  budget: Record<string, number>;
  judge_mode: string;
  output_mode: string;
  updated_at: string;
}

export interface CachedTrace {
  id: string;
  record_id: string;
  events: unknown[];
  cached_at: string;
}

export interface LocalAlert {
  id: string;
  message: string;
  severity: string;
  ts: string;
}

export class XianDatabase extends Dexie {
  drafts!: Table<DraftCampaign, string>;
  traces!: Table<CachedTrace, string>;
  alerts!: Table<LocalAlert, string>;

  constructor(name = 'xian-web') {
    super(name);
    this.version(1).stores({
      drafts: 'id, agent_id, updated_at',
      traces: 'id, record_id, cached_at',
      alerts: 'id, ts, severity'
    });
  }
}

export const db = new XianDatabase();

export async function saveDraft(draft: DraftCampaign): Promise<void> {
  await db.drafts.put(draft);
}

export async function listDrafts(): Promise<DraftCampaign[]> {
  return db.drafts.orderBy('updated_at').reverse().toArray();
}

export async function cacheTrace(trace: CachedTrace): Promise<void> {
  await db.traces.put(trace);
}

export async function readTrace(recordId: string): Promise<CachedTrace | undefined> {
  return db.traces.where('record_id').equals(recordId).first();
}

export async function recordAlert(alert: LocalAlert): Promise<void> {
  await db.alerts.put(alert);
}