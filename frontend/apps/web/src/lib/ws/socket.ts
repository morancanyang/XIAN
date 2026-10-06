import type { BusEvent } from '@xian/types';

import { wsOrigin } from '../config/backend';

/**
 * WebSocket 客户端（技术方案 6.6）。
 * 单例管理连接生命周期，指数退避重连，断线期间事件入本地队列，恢复后补发。
 */

export type ConnectionState = 'idle' | 'connecting' | 'open' | 'closed' | 'error';

export interface SocketOptions {
  url: string;
  onEvent: (event: BusEvent) => void;
  onStateChange?: (state: ConnectionState) => void;
  maxQueue?: number;
}

export class EventSocket {
  private ws: WebSocket | null = null;
  private queue: BusEvent[] = [];
  private retry = 0;
  private closedByUser = false;
  private timer: number | undefined;
  private readonly maxQueue: number;

  state: ConnectionState = 'idle';

  constructor(private readonly options: SocketOptions) {
    this.maxQueue = options.maxQueue ?? 500;
  }

  connect(): void {
    if (typeof window === 'undefined') return;
    this.closedByUser = false;
    this.setState('connecting');

    /* 后端地址可运行时配置：配置了就走配置的 origin，否则同源（开发态由 Vite 代理） */
    const configured = wsOrigin();
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = window.location.host;
    const url = this.options.url.startsWith('ws')
      ? this.options.url
      : configured
        ? `${configured}${this.options.url}`
        : `${scheme}://${host}${this.options.url}`;

    try {
      this.ws = new WebSocket(url);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.retry = 0;
      this.setState('open');
      this.flush();
    };

    this.ws.onmessage = (raw) => {
      try {
        const event = JSON.parse(String(raw.data)) as BusEvent;
        this.options.onEvent(event);
      } catch {
        /* 忽略畸形帧 */
      }
    };

    this.ws.onerror = () => this.setState('error');

    this.ws.onclose = () => {
      this.setState('closed');
      if (!this.closedByUser) this.scheduleReconnect();
    };
  }

  close(): void {
    this.closedByUser = true;
    if (this.timer) window.clearTimeout(this.timer);
    this.ws?.close();
    this.ws = null;
  }

  private scheduleReconnect(): void {
    if (this.timer) return;
    const delay = Math.min(8000, 500 * 2 ** this.retry);
    this.retry += 1;
    this.timer = window.setTimeout(() => {
      this.timer = undefined;
      this.connect();
    }, delay);
  }

  private setState(state: ConnectionState): void {
    this.state = state;
    this.options.onStateChange?.(state);
  }

  /** 连接断开时本地缓存事件，恢复后补发（最多 maxQueue 条）。 */
  enqueue(event: BusEvent): void {
    if (this.queue.length >= this.maxQueue) this.queue.shift();
    this.queue.push(event);
  }

  private flush(): void {
    const pending = this.queue.splice(0, this.queue.length);
    for (const event of pending) this.options.onEvent(event);
  }
}