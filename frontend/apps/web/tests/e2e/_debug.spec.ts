import { test } from '@playwright/test';

test('debug campaigns requests', async ({ page }) => {
  page.on('pageerror', (e) => console.log('PAGEERROR:', e.message.slice(0, 300)));
  page.on('requestfailed', (r) => console.log('REQFAILED:', r.url().slice(0, 200)));
  page.on('response', (r) => { if (r.status() === 404) console.log('HTTP404:', r.url().slice(0, 200)); });
  await page.goto('/campaigns', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
});
