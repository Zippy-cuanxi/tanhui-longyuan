import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const BASE = process.env.SMOKE_BASE || 'http://127.0.0.1:5173'
const ARTIFACTS = path.resolve('artifacts')

const report = {
  base: BASE,
  consoleErrors: [],
  pageErrors: [],
  failedRequests: [],
  httpErrors: [],
  checks: {},
  screenshots: []
}

function recordCheck(name, value) {
  report.checks[name] = value
}

async function waitForServer() {
  for (let i = 0; i < 80; i += 1) {
    try {
      const response = await fetch(BASE, { signal: AbortSignal.timeout(1500) })
      if (response.ok) return
    } catch {
      // retry
    }
    await new Promise((resolve) => setTimeout(resolve, 400))
  }
  throw new Error(`dev server not reachable: ${BASE}`)
}

async function shot(page, name) {
  const file = path.join(ARTIFACTS, `${name}.png`)
  await page.screenshot({ path: file, fullPage: true })
  report.screenshots.push(file)
}

await mkdir(ARTIFACTS, { recursive: true })
await waitForServer()

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await context.newPage()

page.on('console', (message) => {
  if (message.type() === 'error') report.consoleErrors.push(message.text())
})
page.on('pageerror', (error) => report.pageErrors.push(error.message))
page.on('requestfailed', (request) => {
  const url = request.url()
  if (url.includes('/api/') || url.includes('/uploads/')) {
    report.failedRequests.push(
      `${request.method()} ${url} :: ${request.failure()?.errorText || ''}`
    )
  }
})
page.on('response', (response) => {
  const url = response.url()
  if (response.status() >= 400 && (url.includes('/api/') || url.includes('/uploads/'))) {
    report.httpErrors.push(`${response.status()} ${url}`)
  }
})

