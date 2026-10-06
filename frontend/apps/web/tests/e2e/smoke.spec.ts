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

  test('登录页可切换角色并进入驾驶舱', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('body')).toContainText('XIAN');
    await expect(page.getByRole('button', { name: '登录系统' })).toBeVisible();
    await page.getByRole('button', { name: '登录', exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard(\?.*)?$/);
  });
});
