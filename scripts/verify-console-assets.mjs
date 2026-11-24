/**
 * 静态演示版静态资源体检：模拟 GitHub Pages 子路径部署，逐页统计破图与失败请求。
 * 前置：先 node scripts/serve-demo.mjs（端口 4188），或传入自定义 BASE。
 * 用法：node scripts/verify-console-assets.mjs [baseUrl]
 */
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = process.argv[2] || 'http://127.0.0.1:4188/tanhui-longyuan'

const demo = JSON.parse(fs.readFileSync('public/demo-data.json', 'utf8'))
const firstProduct = demo?.products?.[0]?.id || demo?.data?.products?.[0]?.id
const firstOrder = demo?.orders?.[0]?.id || demo?.data?.orders?.[0]?.id

const consumerRoutes = ['/', '/origin', '/products', '/green', '/join', '/notices', '/aid']
if (firstProduct) consumerRoutes.push(`/products/${firstProduct}`)

const adminRoutes = [
  '/console/login',
  '/console/admin/dashboard',
  '/console/admin/merchants',
  '/console/admin/merchants/review',
  '/console/admin/products',
  '/console/admin/products/review',
  '/console/admin/categories',
  '/console/admin/orders',
  '/console/admin/aftersales',
  '/console/admin/origins',
  '/console/admin/users',
  '/console/admin/announcements',
  '/console/admin/finance',
  '/console/admin/settings',
]

const merchantRoutes = [
  '/console/merchant/dashboard',
  '/console/merchant/products',
  '/console/merchant/products/new',
  '/console/merchant/orders',
  '/console/merchant/aftersales',
  '/console/merchant/finance',
  '/console/merchant/shop',
  '/console/merchant/analytics',
  '/console/merchant/notifications',
]
if (firstOrder) merchantRoutes.push(`/console/merchant/orders/${firstOrder}`)

const results = []
const browser = await chromium.launch({ channel: 'msedge', headless: true })

async function scan(page, routes, label, ignore = []) {
  for (const route of routes) {
    const failed = []
    const onFail = (r) => failed.push(`REQFAIL ${r.url()} :: ${r.failure()?.errorText}`)
    const onResp = (r) => {
      // GitHub Pages 对 SPA 深链接返回 404 状态 + 404.html 内容，属预期，不算失败
      if (r.request().resourceType() === 'document') return
      if (r.status() >= 404 && !r.url().includes('hot-update')) failed.push(`HTTP${r.status()} ${r.url()}`)
    }
    page.on('requestfailed', onFail)
    page.on('response', onResp)
    await page
      .goto(BASE + route, { waitUntil: 'networkidle', timeout: 45000 })
      .catch((e) => failed.push('GOTO ' + e.message))
    // 触发懒加载，并等待所有图片解码完成（线上大图较慢，避免误判）
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)).catch(() => {})
    await page.waitForTimeout(300)
    await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {})
    await page
      .waitForFunction(() => Array.from(document.images).every((im) => im.complete), null, {
        timeout: 30000,
      })
      .catch(() => {})
    const imgs = await page.evaluate(() =>
      Array.from(document.images).map((im) => ({
        src: im.currentSrc || im.src,
        complete: im.complete,
        w: im.naturalWidth,
      }))
    )
    // complete 且 naturalWidth=0 → 确定失败；30s 后仍未 complete → 记为pending提示
    const broken = imgs.filter((i) => i.complete && i.w === 0 && !ignore.some((p) => i.src.includes(p)))
    const pending = imgs.filter((i) => !i.complete && !ignore.some((p) => i.src.includes(p)))
    const hardFail = failed.filter((f) => !ignore.some((p) => f.includes(p)))
    results.push({ label, route, total: imgs.length, broken: broken.length, failed: hardFail.length })
    const mark = broken.length || hardFail.length ? 'FAIL' : 'PASS'
    console.log(
      `${mark} | ${label} ${route} | 图 ${imgs.length} 失败 ${broken.length} 请求失败 ${hardFail.length}` +
        (pending.length ? ` 未完成 ${pending.length}` : '')
    )
    broken.slice(0, 6).forEach((b) => console.log('     BROKEN ' + b.src))
    hardFail.slice(0, 6).forEach((f) => console.log('     ' + f))
    page.off('requestfailed', onFail)
    page.off('response', onResp)
  }
}

try {
  // 消费者端
  const consumer = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await scan(consumer, consumerRoutes, '消费者')
  await consumer.close()

  // 管理端：admin_super
  const admin = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await admin.goto(`${BASE}/console/login`, { waitUntil: 'networkidle' })
  await admin.getByRole('tab', { name: '管理员登录' }).click().catch(() => {})
  await admin.getByPlaceholder('请输入账号').fill('admin_super')
  await admin.getByPlaceholder('请输入密码').fill('Demo@123456')
  await admin.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await admin.waitForTimeout(1500)
  await scan(admin, adminRoutes.slice(1), '管理端')
  const adminErrors = []
  admin.on('pageerror', (e) => adminErrors.push(e.message))
  await admin.goto(`${BASE}/console/admin/dashboard`, { waitUntil: 'networkidle' })
  await admin.waitForTimeout(800)
  console.log(`管理端 JS 错误: ${adminErrors.length ? adminErrors.slice(0, 3).join(' | ') : '无'}`)
  await admin.close()

  // 商家端：merchant01
  const merchant = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await merchant.goto(`${BASE}/console/login`, { waitUntil: 'networkidle' })
  await merchant.getByRole('tab', { name: '商家登录' }).click().catch(() => {})
  await merchant.getByPlaceholder('请输入账号').fill('merchant01')
  await merchant.getByPlaceholder('请输入密码').fill('Demo@123456')
  await merchant.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await merchant.waitForTimeout(1500)
  const loginOk = merchant.url().includes('/console/merchant/')
  console.log(`${loginOk ? 'PASS' : 'FAIL'} | 商家登录 -> ${merchant.url()}`)
  await scan(merchant, merchantRoutes, '商家端')
  await merchant.close()
} catch (err) {
  console.log('脚本异常: ' + (err instanceof Error ? err.message : String(err)))
} finally {
  await browser.close()
}

const bad = results.filter((r) => r.broken || r.failed)
console.log(`\n==== 静态资源体检: ${results.length - bad.length}/${results.length} 页面通过 ====`)
if (bad.length) {
  bad.forEach((b) => console.log(`  ${b.label} ${b.route} 破图 ${b.broken} 失败请求 ${b.failed}`))
}
process.exit(bad.length ? 1 : 0)
