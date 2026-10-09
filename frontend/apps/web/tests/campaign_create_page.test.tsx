/**
 * 模式一创建页：并发投放数必须真的进到创建载荷里。
 *
 * 背景：后端 execute_campaign 已改成按 DAG 依赖分层并发（PRD 3.3.5.8.1 规则③），
 * 但创建向导一直没有暴露并发度，用户只能吃默认值 4——想压测目标或怕打爆
 * 目标时没有任何调节入口。这里锁死字段渲染与 constraints.concurrency 传递。
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, test, vi } from 'vitest';
import type { ReactElement } from 'react';

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverStub;

const AGENT_ID = '3735c399-4afc-456d-b495-3fe9ebb2f7c3';

const CATEGORIES = [
  { id: 'c1', code: 'XM-03', name: '系统提示词泄露', stage: '侦察', attack_surface: '提示词层',
    difficulty: 'low', impact: 'medium', techniques: [], detection_signals: [], owasp_ref: [], atlas_ref: [] },
  { id: 'c2', code: 'XM-05', name: '敏感数据渗出', stage: '渗出', attack_surface: '数据层/工具层',
    difficulty: 'medium', impact: 'high', techniques: [], detection_signals: [], owasp_ref: [], atlas_ref: [] }
];

const createMutate = vi.fn(async (body: Record<string, unknown>) => ({ id: 'c-1', body }));

vi.mock('../src/lib/api/hooks', () => ({
  useAgents: () => ({
    data: {
      items: [
        { id: AGENT_ID, name: '演示 Agent', access_type: 'http', endpoint: 'http://127.0.0.1:9001/chat',
          ownership_verified: true, status: 'ready', created_at: '2026-10-01T00:00:00Z' }
      ],
      total: 1, page: 1, size: 100
    }
  }),
  useMatrixCategories: () => ({ data: CATEGORIES }),
  useScenarioInstances: () => ({ data: [] }),
  useCreateCampaign: () => ({ isPending: false, mutateAsync: createMutate, error: null, isError: false }),
  usePreviewCampaignPlan: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useCampaignPlan: () => ({ isPending: false, mutateAsync: vi.fn() })
}));

vi.mock('../src/store/sessionStore', () => ({
  useSessionStore: (selector: (s: unknown) => unknown) =>
    selector({ activeAgentId: AGENT_ID, setActiveCampaign: vi.fn(), setActiveAgent: vi.fn() })
}));

vi.mock('../src/components/layout/ToastHost', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), dismiss: vi.fn() })
}));

let CreatePage: () => ReactElement;

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/campaigns/new']}>
        <CreatePage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

/** 勾一个类别：没选 scope 时创建按钮是禁用的。 */
function pickScope() {
  fireEvent.click(screen.getByRole('checkbox', { name: /XM-03/ }));
}

function submit() {
  fireEvent.click(screen.getByRole('button', { name: '创建战役' }));
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('CampaignCreatePage 并发投放数', () => {
  test('默认 4，且创建战役时随 constraints 一起提交', async () => {
    CreatePage = (await import('../src/pages/mode1/CampaignCreatePage')).default;
    renderPage();

    expect((screen.getByLabelText('并发投放数') as HTMLInputElement).value).toBe('4');

    pickScope();
    submit();
    await waitFor(() => expect(createMutate).toHaveBeenCalledTimes(1));
    expect(createMutate.mock.calls[0][0].constraints).toEqual({ concurrency: 4 });
  });

  test('改动后按输入值提交', async () => {
    CreatePage = (await import('../src/pages/mode1/CampaignCreatePage')).default;
    renderPage();

    fireEvent.change(screen.getByLabelText('并发投放数'), { target: { value: '8' } });
    pickScope();
    submit();
    await waitFor(() => expect(createMutate).toHaveBeenCalledTimes(1));
    expect(createMutate.mock.calls[0][0].constraints).toEqual({ concurrency: 8 });
  });

  test('超出 1~16 的输入被夹回边界，不会把非法并发度发给后端', async () => {
    CreatePage = (await import('../src/pages/mode1/CampaignCreatePage')).default;
    renderPage();

    fireEvent.change(screen.getByLabelText('并发投放数'), { target: { value: '99' } });
    pickScope();
    submit();
    await waitFor(() => expect(createMutate).toHaveBeenCalledTimes(1));
    expect(createMutate.mock.calls[0][0].constraints).toEqual({ concurrency: 16 });
  });
});
