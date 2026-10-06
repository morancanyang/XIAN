/**
 * 运行时后端地址（评审 / 移动端场景）。
 *
 * 浏览器开发态：留空表示同源，由 Vite 代理 /api 与 /ws 到 127.0.0.1:8000。
 * APK / 真机：WebView 的 origin 是本地卷，同源代理不存在，必须在界面里显式
 * 指定后端地址（如 http://192.168.1.5:8000），因此该值可运行时修改并持久化。
 */

const STORAGE_KEY = 'xian.backend';

/** 构建期默认值（可选）：VITE_API_BASE_URL */
const BUILD_DEFAULT: string = import.meta.env.VITE_API_BASE_URL ?? '';

/** 规范化：去尾部斜杠；空串表示同源。 */
export function normalizeBase(raw: string): string {
  const v = (raw ?? '').trim();
  if (!v || v === '/') return '';
  return v.replace(/\/+$/, '');
}

/** 读取当前后端地址（localStorage 优先，其次构建期默认值）。 */
export function getBackendBase(): string {
  if (typeof window === 'undefined') return normalizeBase(BUILD_DEFAULT);
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored !== null) return normalizeBase(stored);
  } catch {
    /* 隐私模式等场景降级 */
  }
  return normalizeBase(BUILD_DEFAULT);
}

/** 写入后端地址并广播，供已挂载的请求 / 连接感知。 */
export function setBackendBase(raw: string): void {
  const v = normalizeBase(raw);
  try {
    window.localStorage.setItem(STORAGE_KEY, v);
  } catch {
    /* 忽略写入失败 */
  }
  window.dispatchEvent(new CustomEvent('xian:backend-change', { detail: v }));
}

/**
 * 请求前缀：后端为绝对地址时拼上标准前缀 /api，同源时退回 /api。
 * 业务路径（ROUTES）已自带 /api/v1，故此处不能再重复 v1。
 */
export function apiBase(): string {
  const base = getBackendBase();
  return base ? `${base}/api` : '/api';
}

/**
 * WebSocket 绝对地址：由后端地址推导 ws/wss。
 * 未配置后端时返回 null，调用方应回退到同源拼接（开发态代理）。
 */
export function wsOrigin(): string | null {
  const base = getBackendBase();
  if (!base) return null;
  try {
    const u = new URL(base);
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${u.protocol}//${u.host}`;
  } catch {
    return null;
  }
}

/** 是否已配置为远程后端（用于界面提示）。 */
export function isRemoteBackend(): boolean {
  return getBackendBase() !== '';
}
