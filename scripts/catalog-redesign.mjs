import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const BASE = process.env.SMOKE_BASE || 'http://127.0.0.1:5174'
const API = process.env.API_BASE || 'http://127.0.0.1:8000/api/v1'
const ARTIFACTS = path.resolve('artifacts')

const report = {
  base: BASE,
  checks: {},
  consoleErrors: [],
  pageErrors: [],
  failedRequests: [],
  screenshots: []
}

function check(name, value) {
  report.checks[name] = value
}

async function shot(page, name, fullPage = true) {
  const file = path.join(ARTIFACTS, `${name}.png`)
  await page.screenshot({ path: file, fullPage })
  report.screenshots.push(file)
  return file
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

async function overflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
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
  if (url.includes('/api/') || url.includes('/uploads/') || url.includes('/images/')) {
    report.failedRequests.push(`${request.method()} ${url} :: ${request.failure()?.errorText || ''}`)
  }
})

try {
  // ---------- 1440 全部商品 ----------
  await page.goto(`${BASE}/products`, { waitUntil: 'load' })
  await page.waitForSelector('.catalog-category-pill', { timeout: 15000 })
  await page.waitForSelector('.product-card', { timeout: 15000 })
  await page.waitForTimeout(1200)

  const panel1440 = await page.locator('.catalog-category-panel').evaluate((el) => {
    const style = getComputedStyle(el)
    return {
      columns: style.gridTemplateColumns.split(' ').filter(Boolean).length,
      width: el.getBoundingClientRect().width
    }
  })
  check('panel1440Columns', panel1440.columns)
  check('categoryPills', await page.locator('.catalog-category-pill').count())
  check('linearIcons', await page.locator('.catalog-category-pill img').count())
  check('categoryCardVisible', await page.locator('.catalog-category-card').isVisible())
  check(
    'categoryCardImageLoaded',
    await page.locator('.catalog-category-card img').evaluate((img) => img.complete && img.naturalWidth > 0)
  )
  check('originItems', await page.locator('.origin-item').count())
  check('productCards', await page.locator('.product-card').count())
  check('dishTaggedCards', await page.locator('.product-dish-tag').count())
  check('dishImagesLoaded', await page.locator('.product-card.catalog .product-image').first().evaluate((img) => img.complete && img.naturalWidth > 0))
  check('mockReviewBadge', await page.locator('.featured-reviews .mock-badge').innerText())
  check(
    'mockReviewNote',
    await page.locator('.featured-reviews-head p').innerText()
  )
  check('overflow1440', await overflow(page))
  await shot(page, 'catalog-v2-1440')

  // 分类切换
  const grainButton = page.locator('.catalog-category-pill').filter({ hasText: '粮油杂粮' })
  await grainButton.click()
  await page.waitForURL(/category_id=/, { timeout: 10000 })
  await page.waitForTimeout(900)
  check('categoryFilterCards', await page.locator('.product-card').count())
  check('categoryFilterActive', await grainButton.getAttribute('aria-pressed'))
  check('categoryFilterOriginItems', await page.locator('.origin-item').count())
  await shot(page, 'catalog-v2-category-1440')

  // 再次点击取消筛选
  await grainButton.click()
  await page.waitForURL((url) => !url.search.includes('category_id'), { timeout: 10000 })
  await page.waitForTimeout(700)
  check('categoryClearCards', await page.locator('.product-card').count())

  // 价格排序
  await page.getByRole('button', { name: '价格优先' }).click()
  await page.waitForURL(/sort=price_asc/, { timeout: 10000 })
  await page.waitForTimeout(700)
  check('priceSortFirst', await page.locator('.product-card h3').first().innerText())

  // ---------- 768 ----------
  await page.setViewportSize({ width: 768, height: 1024 })
  await page.goto(`${BASE}/products`, { waitUntil: 'load' })
  await page.waitForSelector('.product-card', { timeout: 15000 })
  await page.waitForTimeout(900)
  const panel768 = await page.locator('.catalog-category-panel').evaluate((el) => {
    const style = getComputedStyle(el)
    return style.gridTemplateColumns.split(' ').filter(Boolean).length
  })
  check('panel768Columns', panel768)
  check('overflow768', await overflow(page))
  check('originItems768', await page.locator('.origin-item').count())
  check('productCards768', await page.locator('.product-card').count())
  await shot(page, 'catalog-v2-768')

  // ---------- 390 ----------
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`${BASE}/products`, { waitUntil: 'load' })
  await page.waitForSelector('.product-card', { timeout: 15000 })
  await page.waitForTimeout(900)
  check('overflow390', await overflow(page))
  check('categoryPills390', await page.locator('.catalog-category-pill').count())
  check('originItems390', await page.locator('.origin-item').count())
  check('productCards390', await page.locator('.product-card').count())
  check('categoryCard390Visible', await page.locator('.catalog-category-card').isVisible())
  await shot(page, 'catalog-v2-390')

  // ---------- 详情吃法模块 ----------
  const productResponse = await fetch(`${API}/products?page=1&page_size=20`)
  const productPayload = await productResponse.json()
  const lily = productPayload.data.items.find((item) => item.title.includes('百合'))
  check('lilyId', lily?.id || null)
  if (lily) {
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto(`${BASE}/products/${lily.id}`, { waitUntil: 'load' })
    await page.waitForSelector('.recipe-section', { timeout: 15000 })
    await page.waitForTimeout(700)
    check('recipeTitle', await page.locator('.recipe-copy h3').innerText())
    check(
      'recipeImageLoaded',
      await page.locator('.recipe-image img').evaluate((img) => img.complete && img.naturalWidth > 0)
    )
    await page.locator('.recipe-section').screenshot({ path: path.join(ARTIFACTS, 'catalog-v2-recipe.png') })
    report.screenshots.push(path.join(ARTIFACTS, 'catalog-v2-recipe.png'))
  }

  // ---------- 首页素材路径 ----------
  await page.goto(`${BASE}/`, { waitUntil: 'load' })
  await page.waitForSelector('.quick-category', { timeout: 15000 })
  const quickIcons = await page.locator('.quick-category img').evaluateAll((images) =>
    images.map((img) => img.getAttribute('src'))
  )
  check('homeQuickIcons', quickIcons)
  check('homeLogo', await page.locator('.brand img').getAttribute('src'))
  check('homeHero', await page.locator('.banner-home img').getAttribute('src'))
  await shot(page, 'home-v2-1440')

  // ---------- 登录背景 ----------
  await page.goto(`${BASE}/login`, { waitUntil: 'load' })
  check(
    'loginBackground',
    await page.locator('.auth-page').evaluate((el) => getComputedStyle(el).backgroundImage)
  )
} catch (error) {
  report.fatal = error instanceof Error ? error.stack || error.message : String(error)
  try {
    await page.screenshot({ path: path.join(ARTIFACTS, 'catalog-v2-failure.png'), fullPage: true })
    report.screenshots.push(path.join(ARTIFACTS, 'catalog-v2-failure.png'))
  } catch {
    // ignore
  }
} finally {
  await browser.close()
}

console.log(JSON.stringify(report, null, 2))
