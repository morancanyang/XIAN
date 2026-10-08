import { expect, test } from '@playwright/test';

/** 逐章截图九章报告正文，并驱动第五章的 trace 回放，用于人工核对每一章内容。 */
const REPORT_ID = process.env.REPORT_ID ?? '';
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

test('九章逐章截图 + trace 回放', async ({ page, request }) => {
  test.setTimeout(240_000);
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));
  await page.goto('/login');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard(\?.*)?$/);
  let reportId = REPORT_ID;
  if (!reportId) {
    const res = await request.get('http://127.0.0.1:8000/api/v1/reports', {
      headers: {
        'X-Tenant-Id': '00000000-0000-0000-0000-000000000001',
        'X-User-Id': '11111111-1111-1111-1111-111111111111',
        'X-Role': 'admin'
      }
    });
    const rows = (await res.json()) as { id: string }[];
    test.skip(rows.length === 0, '后端暂无报告，跳过截图');
    reportId = rows[rows.length - 1].id;
  }
  await page.goto(`/reports/${reportId}`);
  await page.waitForSelector(`text=报告 ${reportId.slice(0, 12)}`);
  for (let i = 0; i < CHAPTERS.length; i += 1) {
    await page.getByRole('button', { name: new RegExp(CHAPTERS[i]) }).click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `outputs/report-ch${String(i + 1).padStart(2, '0')}.png`, fullPage: true });
  }
  await page.getByRole('button', { name: /高危详情/ }).click();
  await page.getByRole('combobox').first().click();
  await page.getByRole('option').first().click();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'outputs/report-ch05-trace.png', fullPage: true });
  expect(errors, errors.join(' | ')).toHaveLength(0);
});