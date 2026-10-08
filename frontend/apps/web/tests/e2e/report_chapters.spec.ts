import { expect, test } from '@playwright/test';

/**
 * 报告正文回归：九章都要渲染出真实内容，且整页不能有未捕获异常。
 * （曾因 hook 顺序问题导致整页白屏，故保留此守卫。）
 */
const CHAPTERS = [
  '执行摘要',
  'Agent 画像与攻击面清单',
  '攻击路径图',
  '分类别结果',
  '高危详情',
  '根因分析与修复建议',
  '整改清单',
  '复测对比',
  '合规映射'
];

test('九章报告正文可逐章渲染', async ({ page, request }) => {
  test.setTimeout(180_000);
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));
  await page.goto('/login');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard(\?.*)?$/);
  const res = await request.get('http://127.0.0.1:8000/api/v1/reports', {
    headers: {
      'X-Tenant-Id': '00000000-0000-0000-0000-000000000001',
      'X-User-Id': '11111111-1111-1111-1111-111111111111',
      'X-Role': 'admin'
    }
  });
  const rows = (await res.json()) as { id: string }[];
  test.skip(rows.length === 0, '无报告可校验');
  const reportId = rows[rows.length - 1].id;
  await page.goto(`/reports/${reportId}`);
  await page.waitForSelector(`text=报告 ${reportId.slice(0, 12)}`);
  for (const chapter of CHAPTERS) {
    await page.getByRole('button', { name: new RegExp(chapter) }).click();
    await expect(page.locator('section').last()).toBeVisible();
  }
  // 第五章的 trace 回放要能按记录拉取
  await page.getByRole('button', { name: /高危详情/ }).click();
  await page.getByRole('combobox').first().click();
  await page.getByRole('option').first().click();
  await expect(page.getByText('裁判结论')).toBeVisible();
  expect(errors, errors.join(' | ')).toHaveLength(0);
});