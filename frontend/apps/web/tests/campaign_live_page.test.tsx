/**
 * 战役详情页整页渲染回归。
 *
 * 背景：给 DAG 传判定时在「提前 return」之后用了 useMemo，React 直接抛
 * "Rendered fewer hooks than expected"，整个页面白屏——类型检查与单测都抓不到。
 * 这里用真实页面 + mock 数据源渲染一次，把这类白屏挡在测试里。
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, test, vi } from 'vitest';
import type { ReactElement } from 'react';

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverStub;

const CAMPAIGN_ID = '430c1541-5f03-4bd4-9d67-d48e822476a0';

const CAMPAIGN = {
  id: CAMPAIGN_ID,
  tenant_id: 't',
  agent_id: '3735c399-4afc-456d-b495-3fe9ebb2f7c3',
  agent_version_id: null,
  scenario_instance_id: null,
  scope: ['XM-03', 'XM-05'],
  intensity: 'standard',
  budget: { token: 200000, cases: 60, minutes: 30 },
  constraints: {},
  judge_mode: 'standard',
  output_mode: 'summary',
  preset_id: 'standard',
  status: 'completed',
  sec_score: 94,
  grade: 'S',
  progress: 100,
  created_by: null,
  created_at: '2026-10-08T11:23:00Z',
  started_at: '2026-10-08T11:23:00Z',
  ended_at: '2026-10-08T11:24:00Z',
  plan_dag: {
    dag_nodes: [
      { id: 'XM-03', category_code: 'XM-03', stage: 'recon', case_ids: ['XM-03-001'],
        budget_split: { token: 108920, cases: 11, max_turns: 3 }, depends_on: [], weight: 1.2 },
      { id: 'XM-05', category_code: 'XM-05', stage: 'exfiltration', case_ids: ['XM-05-001'],
        budget_split: { token: 45900, cases: 13, max_turns: 3 }, depends_on: ['XM-03'], weight: 1.4 }
    ],
    edges: [['XM-03', 'XM-05']],
    budget_split: {},
    constraints: {}
  }
};

const RECORDS = {
  items: [
    { id: 'r1', tenant_id: 't', agent_id: 'a', agent_version_id: null, campaign_id: CAMPAIGN_ID,
      session_id: null, case_id: 'XM-03-001', category_code: 'XM-03', strategy: 's', mutation_ops: [],
      turns: 1, verdict: 'success', confidence: 0.9, rule_hits: [], evidence: [], tokens: 10, cost: 0,
      trace_key: '', created_at: '2026-10-08T11:23:30Z' }
  ],
  total: 1,
  page: 1,
  size: 100
};

vi.mock('../src/lib/api/hooks', () => ({
  useCampaign: () => ({ isLoading: false, isError: false, data: CAMPAIGN, refetch: vi.fn() }),
  useCampaignRecords: () => ({ data: RECORDS }),
  useRunCampaign: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useCreateCampaignReport: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useCampaignPlan: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useMatrixCategories: () => ({
    data: [
      { id: 'c1', code: 'XM-03', name: '提示词注入', stage: '侦察', attack_surface: '提示词层',
        difficulty: 'medium', impact: 'high', techniques: [], detection_signals: [], owasp_ref: [], atlas_ref: [] },
      { id: 'c2', code: 'XM-05', name: '敏感数据外泄', stage: '数据渗出', attack_surface: '数据层/工具层',
        difficulty: 'medium', impact: 'critical', techniques: [], detection_signals: [], owasp_ref: [], atlas_ref: [] }
    ]
  })
}));

vi.mock('../src/lib/ws/useCampaignStream', () => ({ useCampaignStream: () => undefined }));
// WebGL 背景在 jsdom 里没有 GL 上下文，替换成空div
vi.mock('../src/features/campaign/components/RadarBackdrop', () => ({ RadarBackdrop: () => <div /> }));
vi.mock('../src/components/layout/ToastHost', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), dismiss: vi.fn() })
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/campaigns/${CAMPAIGN_ID}`]}>
        <Routes>
          <Route path="/campaigns/:campaignId" element={<LazyPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

let LazyPage: () => ReactElement;

afterEach(() => {
  vi.clearAllMocks();
});

describe('CampaignLivePage', () => {
  test('整页可渲染：进度/SecScore 显示真实值，DAG 有类别名', async () => {
    LazyPage = (await import('../src/pages/mode1/CampaignLivePage')).default;
    const errors: string[] = [];
    const spy = vi.spyOn(console, 'error').mockImplementation((...args) => errors.push(String(args[0])));
    try {
      renderPage();
    } finally {
      spy.mockRestore();
    }
    expect(errors, `渲染报错：${errors.join(' | ')}`).toHaveLength(0);

    expect(screen.getByText('战役进度')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText('100', { selector: 'span.font-mono' })).toBeInTheDocument()
    );
    expect(screen.getByText('SecScore S')).toBeInTheDocument();
    expect(screen.getByText('94', { selector: 'span.font-mono' })).toBeInTheDocument();
    expect(screen.getByText('提示词注入')).toBeInTheDocument();
    expect(screen.getByText('敏感数据外泄')).toBeInTheDocument();
    expect(screen.getByText('DAG 计划')).toBeInTheDocument();
  });
});
