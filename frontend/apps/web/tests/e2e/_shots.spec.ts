import { test } from '@playwright/test';

const shots: [string, string][] = [
  ['/', 'home'],
  ['/login', 'login'],
  ['/campaigns', 'campaigns'],
  ['/matrix', 'matrix'],
  ['/console', 'console'],
  ['/profile', 'profile'],
  ['/reports', 'reports'],
];

test('screens', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const [path, name] of shots) {
    await page.goto(path, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `outputs/shots/${name}.png` });
    console.log('shot', name);
  }
});
