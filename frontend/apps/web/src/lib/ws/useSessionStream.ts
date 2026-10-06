import { useEffect } from 'react';
import type { BusEvent } from '@xian/types';
import { useConsoleStore } from '../../store/consoleStore';
import { useEventStore } from '../../store/eventStore';
import { EventSocket } from './socket';

/** 订阅会话频道 `sessions:{id}`，token 流与战报卡片经此下发（技术方案 6.6）。 */
export function useSessionStream(sessionId: string | undefined) {
  const appendStream = useConsoleStore((s) => s.appendStream);
  const appendCard = useConsoleStore((s) => s.appendCard);
  const appendEvent = useEventStore((s) => s.append);
  const setConnection = useEventStore((s) => s.setConnection);
  const clearEvents = useEventStore((s) => s.clear);

  useEffect(() => {
    if (!sessionId) return;
    /* eventStore 是全局单例：切换会话前先清空，避免战役页事件串台到自由攻击页 */
    clearEvents();
    const socket = new EventSocket({
      url: `/ws/session/${sessionId}`,
      onEvent: (event: BusEvent) => {
        appendEvent(event);
        /* verdict 也要进流：教官面板「最近判定」直接消费 consoleStore.stream */
        if (event.type === 'log' || event.type === 'tool_call' || event.type === 'verdict') appendStream(event);
        if (event.type === 'battle_card') appendCard(event);
      },
      onStateChange: setConnection
    });
    socket.connect();
    return () => socket.close();
  }, [sessionId, appendStream, appendCard, appendEvent, setConnection, clearEvents]);
}
