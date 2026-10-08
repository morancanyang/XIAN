import { expect, test } from '@playwright/test';

/**
 * E2E 冒烟：验证九大页面区可渲染、左侧导航与命令面板可用。
 * 依赖后端启动（scripts/smoke.sh 会先拉起 API），未启动时页面走空态也不应白屏。
 */
const PAGES = [
  { path: '/dashboard', marker: '驾驶舱' },
  { path: '/agents', marker: 'Agent 资产' },
  { path: '/scenarios', marker: '靶场场景' },
  { path: '/campaigns', marker: '模式一' },
  { path: '/console', marker: '模式二' },
  { path: '/levels', marker: '十关挑战' },
  { path: '/matrix', marker: '攻击矩阵' },
  { path: '/reports', marker: '报告中心' },
  { path: '/admin', marker: '管理后台' },
  { path: '/profile', marker: '个人中心' }
];

/** 详情页路由：ID 从后端实时取，库里没有对应数据时自动跳过。 */
const DETAILS: { path: (id: string) => string; marker: string; list: string }[] = [
  { path: (id) => `/agents/${id}`, marker: 'Agent', list: '/api/v1/agents' },
  { path: (id) => `/campaigns/${id}`, marker: '战役进度', list: '/api/v1/campaigns' },
  { path: (id) => `/reports/${id}`, marker: '报告', list: '/api/v1/reports' },
  { path: (id) => `/scenarios/${id}`, marker: '场景', list: '/api/v1/scenarios' }
];

test.describe('XIAN Web 冒烟', () => {
  for (const p of PAGES) {
    test(`页面 ${p.path} 可渲染`, async ({ page }) => {
      const errors: string[] = [];
      page.on('pageerror', (err) => errors.push(err.message));
      await page.goto(p.path);
      await expect(page.locator('body')).toContainText(p.marker);
      expect(errors, `页面 ${p.path} 出现未捕获异常：${errors.join(' | ')}`).toHaveLength(0);
    });
  }

  test('左侧导航可跳转到攻击矩阵', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByRole('link', { name: /攻击矩阵/ }).click();
    await expect(page).toHaveURL(/\/matrix$/);
    await expect(page.locator('body')).toContainText('类别 × 阶段热力网格');
  });

  test('命令面板 Ctrl+K 可打开', async ({ page }) => {
    await page.goto('/dashboard');
    await page.keyboard.press('Control+k');
    await expect(page.getByText('命令面板').first()).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('详情页不白屏：Agent / 战役 / 报告 / 场景', async ({ page, request }) => {
    test.setTimeout(180_000);
    const headers = {
      'X-Tenant-Id': '00000000-0000-0000-0000-000000000001',
      'X-User-Id': '11111111-1111-1111-1111-111111111111',
      'X-Role': 'admin'
    };
    for (const d of DETAILS) {
      const res = await request.get(`http://127.0.0.1:8000${d.list}`, { headers });
      // 接口返回两种形状：直接数组，或 { items: [] } 分页封装
      const body = (await res.json()) as { items?: { id?: string; code?: string }[] } | { id?: string; code?: string }[];
      const rows: { id?: string; code?: string }[] = Array.isArray(body) ? body : (body.items ?? []);
      const first = rows[rows.length - 1];
      const id = first?.id ?? first?.code;
      test.skip(!id, `${d.list} 无数据，跳过`);

      const errors: string[] = [];
      page.on('pageerror', (err) => errors.push(err.message));
      await page.goto(d.path(id!));
      // 白屏的直接信号：整页没有任何可见文本
      await expect(page.locator('body')).not.toBeEmpty();
      await expect(page.locator('body')).toContainText(d.marker);
      expect(errors, `详情页 ${d.path(id!)} 出现未捕获异常：${errors.join(' | ')}`).toHaveLength(0);
      page.removeAllListeners('pageerror');
    }
  });

  test('登录页可切换角色并进入驾驶舱', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('body')).toContainText('XIAN');
    await expect(page.getByRole('button', { name: '登录系统' })).toBeVisible();
    await page.getByRole('button', { name: '登录', exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard(\?.*)?$/);
  });
});
