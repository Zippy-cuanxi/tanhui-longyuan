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

await page.goto(`${BASE}/products/4d21cb04-7cbc-491c-9376-f0e67b6c030b`, { waitUntil: 'load' })
await page.waitForSelector('.detail-actions')
await page.getByRole('button', { name: /立即购买/ }).click()
await page.waitForURL('**/checkout')
await page.waitForSelector('.checkout-store li', { timeout: 15000 })
const items = await page.locator('.checkout-store li').count()
const amount = await page.locator('.checkout-summary .total-row dd').innerText()
const directNote = await page.locator('.page-heading p').innerText()
console.log(JSON.stringify({ items, amount, directNote, errors }, null, 2))
await browser.close()
