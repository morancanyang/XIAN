import { useEffect, useRef } from 'react';
import type { BusEvent } from '@xian/types';
import { useEventStore } from '../../store/eventStore';
import { EventSocket, type ConnectionState } from './socket';

/**
 * 订阅战役频道 `campaign:{id}`（技术方案 6.6）。
 * 事件统一进 eventStore，页面按需读取；卸载时断开连接。
 */
export function useCampaignStream(campaignId: string | undefined): ConnectionState {
  const append = useEventStore((s) => s.append);
  const setConnection = useEventStore((s) => s.setConnection);
  const clear = useEventStore((s) => s.clear);
  const socketRef = useRef<EventSocket | null>(null);

  useEffect(() => {
    if (!campaignId) return;
    /* eventStore 是全局单例：切换频道前先清空，否则会串台显示上一页会话的事件 */
    clear();
    const socket = new EventSocket({
      url: `/ws/campaign/${campaignId}`,
      onEvent: (event: BusEvent) => append(event),
      onStateChange: setConnection
    });
    socketRef.current = socket;
    socket.connect();
    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [campaignId, append, setConnection, clear]);

  return useEventStore((s) => s.connection);
}