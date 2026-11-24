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

await page.goto(`${BASE}/account/points`, { waitUntil: 'load' })
await page.waitForSelector('.redemption-card')
const balanceBefore = await page.locator('.points-hero strong').innerText()
await page.locator('.redemption-card').last().getByRole('button', { name: '兑换' }).click()
await page.waitForSelector('.confirm-dialog')
await page.getByRole('button', { name: '确认兑换' }).click()
await page.waitForSelector('.voucher-code', { timeout: 15000 })
const voucher = await page.locator('.voucher-code').innerText()
await page.screenshot({ path: 'artifacts/18-voucher-1440.png', fullPage: true })
await page.getByRole('button', { name: '知道了' }).click()
await page.waitForTimeout(700)
const balanceAfter = await page.locator('.points-hero strong').innerText()
console.log(JSON.stringify({ balanceBefore, balanceAfter, voucher, errors }, null, 2))
await browser.close()
