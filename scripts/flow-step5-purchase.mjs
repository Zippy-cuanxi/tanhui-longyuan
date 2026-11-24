/**
 * 流程步骤5：消费者购买商品（5174 消费者端 → 真实后端）
 * 从 /products?page=2 找到流程验证商品 → 详情 → 立即购买 → 结算 → 沙箱支付。
 */
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:5174'
const API = 'http://127.0.0.1:8000/api/v1'
const state = JSON.parse(fs.readFileSync('scripts/flow-state.json', 'utf8'))
const results = []
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${detail ? ' :: ' + detail : ''}`)
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
page.on('pageerror', (e) => errors.push(e.message))

try {
  // 1. 消费者登录
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' })
  await page.locator('input').nth(0).fill('buyer@tanhui.example.com')
  await page.locator('input[type="password"]').first().fill('Passw0rd!123')
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1500)
  check('消费者登录', !(await page.url()).includes('/login'), page.url())

  // 2. 指定入口：/products?page=2，翻页找到商品
  await page.goto(`${BASE}/products?page=2`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  check('商品列表页(page=2)', page.url().includes('/products'), page.url())

  // 搜索流程验证商品（列表支持关键词）
  const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="商品"]').first()
  if (await searchInput.count()) {
    await searchInput.fill('流程验证')
    await searchInput.press('Enter')
    await page.waitForTimeout(1500)
  }
  let foundOnList = (await page.locator('body').innerText()).includes(state.productTitle)
  if (!foundOnList) {
    // 回到 page=1 搜索
    await page.goto(`${BASE}/products`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1200)
    const si = page.locator('input[placeholder*="搜索"], input[placeholder*="商品"]').first()
    if (await si.count()) { await si.fill('流程验证'); await si.press('Enter'); await page.waitForTimeout(1500) }
    foundOnList = (await page.locator('body').innerText()).includes(state.productTitle)
  }
  check('消费者列表可见商品', foundOnList, state.productTitle)
  if (!foundOnList) throw new Error('消费者端未找到商品')

  // 3. 进入详情
  const card = page.locator('a, .product-card').filter({ hasText: state.productTitle }).first()
  await card.click().catch(() => {})
  await page.waitForTimeout(1500)
  const detailOk = (await page.locator('body').innerText()).includes(state.productTitle)
  check('商品详情打开', detailOk, page.url())
  if (!page.url().includes('/products/')) {
    await page.goto(`${BASE}/products/${state.productId}`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1200)
  }

  // 4. 立即购买
  await page.getByRole('button', { name: /立即购买/ }).first().click()
  await page.waitForTimeout(1500)
  check('进入结算页', page.url().includes('/checkout'), page.url())

  // 5. 结算页确认地址与预览，提交订单
  await page.waitForTimeout(1000)
  const addressText = await page.locator('body').innerText()
  check('结算页有收货地址', addressText.includes('王小明'), addressText.includes('王小明') ? '默认地址已选' : '未找到地址')

  const submitBtn = page.getByRole('button', { name: /提交订单|确认下单/ }).first()
  if (await submitBtn.count()) await submitBtn.click()
  else throw new Error('未找到提交订单按钮')
  await page.waitForTimeout(2000)

  // 6. 跳支付页 → 沙箱支付
  check('进入支付页', page.url().includes('/pay/'), page.url())
  const payBtn = page.getByRole('button', { name: /沙箱支付|确认支付/ }).first()
  if (await payBtn.count()) await payBtn.click()
  else throw new Error('未找到支付按钮')
  await page.waitForTimeout(2500)

  const payText = await page.locator('body').innerText()
  check('支付成功', payText.includes('支付成功'), payText.split('\n').filter((l) => l.includes('支付成功') || l.includes('订单')).slice(0, 2).join(' | '))

  // 7. 后端核验订单
  const login = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'buyer@tanhui.example.com', password: 'Passw0rd!123' })
  }).then((r) => r.json())
  const token = login?.data?.access_token
  const orders = await fetch(`${API}/orders`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json())
  const items = orders?.data?.items || []
  const latest = items.find((o) => JSON.stringify(o).includes(state.productId)) || items[0]
  const paid = latest?.status === 'paid'
  check('后端订单为 paid 状态', paid, latest ? `${latest.order_no} status=${latest.status} pay=${latest.pay_amount}` : '无订单')

  if (latest) {
    state.orderId = latest.id
    state.orderNo = latest.order_no
    state.orderStoreOrderId = latest.store_orders?.[0]?.id || ''
    fs.writeFileSync('scripts/flow-state.json', JSON.stringify(state, null, 2))
  }
  check('无页面异常', errors.length === 0, errors.slice(0, 2).join(' | '))
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 步骤5 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
