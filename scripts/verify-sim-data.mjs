/**
 * 验证仿真数据在管理端与消费者端 UI 可见、状态页签正确、无报错。
 */
import { chromium } from 'playwright'

const CONSOLE = 'http://127.0.0.1:4174'
const B2C = 'http://127.0.0.1:5174'
const results = []
const check = (name, ok, detail = '') => {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${detail ? ' :: ' + detail : ''}`)
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })

async function loginConsole(page, role, user, pwd) {
  await page.goto(`${CONSOLE}/console/login`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: role === 'admin' ? '管理员登录' : '商家登录' }).click()
  await page.getByPlaceholder('请输入账号').fill(user)
  await page.getByPlaceholder('请输入密码').fill(pwd)
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1400)
}

try {
  // ===== 管理端 =====
  const admin = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const adminErrors = []
  admin.on('pageerror', (e) => adminErrors.push(e.message))
  await loginConsole(admin, 'admin', 'admin_super', 'Demo@123456')

  // 入驻审核页：应看到 2 个 SIM 待审商家
  await admin.goto(`${CONSOLE}/console/admin/merchants/review`, { waitUntil: 'networkidle' })
  await admin.waitForTimeout(2200)
  const merchantText = await admin.locator('body').innerText()
  const simPending = (merchantText.match(/SIM-/g) || []).length
  check('管理端入驻审核可见仿真商家', simPending >= 2, `SIM出现${simPending}次`)

  // 商品审核页：应看到 SIM 待审商品
  await admin.goto(`${CONSOLE}/console/admin/products/review`, { waitUntil: 'networkidle' })
  await admin.waitForTimeout(2200)
  const productText = await admin.locator('body').innerText()
  check('管理端商品审核可见待审商品', productText.includes('SIM-'), productText.includes('SIM-') ? '有SIM待审' : '无')

  // 订单列表：应看到 SIM 订单号
  await admin.goto(`${CONSOLE}/console/admin/orders`, { waitUntil: 'networkidle' })
  await admin.waitForTimeout(2200)
  const orderText = await admin.locator('body').innerText()
  check('管理端订单列表可见仿真订单', orderText.includes('SIM-TS'), orderText.includes('SIM-TS') ? '有SIM订单(店铺子单号)' : '无')

  // 售后列表：应看到 SIM 退款
  await admin.goto(`${CONSOLE}/console/admin/aftersales`, { waitUntil: 'networkidle' })
  await admin.waitForTimeout(2200)
  const afterText = await admin.locator('body').innerText()
  check('管理端售后列表可见仿真退款', afterText.includes('SIM-RF'), afterText.includes('SIM-RF') ? '有SIM退款' : '无')

  // 公告页
  await admin.goto(`${CONSOLE}/console/admin/announcements`, { waitUntil: 'networkidle' })
  await admin.waitForTimeout(2200)
  const annText = await admin.locator('body').innerText()
  check('管理端公告页可见仿真公告', annText.includes('SIM-'), 'SIM公告')
  check('管理端无控制台错误', adminErrors.length === 0, adminErrors.slice(0, 2).join(' | '))
  await admin.close()

  // ===== 消费者端 =====
  const consumer = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const cErrors = []
  consumer.on('pageerror', (e) => cErrors.push(e.message))

  // 商品列表：用搜索框过滤 SIM，避免分页导致误判
  await consumer.goto(`${B2C}/products`, { waitUntil: 'networkidle' })
  await consumer.waitForTimeout(1200)
  const search = consumer.locator('input[placeholder*="搜索"], input[placeholder*="商品"]').first()
  if (await search.count()) {
    await search.fill('SIM')
    await search.press('Enter')
    await consumer.waitForTimeout(1500)
  }
  const catalogText = await consumer.locator('body').innerText()
  check('消费者商品列表可见在售仿真商品', catalogText.includes('SIM-'), 'SIM在售(搜索过滤)')

  // 公告
  await consumer.goto(`${B2C}/notices`, { waitUntil: 'networkidle' })
  await consumer.waitForTimeout(1200)
  const noticesText = await consumer.locator('body').innerText()
  check('消费者公告页可见仿真公告', noticesText.includes('SIM-'), noticesText.includes('SIM-') ? '有' : '无')

  // 消费者登录后订单页（SIM订单属 simbuyer1）
  await consumer.goto(`${B2C}/login`, { waitUntil: 'networkidle' })
  await consumer.locator('input').nth(0).fill('simbuyer1@tanhui.example.com')
  await consumer.locator('input[type="password"]').first().fill('Passw0rd!123')
  await consumer.locator('form').press('Enter').catch(() => {})
  await consumer.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await consumer.waitForTimeout(1400)
  await consumer.goto(`${B2C}/account/orders`, { waitUntil: 'networkidle' })
  await consumer.waitForTimeout(1500)
  const myOrders = await consumer.locator('body').innerText()
  check('消费者订单页可见自己的仿真订单', myOrders.includes('SIM-TH'), myOrders.includes('SIM-TH') ? '有' : '无')
  check('消费者端无控制台错误', cErrors.length === 0, cErrors.slice(0, 2).join(' | '))
  await consumer.close()
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 仿真数据 UI 验证: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
