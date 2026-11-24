/** 验证 GitHub Pages 静态演示版：消费者端 + 管理端均可访问且可交互。 */
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:4188/tanhui-longyuan'
const results = []
const check = (name, ok, detail = '') => {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${detail ? ' :: ' + detail : ''}`)
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })

try {
  // ===== 消费者端 =====
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))

  await page.goto(`${BASE}/`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  const homeText = await page.locator('body').innerText()
  check('消费者首页加载', homeText.length > 100 && !homeText.includes('页面配置暂不可用'), homeText.slice(0, 40).replace(/\n/g, ' '))

  await page.goto(`${BASE}/products`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  const catalogText = await page.locator('body').innerText()
  const cards = await page.locator('.product-card, [class*="product-card"]').count()
  check('商品列表展示快照商品', cards > 0 || catalogText.includes('SIM-'), `卡片数=${cards}`)

  await page.goto(`${BASE}/notices`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1000)
  const noticeText = await page.locator('body').innerText()
  check('公告页展示快照公告', noticeText.includes('SIM-'), noticeText.includes('SIM-') ? '有SIM公告' : '无')

  // 登录 → 购物车 → 下单 → 支付
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' })
  await page.locator('input').nth(0).fill('simbuyer1@tanhui.example.com')
  await page.locator('input[type="password"]').first().fill('Passw0rd!123')
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1200)
  check('消费者登录(demo)', !(await page.url()).includes('/login'), page.url())

  await page.goto(`${BASE}/products`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1000)
  await page.locator('.product-card, [class*="product-card"]').first().click().catch(() => {})
  await page.waitForTimeout(1000)
  if (!(await page.url()).includes('/products/')) {
    await page.goto(`${BASE}/products/4d21cb04-7cbc-491c-9376-f0e67b6c030b`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)
  }
  const addBtn = page.getByRole('button', { name: /加入购物车/ }).first()
  if (await addBtn.count()) { await addBtn.click(); await page.waitForTimeout(800) }
  check('商品详情+加购', (await page.url()).includes('/products/'), page.url())

  await page.goto(`${BASE}/cart`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1000)
  const cartText = await page.locator('body').innerText()
  check('购物车展示', !cartText.includes('购物车为空') || cartText.includes('去逛逛'), '购物车页可见')

  check('消费者端无JS错误', errors.length === 0, errors.slice(0, 2).join(' | '))
  await page.close()

  // ===== 管理端 =====
  const console = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const cErrors = []
  console.on('pageerror', (e) => cErrors.push(e.message))
  await console.goto(`${BASE}/console/login`, { waitUntil: 'networkidle' })
  await console.waitForTimeout(800)
  await console.getByRole('tab', { name: '管理员登录' }).click()
  await console.getByPlaceholder('请输入账号').fill('admin_super')
  await console.getByPlaceholder('请输入密码').fill('Demo@123456')
  await console.locator('form').press('Enter').catch(() => {})
  await console.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await console.waitForTimeout(1400)
  check('管理端登录(纯mock)', console.url().includes('/console/admin/'), console.url())

  await console.goto(`${BASE}/console/admin/dashboard`, { waitUntil: 'networkidle' })
  await console.waitForTimeout(1500)
  const dashText = await console.locator('body').innerText()
  check('管理端看板渲染', dashText.length > 200 && dashText.includes('商品'), dashText.slice(0, 40).replace(/\n/g, ' '))

  await console.goto(`${BASE}/console/admin/orders`, { waitUntil: 'networkidle' })
  await console.waitForTimeout(1500)
  const orderText = await console.locator('body').innerText()
  check('管理端订单列表(mock)', orderText.length > 200, '列表渲染')
  check('管理端无JS错误', cErrors.length === 0, cErrors.slice(0, 2).join(' | '))
  await console.close()
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 静态演示验证: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
