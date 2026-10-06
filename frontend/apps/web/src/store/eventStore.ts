import { create } from 'zustand';
import type { BusEvent } from '@xian/types';
import type { ConnectionState as SocketState } from '../lib/ws/socket';

/** 事件流存储：驾驶舱实时事件（技术方案 5 store/eventStore）。 */
export interface EventState {
  events: BusEvent[];
  connection: SocketState;
  alert: string | null;
  append: (event: BusEvent) => void;
  setConnection: (state: SocketState) => void;
  pushAlert: (message: string | null) => void;
  clear: () => void;
}

const MAX_EVENTS = 500;

export const useEventStore = create<EventState>((set) => ({
  events: [],
  connection: 'idle',
  alert: null,
  append: (event) =>
    set((s) => {
      const events = [event, ...s.events].slice(0, MAX_EVENTS);
      const alert =
        event.type === 'alert'
          ? String(event.payload?.message ?? event.message ?? '')
          : s.alert;
      return { events, alert: alert && alert.length > 0 ? alert : s.alert };
    }),
  setConnection: (connection) => set({ connection }),
  pushAlert: (alert) => set({ alert }),
  clear: () => set({ events: [], alert: null })
}));