import { useEffect, useRef } from 'react';
import { cn } from '../../../lib/utils/cn';
import { fmtClock } from '../../../lib/utils/format';
import type { SessionMessage } from '@xian/types';

export interface ChatStreamProps {
  messages: SessionMessage[];
  streaming?: string;
  className?: string;
}

/** 对话流：token 逐字渲染（技术方案 8.4 / 8.6）。 */
export function ChatStream({ messages, streaming = '', className }: ChatStreamProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [messages.length, streaming]);

  return (
    <div className={cn('xian-scrollbar h-full space-y-3 overflow-y-auto pr-2', className)}>
      {messages.map((m) => (
        <div
          key={m.id}
          className={cn(
            'max-w-[85%] rounded-card border px-3 py-2 text-sm',
            m.role === 'user'
              ? 'ml-auto border-blue-team/40 bg-blue-team/10'
              : 'border-border bg-elevated'
          )}
        >
          <div className="mb-1 flex items-center gap-2 text-[10px] text-content-faint">
            <span>{m.role === 'user' ? '我' : 'Agent'}</span>
            <span className="font-mono">{fmtClock(new Date(m.ts).getTime())}</span>
            {m.payload_ref ? <span className="font-mono">payload: {m.payload_ref}</span> : null}
          </div>
          <p className="whitespace-pre-wrap break-words xian-cjk">{m.content}</p>
        </div>
      ))}

      {streaming ? (
        <div className="max-w-[85%] rounded-card border border-coach/40 bg-coach/5 px-3 py-2 text-sm">
          <p className="mb-1 text-[10px] text-content-faint">Agent（流式）</p>
          <p className="whitespace-pre-wrap break-words xian-cjk">{streaming}</p>
        </div>
      ) : null}
      <div ref={bottomRef} />
    </div>
  );
}