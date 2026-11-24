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
    const soft = []
    const onFail = (r) => {
      const msg = `${r.url()} :: ${r.failure()?.errorText}`
      // ERR_ABORTED 多为元素重渲染/切页取消，不代表资源缺失
      if (/ERR_ABORTED/.test(msg)) soft.push(msg)
      else failed.push('REQFAIL ' + msg)
    }
    const onResp = (r) => {
      // GitHub Pages 对 SPA 深链接返回 404 状态 + 404.html 内容，属预期，不算失败
      if (r.request().resourceType() === 'document') return
      if (r.status() >= 404 && !r.url().includes('hot-update')) failed.push(`HTTP${r.status()} ${r.url()}`)
    }
    page.on('requestfailed', onFail)
    page.on('response', onResp)
    await page
      .goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 60000 })
      .catch((e) => failed.push('GOTO ' + e.message))
    // 等页面异步数据渲染出图片，再等待解码完成（线上大图较慢，避免误判）
    await page.waitForTimeout(1200)
    await page
      .waitForFunction(
        () => Array.from(document.images).every((im) => im.complete && im.naturalWidth > 0),
        null,
        { timeout: 8000 }
      )
      .catch(() => {})
    const imgs = await page.evaluate(() =>
      Array.from(document.images).map((im) => ({
        src: im.currentSrc || im.src,
        w: im.naturalWidth,
      }))
    )
    // naturalWidth=0 可能只是弱网下尚未解码，再用一次直连请求判定资源是否真的缺失
    const suspects = imgs.filter((i) => i.w === 0 && !ignore.some((p) => i.src.includes(p)))
    const broken = []
    const slow = []
    for (const s of suspects) {
      const resp = await page.request.get(s.src).catch(() => null)
      if (!resp || resp.status() >= 400) broken.push(s)
      else slow.push(s)
    }
    const hardFail = failed.filter((f) => !ignore.some((p) => f.includes(p)))
    results.push({ label, route, total: imgs.length, broken: broken.length, failed: hardFail.length })
    const mark = broken.length || hardFail.length ? 'FAIL' : 'PASS'
    console.log(
      `${mark} | ${label} ${route} | 图 ${imgs.length} 失败 ${broken.length} 请求失败 ${hardFail.length}` +
        (slow.length ? ` 未解码 ${slow.length}` : '')
    )
    broken.slice(0, 6).forEach((b) => console.log('     BROKEN ' + b.src))
    hardFail.slice(0, 6).forEach((f) => console.log('     ' + f))
    page.off('requestfailed', onFail)
    page.off('response', onResp)
  }
}

/** 管理端登录：等表单就绪→切角色页签→填账号密码→等路由跳转 */
async function login(page, tabName, account) {
  await page.goto(`${BASE}/console/login`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.getByPlaceholder('请输入账号').waitFor({ timeout: 30000 })
  await page.getByRole('tab', { name: tabName }).click().catch(() => {})
  await page.waitForTimeout(300)
  await page.getByPlaceholder('请输入账号').fill(account)
  await page.getByPlaceholder('请输入密码').fill('Demo@123456')
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForURL(/\/console\/(admin|merchant)\//, { timeout: 30000 }).catch(() => {})
  await page.waitForTimeout(800)
}

try {
  // 消费者端
  const consumer = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await scan(consumer, consumerRoutes, '消费者')
  await consumer.close()

  // 管理端：admin_super
  const admin = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await login(admin, '管理员登录', 'admin_super')
  console.log(`${admin.url().includes('/console/admin/') ? 'PASS' : 'FAIL'} | 管理员登录 -> ${admin.url()}`)
  await scan(admin, adminRoutes.slice(1), '管理端')
  const adminErrors = []
  admin.on('pageerror', (e) => adminErrors.push(e.message))
  await admin.goto(`${BASE}/console/admin/dashboard`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await admin.waitForTimeout(800)
  console.log(`管理端 JS 错误: ${adminErrors.length ? adminErrors.slice(0, 3).join(' | ') : '无'}`)
  await admin.close()

  // 商家端：merchant01
  const merchant = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await login(merchant, '商家登录', 'merchant01')
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
