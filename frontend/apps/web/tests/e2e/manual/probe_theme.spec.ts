import { test } from '@playwright/test';

test('probe theme', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  const info = await page.evaluate(() => {
    const html = document.documentElement;
    const cs = getComputedStyle(html);
    const body = getComputedStyle(document.body);
    return {
      dataTheme: html.getAttribute('data-theme'),
      bgBase: cs.getPropertyValue('--bg-base').trim(),
      bgElevated: cs.getPropertyValue('--bg-elevated').trim(),
      bodyBg: body.backgroundColor,
      mainBg: getComputedStyle(document.querySelector('main') ?? document.body).backgroundColor,
      bodyClass: document.body.className
    };
  });
  console.log(JSON.stringify(info, null, 2));
});
