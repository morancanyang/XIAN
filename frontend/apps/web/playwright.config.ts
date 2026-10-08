import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  /* manual/ 下是人工核对用的截图与探针脚本，不进常规 e2e 跑测 */
  testIgnore: '**/manual/**',
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173',
    /* 本机未下载 Playwright 自带浏览器时可用系统 Chrome：E2E_CHANNEL=chrome */
    channel: process.env.E2E_CHANNEL || undefined,
    trace: 'off',
    screenshot: 'off',
    video: 'off'
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }]
});
