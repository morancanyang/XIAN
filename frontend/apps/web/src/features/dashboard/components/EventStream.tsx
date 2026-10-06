import { useEventStore } from '../../../store/eventStore';
import { StaggerList } from '@xian/ui';
import { EVENT_ROLE_LABEL, EVENT_TYPE_LABEL } from '@xian/types';
import type { BusEvent } from '@xian/types';
import { fmtClock, shortId } from '../../../lib/utils/format';
import { cn } from '../../../lib/utils/cn';

/** 实时事件流：新事件滑入，告警事件高亮（技术方案 8.4 / 8.6）。 */
export function EventStream({ limit = 40, className }: { limit?: number; className?: string }) {
  const events = useEventStore((s) => s.events).slice(0, limit);

  return (
    <div className={cn('h-full overflow-hidden', className)}>
      <StaggerList
        as="ul"
        step={0.02}
        className="xian-scrollbar max-h-[420px] space-y-1 overflow-y-auto pr-1"
        items={events}
        keyOf={(e: BusEvent) => `${e.ts}-${e.type}-${shortId(String(e.payload?.id ?? ''), 6, 4)}`}
        renderItem={(event) => (
          <li
            className={cn(
              'flex items-start gap-2 rounded-control border px-2.5 py-2 text-xs',
              event.type === 'alert'
                ? 'border-red-team/40 bg-red-team/10'
                : event.type === 'verdict'
                  ? 'border-blue-team/30 bg-blue-team/5'
                  : 'border-border bg-elevated/50'
            )}
          >
            <span className="mt-0.5 font-mono text-[10px] text-content-faint">{fmtClock(event.ts)}</span>
            <span className="shrink-0 rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-content-muted">
              {EVENT_ROLE_LABEL[event.role ?? 'system']}
            </span>
            <span className="shrink-0 text-[10px] text-blue-team">{EVENT_TYPE_LABEL[event.type]}</span>
            <span className="min-w-0 flex-1 break-words text-content-muted">
              {event.message || JSON.stringify(event.payload ?? {})}
            </span>
          </li>
        )}
      />
      {events.length === 0 ? (
        <p className="px-2 py-8 text-center text-xs text-content-faint">暂无事件，连接战役或会话后实时推送</p>
      ) : null}
    </div>
  );
}