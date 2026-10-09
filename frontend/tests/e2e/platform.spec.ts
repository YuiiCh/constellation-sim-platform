import { test, expect, request } from '@playwright/test'

const SMALL_SIM = {
  name: 'e2e-smoke',
  constellation_id: 'qianfan',
  rule_type: 'simple_elevation',
  duration_h: 1,
  sample_interval_s: 300,
  region: [31.0, 114.0, 36.0, 120.0],
  h3_res: 4,
  selected_shell_ids: [],
}

const BASE = 'http://127.0.0.1:8080'

async function createAndWait() {
  const ctx = await request.newContext()
  const post = await ctx.post(`${BASE}/api/simulations`, {
    data: SMALL_SIM,
    headers: { 'Content-Type': 'application/json' },
  })
  expect(post.ok()).toBeTruthy()
  const task = await post.json()
  const id = task.id
  // 轮询直至完成
  for (let i = 0; i < 60; i++) {
    const r = await ctx.get(`${BASE}/api/simulations/${id}`)
    const t = await r.json()
    if (t.status === 'succeeded' || t.status === 'failed') return id
    await new Promise((res) => setTimeout(res, 1000))
  }
  return id
}

test.describe('星座仿真平台 端到端', () => {
  test('1) 页面加载与地球渲染', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (e) => errors.push(e.message))
    await page.goto('/')
    await expect(page.locator('.header .title')).toBeVisible()
    // Cesium canvas 存在
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 30000 })
    // 星座下拉存在且有选项
    const opts = page.locator('.cons-select option')
    await expect(opts.first()).toBeVisible()
    expect(await opts.count()).toBeGreaterThan(0)
  })

  test('2) 星座切换与壳层筛选', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('.cons-select')
    const sel = page.locator('.cons-select')
    const before = await sel.inputValue()
    // 切换到第二个星座
    const opts = page.locator('.cons-select option')
    const count = await opts.count()
    if (count > 1) {
      await sel.selectOption({ index: 1 })
      await page.waitForTimeout(800)
      const after = await sel.inputValue()
      expect(after).not.toBe(before)
    }
    // 壳层筛选：取消勾选一个稳定壳层，卫星数应变化
    const firstCb = page.locator('.info .shell input[type=checkbox]').first()
    const satBefore = await page.locator('.info .tag.ok').first().innerText()
    await firstCb.uncheck()
    await page.waitForTimeout(800)
    const satAfter = await page.locator('.info .tag.ok').first().innerText()
    expect(satAfter).not.toBe(satBefore)
    // 恢复：重新勾选
    await firstCb.check()
  })

  test('3) 时间轴实时按钮逻辑', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('.timeaxis')
    const rt = page.locator('.timeaxis .realtime')
    await expect(rt).toHaveClass(/active/)
    // 修改时间输入，实时应变灰
    const timeInput = page.locator('.timeaxis input[type=time]')
    await timeInput.fill('03:14:00')
    await timeInput.dispatchEvent('change')
    await page.waitForTimeout(300)
    await expect(rt).not.toHaveClass(/active/)
    // 点击实时恢复
    await rt.click()
    await page.waitForTimeout(300)
    await expect(rt).toHaveClass(/active/)
  })

  test('4) 创建覆盖仿真并查看结果', async ({ page }) => {
    const id = await createAndWait()
    await page.goto('/')
    // 等待任务栏出现该任务（周期刷新 3s）
    await page.waitForTimeout(4000)
    const taskCard = page.locator(`.taskbar .task:has-text("#${id}")`)
    await expect(taskCard).toBeVisible()
    // 点击查看结果
    await taskCard.locator('button:has-text("查看结果")').click()
    // 覆盖结果面板出现，含 ECharts canvas 与统计
    await expect(page.locator('.coverage')).toBeVisible()
    await expect(page.locator('.coverage .chart canvas')).toBeVisible({ timeout: 20000 })
    await expect(page.locator('.coverage .stats')).toContainText('网格数')
  })

  test('5) 任务删除与历史可视化', async ({ page }) => {
    const id = await createAndWait()
    await page.goto('/')
    await page.waitForTimeout(4000)
    const taskCard = page.locator(`.taskbar .task:has-text("#${id}")`)
    await expect(taskCard).toBeVisible()
    // 删除
    await taskCard.locator('button:has-text("删除")').click()
    await page.waitForTimeout(3500)
    await expect(page.locator(`.taskbar .task:has-text("#${id}")`)).toHaveCount(0)
  })
})
