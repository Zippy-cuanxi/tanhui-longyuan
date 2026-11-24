import { chromium } from 'playwright'

const BASE = process.env.SMOKE_BASE || 'http://127.0.0.1:5173'
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await context.newPage()
const errors = []
page.on('pageerror', (error) => errors.push(error.message))
page.on('console', (message) => {
  if (message.type() === 'error') errors.push(message.text())
})

await page.goto(`${BASE}/login`, { waitUntil: 'load' })
await page.getByRole('button', { name: '填入演示账号' }).click()
await page.getByRole('button', { name: '登录', exact: true }).click()
await page.waitForURL((url) => !url.pathname.startsWith('/login'))

await page.goto(`${BASE}/account/orders?status=paid`, { waitUntil: 'load' })
await page.waitForSelector('.order-card')
await page.getByRole('button', { name: '申请退款' }).first().click()
await page.waitForURL('**/refund')
await page.waitForSelector('.refund-form', { timeout: 15000 })
const refundable = await page.locator('.refundable').first().innerText()
await page.locator('textarea[placeholder^="如："]').fill('演示：商品与描述不符，申请退款测试')
await page.getByRole('button', { name: '提交退款申请' }).click()
await page.waitForSelector('.refund-success', { timeout: 20000 })
const success = await page.locator('.refund-success').innerText()
const recordCount = await page.locator('.refund-list li').count()
await page.screenshot({ path: 'artifacts/17-refund-1440.png', fullPage: true })
console.log(JSON.stringify({ refundable, success, recordCount, errors }, null, 2))
await browser.close()
