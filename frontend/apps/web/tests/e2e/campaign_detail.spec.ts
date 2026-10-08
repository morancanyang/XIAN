import { expect, test } from '@playwright/test';

/**
 * 战役详情页端到端回归。
 *
 * 这条用例直接对准一次线上事故：给 DAG 传判定汇总时把 useMemo 放在了
 * 「加载中 / 加载失败 / 战役不存在」三个提前 return 之后，状态从 loading
 * 变成 loaded 时 React 抛 "Rendered fewer hooks than expected"，整页白屏。
 * typecheck 与单元测试都抓不到，只有真实浏览器里打开页面才会暴露，
 * 所以这里用 pageerror 断言把它钉死。
 */
const API = 'http://127.0.0.1:8000/api/v1';
const HEADERS = {
  'X-Tenant-Id': '00000000-0000-0000-0000-000000000001',
  'X-User-Id': '11111111-1111-1111-1111-111111111111',
  'X-Role': 'admin'
};

test('战役详情页可渲染，进度环与 DAG 有真实内容', async ({ page, request }) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));

  await page.goto('/login');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard(\?.*)?$/);

  const res = await request.get(`${API}/campaigns`, { headers: HEADERS });
  const rows = (await res.json()) as { id: string }[];
  test.skip(rows.length === 0, '无战役可校验');
  const campaignId = rows[rows.length - 1].id;

  await page.goto(`/campaigns/${campaignId}`);
  await expect(page.locator('body')).toContainText('战役进度');
  await expect(page.locator('body')).toContainText('DAG 计划');
  await expect(page.locator('body')).toContainText('SecScore');
  // 白屏事故的直接信号：整页没有任何可见内容
  await expect(page.locator('body')).not.toBeEmpty();

  expect(errors, `战役详情页出现未捕获异常：${errors.join(' | ')}`).toHaveLength(0);
});
