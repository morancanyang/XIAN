import { useEventStore } from '../../../store/eventStore';
import { EVENT_ROLE_LABEL } from '@xian/types';
import type { BusEvent } from '@xian/types';
import { fmtClock } from '../../../lib/utils/format';
import { PulseDot } from '@xian/ui';
import { cn } from '../../../lib/utils/cn';

const ROLE_ORDER: Record<string, number> = {
  commander: 0,
  recon: 1,
  payload: 2,
  mutator: 3,
  attacker: 4,
  judge: 5,
  reporter: 6,
  system: 7
};

/** 中部角色活动流（技术方案 8.4 模式一）：按角色聚合展示当前正在发生什么。 */
export function RoleActivityFeed({ className }: { className?: string }) {
  const events = useEventStore((s) => s.events).slice(0, 80);

  const grouped = events.reduce<Record<string, BusEvent[]>>((acc, e) => {
    const role = e.role ?? 'system';
    (acc[role] ??= []).push(e);
    return acc;
  }, {});

  const roles = Object.keys(grouped).sort((a, b) => (ROLE_ORDER[a] ?? 9) - (ROLE_ORDER[b] ?? 9));

  return (
    <div className={cn('space-y-3', className)}>
      {roles.map((role) => (
        <div key={role} className="rounded-card border border-border bg-elevated/60 p-3">
          <div className="mb-2 flex items-center gap-2">
            <PulseDot tone={role === 'attacker' || role === 'payload' ? 'red' : role === 'judge' ? 'coach' : 'blue'} active={role === 'attacker' || role === 'judge'} />
            <span className="text-xs font-semibold text-content">{EVENT_ROLE_LABEL[role as keyof typeof EVENT_ROLE_LABEL]}</span>
            <span className="ml-auto text-[10px] text-content-faint">{grouped[role].length} 条</span>
          </div>
          <ul className="space-y-1">
            {grouped[role].slice(0, 4).map((e) => (
              <li key={`${e.ts}-${e.type}`} className="flex gap-2 text-[11px] text-content-muted">
                <span className="font-mono text-content-faint">{fmtClock(e.ts)}</span>
                <span className="min-w-0 flex-1 truncate">{e.message || e.type}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
      {roles.length === 0 ? <p className="text-xs text-content-faint">连接战役频道后展示角色活动。</p> : null}
    </div>
  );
}