try {
  // ---------- 首页 ----------
  await page.goto(`${BASE}/`, { waitUntil: 'load' })
  await page.waitForSelector('.product-card', { timeout: 15000 })
  await page.waitForTimeout(600)
  recordCheck('homeTitle', await page.title())
  recordCheck(
    'homeHeroLoaded',
    await page
      .locator('.banner-home img')
      .first()
      .evaluate((img) => img.complete && img.naturalWidth > 0)
  )
  recordCheck('homeQuickCategories', await page.locator('.quick-category').count())
  recordCheck('homeProductCards', await page.locator('.product-card').count())
  recordCheck('homeFirstProduct', await page.locator('.product-card h3').first().innerText())
  recordCheck(
    'homeFirstPrice',
    await page.locator('.product-card .product-price').first().innerText()
  )
  const homeOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth
  )
  recordCheck('homeOverflow1440', homeOverflow)
  await shot(page, '01-home-1440')

  // ---------- 全部商品 ----------
  await page.goto(`${BASE}/products`, { waitUntil: 'load' })
  await page.waitForSelector('.product-card', { timeout: 15000 })
  await page.waitForTimeout(400)
  recordCheck('catalogCards', await page.locator('.product-card').count())
  recordCheck('catalogCategories', await page.locator('.category-sidebar button').count())
  recordCheck('catalogPagination', await page.locator('.pagination button').count())
  await shot(page, '02-catalog-1440')

  // ---------- 商品详情 ----------
  await page.locator('.product-card').first().click()
  await page.waitForSelector('.detail-title-row h1', { timeout: 15000 })
  await page.waitForTimeout(500)
  recordCheck('detailTitle', await page.locator('.detail-title-row h1').innerText())
  recordCheck('detailPrice', await page.locator('.detail-price').innerText())
  recordCheck('detailThumbs', await page.locator('.thumbnail-list button').count())
  recordCheck('detailSkuOptions', await page.locator('.sku-options button').count())
  recordCheck('detailRelated', await page.locator('.related-item').count())
  recordCheck('detailGreenTab', await page.getByRole('tab', { name: '绿色资料' }).count())
  await shot(page, '03-detail-1440')

  // ---------- 登录 ----------
  await page.goto(`${BASE}/login`, { waitUntil: 'load' })
  await page.getByRole('button', { name: '填入演示账号' }).click()
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 15000 })
  recordCheck('loginRedirect', new URL(page.url()).pathname)
  await page.waitForTimeout(500)

  // ---------- 加购 ----------
  await page.goto(`${BASE}/products`, { waitUntil: 'load' })
  await page.waitForSelector('.product-card', { timeout: 15000 })
  await page.locator('.product-card').first().click()
  await page.waitForSelector('.detail-actions', { timeout: 15000 })
  await page.getByRole('button', { name: /加入购物车/ }).click()
  await page.waitForSelector('.toast', { timeout: 15000 })
  recordCheck('addToCartToast', await page.locator('.toast').innerText())
  await page.goto(`${BASE}/cart`, { waitUntil: 'load' })
  await page.waitForSelector('.cart-item', { timeout: 15000 })
  recordCheck('cartItems', await page.locator('.cart-item').count())
  recordCheck('cartSubtotal', await page.locator('.cart-summary dd').nth(1).innerText())
  await shot(page, '04-cart-1440')

  // ---------- 结算 ----------
  await page.getByRole('button', { name: /去结算/ }).click()
  await page.waitForURL('**/checkout', { timeout: 15000 })
  await page.waitForSelector('.checkout-summary .total-row dd', { timeout: 15000 })
  await page.waitForTimeout(700)
  recordCheck(
    'checkoutPayAmount',
    await page.locator('.checkout-summary .total-row dd').innerText()
  )
  recordCheck('checkoutStores', await page.locator('.checkout-store').count())
  await shot(page, '05-checkout-1440')

  // ---------- 提交订单 ----------
  await page.getByRole('button', { name: /提交订单/ }).click()
  await page.waitForURL('**/pay/**', { timeout: 20000 })
  await page.waitForSelector('.payment-card', { timeout: 15000 })
  await page.waitForTimeout(400)
  recordCheck('paymentAmount', await page.locator('.payment-amount strong').innerText())
  recordCheck('paymentSandbox', await page.locator('.sandbox-badge').innerText())
  await shot(page, '06-payment-1440')

  // ---------- 沙箱支付 ----------
  await page.getByRole('button', { name: /沙箱支付/ }).click()
  await page.waitForSelector('.payment-result.success', { timeout: 20000 })
  recordCheck('paymentSuccessTitle', await page.locator('.payment-result h1').innerText())
  await shot(page, '07-payment-success-1440')

  // ---------- 订单 / 积分 ----------
  await page.goto(`${BASE}/account/orders`, { waitUntil: 'load' })
  await page.waitForSelector('.order-card', { timeout: 15000 })
  recordCheck('accountOrders', await page.locator('.order-card').count())
  await shot(page, '08-orders-1440')

  await page.goto(`${BASE}/account/points`, { waitUntil: 'load' })
  await page.waitForSelector('.points-hero', { timeout: 15000 })
  await page.waitForTimeout(600)
  recordCheck('pointsBalance', await page.locator('.points-hero strong').innerText())
  recordCheck('pointTransactions', await page.locator('.transaction-list li').count())
  await shot(page, '09-points-1440')

  await page.goto(`${BASE}/account`, { waitUntil: 'load' })
  await page.waitForSelector('.account-welcome', { timeout: 15000 })
  await page.waitForTimeout(600)
  await shot(page, '10-account-1440')

  // ---------- 其他页面 ----------
  for (const [pathName, name, selector] of [
    ['/origin', '11-origin-1440', '.region-chips'],
    ['/aid', '12-aid-1440', '.aid-grid'],
    ['/green', '13-green-1440', '.green-product-grid'],
    ['/brand', '14-brand-1440', '.brand-story-grid'],
    ['/help', '15-help-1440', '.help-grid']
  ]) {
    await page.goto(`${BASE}${pathName}`, { waitUntil: 'load' })
    await page.waitForSelector(selector, { timeout: 15000 })
    await page.waitForTimeout(350)
    await shot(page, name)
  }

  // ---------- 移动端 ----------
  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true })
  const mobilePage = await mobile.newPage()
  const mobileErrors = []
  mobilePage.on('pageerror', (error) => mobileErrors.push(error.message))
  await mobilePage.goto(`${BASE}/`, { waitUntil: 'load' })
  await mobilePage.waitForSelector('.product-card', { timeout: 15000 })
  await mobilePage.waitForTimeout(600)
  recordCheck(
    'mobileOverflow',
    await mobilePage.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  )
  recordCheck('mobileProductCards', await mobilePage.locator('.product-card').count())
  await mobilePage.screenshot({ path: path.join(ARTIFACTS, '16-home-390.png'), fullPage: true })
  report.screenshots.push(path.join(ARTIFACTS, '16-home-390.png'))
  report.checks.mobilePageErrors = mobileErrors
  await mobile.close()
} catch (error) {
  report.fatal = error instanceof Error ? error.stack || error.message : String(error)
  try {
    await page.screenshot({ path: path.join(ARTIFACTS, '99-failure.png'), fullPage: true })
    report.screenshots.push(path.join(ARTIFACTS, '99-failure.png'))
  } catch {
    // ignore
  }
} finally {
  await browser.close()
}

console.log(JSON.stringify(report, null, 2))
