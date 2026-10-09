import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 180000,
  expect: { timeout: 30000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:8080',
    headless: true,
    launchOptions: {
      args: [
        '--use-gl=swiftshader',
        '--enable-unsafe-swiftshader',
        '--ignore-gpu-blocklist',
        '--no-sandbox',
        '--disable-dev-shm-usage',
      ],
    },
  },
  webServer: {
    command: 'cd /workspace/backend && ./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8080',
    url: 'http://127.0.0.1:8080/api/health',
    reuseExistingServer: true,
    timeout: 90000,
  },
})
