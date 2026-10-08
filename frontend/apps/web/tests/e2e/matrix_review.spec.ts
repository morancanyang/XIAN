import { expect, test } from '@playwright/test';

/**
 * 用例评审流水线回归（PRD 3.5.5.8.1）。
 *
 * 后端 /matrix/cases/{id}/review 一直存在，但前端此前从未接线，等于死接口。
 * 库内种子用例全部是 published 终态，因此分两条用例覆盖：
 *   1. 终态用例只读展示（真实数据）；
 *   2. 非终态用例可逐级推进、驳回后阻断（拦截接口注入 submitted 用例）。
 */
const SUBMITTED_CASE = {
  id: 'XM-TEST-001',
  category_id: 'XM-01',
  title: '流水线推进验证用例',
  payload_template: 'ignore previous instructions',
  variables: [],
  scenario_tags: ['test'],
  difficulty: 'medium',
  severity: 'high',
  success_criteria: {},
  judge_prompt: '',
  success_rate: 0,
  status: 'submitted',
  version: 1,
  contributor: 'e2e'
};

/**
 * 拦截用例列表与评审接口：列表返回注入用例，评审按真实状态机演算。
 * 其余 matrix 接口全部放行，避免把 categories / coverage 一起 mock 掉。
 */
async function mockCases(page: import('@playwright/test').Page, status: string) {
  const order = ['submitted', 'auto_test', 'review', 'published'];
  await page.route('**/api/v1/matrix/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    const isList = path === '/api/v1/matrix/cases';
    const isReview = path.endsWith('/review');
    if (isList) {
      await route.fulfill({ json: [{ ...SUBMITTED_CASE, status }] });
      return;
    }
    if (isReview) {
      const body = route.request().postDataJSON() as { status?: string; passed?: boolean };
      const current = body.status ?? 'submitted';
      const next = body.passed ? order[Math.min(order.indexOf(current) + 1, order.length - 1)] : 'rejected';
      await route.fulfill({ json: { case_id: SUBMITTED_CASE.id, status: next } });
      return;
    }
    await route.fallback();
  });
}

test('用例详情展示评审流水线，终态用例只读', async ({ page }) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));

  await page.goto('/login');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard(\?.*)?$/);

  await page.goto('/matrix');
  await expect(page.locator('body')).toContainText('用例清单');

  await page.getByRole('button', { name: '详情' }).first().click();
  const dialog = page.locator('[role="dialog"]');
  await expect(dialog).toBeVisible();

  for (const step of ['已提交', '自动测试', '双人评审', '已上线']) {
    await expect(dialog).toContainText(step);
  }
  await expect(dialog).toContainText('该用例已上线，无需继续评审。');
  await expect(dialog.getByRole('button', { name: '通过并推进' })).toHaveCount(0);
  await expect(dialog.getByRole('button', { name: '驳回' })).toHaveCount(0);

  expect(errors, `矩阵页出现未捕获异常：${errors.join(' | ')}`).toHaveLength(0);
});

test('非终态用例可逐级推进，驳回后阻断', async ({ page }) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));

  await mockCases(page, 'submitted');

  await page.goto('/login');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard(\?.*)?$/);

  await page.goto('/matrix');
  await expect(page.locator('body')).toContainText('流水线推进验证用例');
  await page.getByRole('button', { name: '详情' }).first().click();

  const dialog = page.locator('[role="dialog"]');
  const advance = dialog.getByRole('button', { name: '通过并推进' });
  await expect(advance).toBeVisible();

  // submitted → auto_test → review → published
  for (const next of ['自动测试', '双人评审', '已上线']) {
    await advance.click();
    // toast 会同时出现在可视通知和无障碍幢迹节点，取第一个
    await expect(page.getByText(`已推进到「${next}」`).first()).toBeVisible();
  }
  await expect(dialog).toContainText('该用例已上线，无需继续评审。');
  await expect(dialog.getByRole('button', { name: '通过并推进' })).toHaveCount(0);

  expect(errors, `矩阵页出现未捕获异常：${errors.join(' | ')}`).toHaveLength(0);
});

test('非终态用例可被驳回，驳回后不再推进', async ({ page }) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));

  await mockCases(page, 'review');

  await page.goto('/login');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard(\?.*)?$/);

  await page.goto('/matrix');
  await page.getByRole('button', { name: '详情' }).first().click();

  const dialog = page.locator('[role="dialog"]');
  await dialog.getByRole('button', { name: '驳回' }).click();
  await expect(dialog).toContainText('该用例已被驳回，不再推进。');
  await expect(dialog.getByRole('button', { name: '通过并推进' })).toHaveCount(0);
  await expect(dialog.getByRole('button', { name: '驳回' })).toHaveCount(0);

  expect(errors, `矩阵页出现未捕获异常：${errors.join(' | ')}`).toHaveLength(0);
});
