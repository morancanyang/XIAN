import { useEffect, useRef } from 'react';
import { FaultyTerminalBackdrop } from './FaultyTerminalBackdrop';
import { TraceTerminal } from '@xian/ui';
import type { BusEvent } from '@xian/types';
import { fmtClock } from '../../../lib/utils/format';

export interface ObservationPanelProps {
  events: BusEvent[];
  className?: string;
}

/** 把事件流转成终端行文本（xterm 风格回放）。 */
export function toTerminalLines(events: BusEvent[]): string[] {
  return events
    .slice(0, 120)
    .map(
      (e) => `[${fmtClock(e.ts)}] ${e.role ?? 'system'} ${e.type} ${e.message ?? JSON.stringify(e.payload ?? {})}`
    );
}

/** 底部观测面板：FaultyTerminal 底层 + xterm 终端（技术方案 8.4）。 */
export function ObservationPanel({ events, className }: ObservationPanelProps) {
  const lines = toTerminalLines(events);
  const lastCount = useRef(0);
  useEffect(() => {
    lastCount.current = events.length;
  }, [events.length]);

  return (
    <div className={className}>
      <div className="relative overflow-hidden rounded-card border border-border">
        <div className="pointer-events-none absolute inset-0 z-0 opacity-30">
          <FaultyTerminalBackdrop />
        </div>
        <div className="relative z-10 p-3">
          <TraceTerminal lines={lines} height={220} />
        </div>
      </div>
    </div>
  );
}