import { ROUTES } from '@xian/types';

import { apiBase } from '../config/backend';

/**
 * 轻量 HTTP 客户端（PRD 2.3.1）。
 * 统一注入租户上下文 header、错误归一化、超时与重试提示；业务 hook 全部经此出口。
 */

export interface ApiError {
  error: string;
  message: string;
  hint: string;
  status: number;
}

export class ApiClientError extends Error implements ApiError {
  error: string;
  hint: string;
  status: number;

  constructor(error: string, message: string, hint: string, status: number) {
    super(message);
    this.name = 'ApiClientError';
    this.error = error;
    this.hint = hint;
    this.status = status;
  }
}

export interface RequestContext {
  tenantId: string;
  userId: string;
  role: 'admin' | 'red' | 'blue' | 'viewer';
}

const STORAGE_KEY = 'xian.session';
const DEFAULT_CTX: RequestContext = {
  tenantId: '00000000-0000-0000-0000-000000000001',
  userId: '00000000-0000-0000-0000-0000000000a1',
  role: 'admin'
};

/** 租户上下文：本地持久化，登录 / 切换租户时覆写。 */
export function loadContext(): RequestContext {
  if (typeof window === 'undefined') return DEFAULT_CTX;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_CTX;
    return { ...DEFAULT_CTX, ...(JSON.parse(raw) as Partial<RequestContext>) };
  } catch {
    return DEFAULT_CTX;
  }
}

export function saveContext(ctx: RequestContext): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ctx));
  window.dispatchEvent(new CustomEvent('xian:context-change'));
}

export const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

/** 运行时后端前缀（可在界面中修改，见 lib/config/backend.ts）。 */
function apiPrefix(): string {
  return apiBase();
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
  /** 覆盖默认上下文（管理端 impersonate 场景） */
  context?: Partial<RequestContext>;
}

/** 拼接请求路径：合并 BASE_URL、清理重复斜杠、附带查询参数（单测直接断言该函数）。 */
export function buildRequestPath(path: string, query?: RequestOptions['query']): string {
  const base = apiPrefix();
  /* 绝对地址后端：直接拼到配置的 origin 之后 */
  let raw: string;
  if (path.startsWith('/api')) {
    /* ROUTES 已带 /api/v1 前缀，只需替换掉前导 /api */
    const suffix = path.slice(4);
    raw = base === '/api' ? path : `${base}${suffix}`;
  } else {
    raw = `${base}${path.startsWith('/') ? path : `/${path}`}`;
  }
  const url = raw.replace(/([^:]\/)\/+/g, '$1');
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue;
    params.set(k, String(v));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

const buildUrl = buildRequestPath;

function headers(ctx: RequestContext, hasBody: boolean): HeadersInit {
  const h: Record<string, string> = {
    'X-Tenant-Id': ctx.tenantId,
    'X-User-Id': ctx.userId,
    'X-Role': ctx.role
  };
  if (hasBody) h['Content-Type'] = 'application/json';
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('xian.token') : null;
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
}

/** 领域异常 → 用户可读提示（PRD 2.3.1）。 */
const HINTS: Record<string, string> = {
  OwnershipNotVerified: '该 Agent 尚未完成归属校验，请先在资产页完成 DNS TXT 或镜像摘要校验。',
  EgressBlocked: '出口被沙箱代理拦截，已按白名单策略阻断该次访问。',
  BudgetTripped: '战役预算已熔断，可在战役详情中调整预算后重试。',
  SandboxEnvFailed: '沙箱环境创建失败，请检查场景模板与 Docker 状态。',
  QuotaExceeded: '已超出配额，请联系管理员调整。',
  PermissionDenied: '当前角色无该操作权限。',
  ExportForbidden: '导出被管控策略拦截。'
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, signal, context } = options;
  const ctx = { ...loadContext(), ...context };
  const hasBody = body !== undefined;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers: headers(ctx, hasBody),
      body: hasBody ? JSON.stringify(body) : undefined,
      signal
    });
  } catch (err) {
    throw new ApiClientError('NetworkError', '网络请求失败，请检查后端服务是否已启动', String(err), 0);
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  let payload: unknown = text;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    /* 保留原文，交由上层展示 */
  }

  if (!response.ok) {
    const obj = (typeof payload === 'object' && payload !== null ? payload : {}) as Partial<ApiError> & {
      detail?: unknown;
    };
    const code = obj.error ?? `Http${response.status}`;
    // 未捕获异常（HTTP 500）返回的是纯文本而不是 {error,message}，此时要把原文带给用户，
    // 否则前端只剩一句「请求失败（HTTP 500）」，没法判断是渲染炸了还是别的原因。
    const raw = typeof payload === 'string' ? payload.trim() : '';
    const detail = typeof obj.detail === 'string' ? obj.detail.trim() : '';
    const reason = raw || detail;
    throw new ApiClientError(
      code,
      obj.message ??
        (reason ? `请求失败（HTTP ${response.status}）：${reason.slice(0, 200)}` : `请求失败（HTTP ${response.status}）`),
      obj.hint ?? HINTS[code] ?? '',
      response.status
    );
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions['query'], signal?: AbortSignal) =>
    apiRequest<T>(path, { method: 'GET', query, signal }),
  post: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: 'POST', body }),
  patch: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: 'PATCH', body }),
  put: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: 'PUT', body }),
  delete: <T>(path: string) => apiRequest<T>(path, { method: 'DELETE' }),
  download: async (path: string): Promise<{ blob: Blob; filename: string }> => {
    const ctx = loadContext();
    const res = await fetch(buildUrl(path), { headers: headers(ctx, false) });
    if (!res.ok) throw new ApiClientError('ExportFailed', `导出失败（HTTP ${res.status}）`, HINTS.ExportForbidden ?? '', res.status);
    const disposition = res.headers.get('content-disposition') ?? '';
    const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
    return { blob: await res.blob(), filename: match ? decodeURIComponent(match[1]) : 'xian-export' };
  }
};

export { ROUTES };