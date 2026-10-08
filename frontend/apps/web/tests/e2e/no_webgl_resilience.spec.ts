import { expect, test } from '@playwright/test';

/**
 * 背景组件降级与错误边界的端到端回归。
 *
 * 背景故障目录：部分内嵌 WebView（APP 容器、部分远程桌面）拿不到 WebGL 上下文，
 * ogl 的 Renderer 会抛 "unable to create webgl context"。当时整个应用没有错误边界，
 * 异常把整棵组件树卸载，侧边栏、顶栏、导航全部消失，用户看到的就是整页白屏。
 * 这里用 addInitScript 把 getContext 扇出 null，上线后页面必须仍然完整可用。
 */
const API = 'http://127.0.0.1:8000/api/v1';
const HEADERS = {
  'X-Tenant-Id': '00000000-0000-0000-0000-000000000001',
  'X-User-Id': '11111111-1111-1111-1111-111111111111',
  'X-Role': 'admin'
};

/** 把所有 WebGL 上下文挖空，模拟不支持 WebGL 的环境。 */
async function disableWebGL(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function patched(this: HTMLCanvasElement, kind: string, ...rest: unknown[]) {
      if (String(kind).includes('webgl')) return null;
      return (original as (...args: unknown[]) => unknown).call(this, kind, ...rest);
    } as typeof HTMLCanvasElement.prototype.getContext;
  });
}

test('无 WebGL 环境下战役详情页不白屏', async ({ page, request }) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));
  await disableWebGL(page);

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
  // 白屏故障的具体表现：侧边栏导航随整棵树一起消失
  const sidebar = page.locator('aside');
  await expect(sidebar.locator('a[href="/dashboard"]')).toBeVisible();
  await expect(sidebar.locator('a[href="/campaigns"]')).toBeVisible();
  await expect(sidebar.locator('a[href="/matrix"]')).toBeVisible();
  await expect(page.locator('body')).not.toBeEmpty();

  expect(errors, `无 WebGL 环境下出现未捕获异常：${errors.join(' | ')}`).toHaveLength(0);
});
