/**
 * Agent 详情页归属校验：目标默认取 Agent 端点主机名。
 *
 * 背景：目标输入框原先硬编码占位域名 agent.example.com，用户照着实测必然失败——
 * 那个域名既没有对应 TXT 记录，也不属于被接入的 Agent（demo Agent 跑在 127.0.0.1）。
 * 现在默认从端点推导，用户没改过就直接提交推导值；改过则以用户为准。
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, test, vi } from 'vitest';
import type { ReactElement } from 'react';

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverStub;

const AGENT_ID = '3735c399-4afc-456d-b495-3fe9ebb2f7c3';

const AGENT = {
  id: AGENT_ID,
  tenant_id: '00000000-0000-0000-0000-000000000001',
  name: '演示 Agent',
  access_type: 'http',
  endpoint: 'http://127.0.0.1:9001/chat',
  description: '',
  ownership_verified: false,
  ownership_method: null,
  baseline_declaration: {},
  status: 'ready',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: null
};

const verifyMutate = vi.fn(async (body: { method: string; target: string }) => ({
  result: 'verified',
  detail: `TXT 记录匹：${body.target}`
}));

vi.mock('../src/lib/api/hooks', () => ({
  useAgent: () => ({ data: AGENT, isLoading: false, isError: false, error: null, refetch: vi.fn() }),
  useAgentHealthcheck: () => ({ data: null, isPending: false, mutateAsync: vi.fn() }),
  useAgentRecon: () => ({ data: null, isPending: false, mutateAsync: vi.fn() }),
  useAgentRecommendations: () => ({ data: [] }),
  useAgentVersions: () => ({ data: [] }),
  useCreateAgentVersion: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useUpdateAgent: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useVerifyAgent: () => ({ data: null, isPending: false, mutateAsync: verifyMutate, error: null, isError: false })
}));

vi.mock('../src/components/layout/ToastHost', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), dismiss: vi.fn() })
}));

let DetailPage: () => ReactElement;

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/agents/${AGENT_ID}`]}>
        <Routes>
          <Route path="/agents/:agentId" element={<DetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('AgentDetailPage 归属校验目标', () => {
  test('默认取 Agent 端点主机名，不再硬编码占位域名', async () => {
    DetailPage = (await import('../src/pages/agents/AgentDetailPage')).default;
    renderPage();

    await waitFor(() =>
      expect((screen.getByLabelText('目标') as HTMLInputElement).value).toBe('127.0.0.1')
    );
  });

  test('未改过目标时提交端点主机名', async () => {
    DetailPage = (await import('../src/pages/agents/AgentDetailPage')).default;
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: '开始校验' }));
    await waitFor(() => expect(verifyMutate).toHaveBeenCalledTimes(1));
    expect(verifyMutate.mock.calls[0][0]).toEqual({ method: 'dns_txt', target: '127.0.0.1' });
  });

  test('用户改过目标后按用户的值提交', async () => {
    DetailPage = (await import('../src/pages/agents/AgentDetailPage')).default;
    renderPage();

    fireEvent.change(screen.getByLabelText('目标'), { target: { value: 'agent.corp.com' } });
    fireEvent.click(screen.getByRole('button', { name: '开始校验' }));
    await waitFor(() => expect(verifyMutate).toHaveBeenCalledTimes(1));
    expect(verifyMutate.mock.calls[0][0]).toEqual({ method: 'dns_txt', target: 'agent.corp.com' });
  });
});
