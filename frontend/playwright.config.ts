import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './e2e', expect: { timeout: 20000 }, use: { headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined, screenshot: 'only-on-failure' }, timeout: 60000, reporter: [['junit', { outputFile: '../reports/browser.xml' }], ['list'], ['html', { open: 'never' }]] });
