// React Flow 在 jsdom 里需要 ResizeObserver，补一个最小桩
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverStub;

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';
import type { ReactElement } from 'react';
import { MetricRing } from '@xian/ui';
import type { CampaignPlan } from '@xian/types';

const CATEGORIES = [
  { id: 'c1', code: 'XM-03', name: '提示词注入', stage: '侦察', attack_surface: '提示词层',
    difficulty: 'medium', impact: 'high', techniques: [], detection_signals: [], owasp_ref: [], atlas_ref: [] },
  { id: 'c2', code: 'XM-05', name: '敏感数据外泄', stage: '数据渗出', attack_surface: '数据层/工具层',
    difficulty: 'medium', impact: 'critical', techniques: [], detection_signals: [], owasp_ref: [], atlas_ref: [] }
];

/** 与后端 build_plan 输出完全一致的 plan_dag 形状。 */
const PLAN = {
  dag_nodes: [
    { id: 'XM-03', category_code: 'XM-03', stage: 'recon', case_ids: ['XM-03-001', 'XM-03-002'],
      budget_split: { token: 108920, cases: 11, max_turns: 3 }, depends_on: [], weight: 1.2 },
    { id: 'XM-05', category_code: 'XM-05', stage: 'exfiltration', case_ids: ['XM-05-001'],
      budget_split: { token: 45900, cases: 13, max_turns: 3 }, depends_on: ['XM-03'], weight: 1.4 }
  ],
  edges: [['XM-03', 'XM-05']],
  budget_split: {},
  constraints: { max_turns: 3 }
} as unknown as CampaignPlan;

function renderWithQuery(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('MetricRing', () => {
  test('显示传入的真实数值，而不是恒定 0', async () => {
    renderWithQuery(<MetricRing value={100} label="战役进度" />);
    await waitFor(() => expect(screen.getByText('100')).toBeInTheDocument());
    expect(screen.getByText('战役进度')).toBeInTheDocument();
  });

  test('SecScore 与等级一起显示', async () => {
    renderWithQuery(<MetricRing value={95} label="SecScore S" tone="success" />);
    await waitFor(() => expect(screen.getByText('95')).toBeInTheDocument());
    expect(screen.getByText('SecScore S')).toBeInTheDocument();
  });
});

describe('PlanPreview', () => {
  test('按后端契约渲染类别名、阶段与预算，节点不是空白卡片', async () => {
    vi.mock('../src/lib/api/hooks', () => ({ useMatrixCategories: () => ({ data: CATEGORIES }) }));
    const { PlanPreview } = await import('../src/features/campaign/components/PlanPreview');
    renderWithQuery(<PlanPreview plan={PLAN} verdicts={{ 'XM-05': 'success' }} />);

    await waitFor(() => expect(screen.getByText('提示词注入')).toBeInTheDocument());
    expect(screen.getByText('敏感数据外泄')).toBeInTheDocument();
    expect(screen.getByText('2 例 · 109k token')).toBeInTheDocument();
    expect(screen.getByText('1 例 · 46k token')).toBeInTheDocument();
    expect(screen.getByText('命中')).toBeInTheDocument();
    expect(screen.getByText(/kill chain 阶段/)).toBeInTheDocument();
  });

  test('没有计划时给空态而不是崩', async () => {
    const { PlanPreview } = await import('../src/features/campaign/components/PlanPreview');
    renderWithQuery(<PlanPreview plan={null} />);
    expect(screen.getByText('暂无战役计划')).toBeInTheDocument();
  });
});
