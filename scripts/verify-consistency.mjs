/**
 * 数据一致性验证：消费者端(真实后端) ↔ 管理端(投影桥)
 * 前置：8000 后端 + 5174 dev server 运行中。
 */
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:5174'
const API = 'http://127.0.0.1:8000/api/v1'
const results = []
function check(name, ok, detail = '') {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${detail ? ' :: ' + detail : ''}`)
}

async function apiJson(path, token) {
  const res = await fetch(`${API}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  const text = await res.text()
  try { return JSON.parse(text) } catch { return null }
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()
const consoleErrors = []
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })

try {
  // 0. 后端真实数据基线
  const login = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@tanhui.example.com', password: 'Demo@123456' })
  }).then((r) => r.json())
  const adminToken = login?.data?.access_token
  check('后端管理员登录', Boolean(adminToken), `token=${adminToken ? 'ok' : 'fail'}`)

  await apiJson('/admin/orders?page=1&page_size=50', adminToken)
  // 管理端投影使用 store_order_no(TS...)，从商家端拉取真实店铺子单号
  const merchantLogin = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'merchant1@tanhui.example.com', password: 'Passw0rd!123' })
  }).then((r) => r.json())
  const merchantOrders = await apiJson('/merchant/orders', merchantLogin?.data?.access_token)
  const backendOrderNos = (merchantOrders?.data?.items || []).map((o) => o.store_order_no).filter(Boolean)
  check('后端存在真实订单', backendOrderNos.length > 0, `${backendOrderNos.length} 单, 例: ${backendOrderNos[0]}`)

  const noticeRaw = await fetch(`${API}/client/notices`).then((r) => r.json())
  const backendNoticeTitles = (Array.isArray(noticeRaw) ? noticeRaw : []).map((n) => n.title)
  check('后端存在已发布公告', backendNoticeTitles.length > 0, backendNoticeTitles.join(' / '))

  // 1. 管理端登录（管理员）
  await page.goto(`${BASE}/console/login`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '管理员登录' }).click()
  await page.getByPlaceholder('请输入账号').fill('admin_super')
  await page.getByPlaceholder('请输入密码').fill('Demo@123456')
  // 验证码连续失败才出现，演示账号一次成功
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1500)
  const afterLogin = page.url()
  check('管理端管理员登录', afterLogin.includes('/console/admin/'), afterLogin)

  // 2. 强制同步（页面 API 读取会自动触发桥接同步）
  await page.goto(`${BASE}/console/admin/orders`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  const bodyText = await page.locator('body').innerText()
  const visibleRealOrders = backendOrderNos.filter((no) => bodyText.includes(no))
  check('消费者订单在管理端可见', visibleRealOrders.length > 0,
    `可见 ${visibleRealOrders.length}/${backendOrderNos.length} 单, 例: ${visibleRealOrders[0] || '无'}`)

  // 3. localStorage 投影含真实订单
  const dbState = await page.evaluate(() => {
    try {
      const db = JSON.parse(localStorage.getItem('tanhui_console_db_v1') || '{}')
      const map = JSON.parse(localStorage.getItem('tanhui_console_id_map_v1') || '{}')
      return { orders: (db.orders || []).map((o) => o.orderNo), hasMap: Boolean(map.uuidToMock), accounts: Boolean(localStorage.getItem('tanhui_console_backend_token')) }
    } catch { return { orders: [], hasMap: false, accounts: false } }
  })
  const projectedReal = backendOrderNos.filter((no) => dbState.orders.includes(no))
  check('后端订单已投影到本地数据源', projectedReal.length > 0,
    `投影 ${projectedReal.length} 单; ID映射=${dbState.hasMap}; 后端令牌=${dbState.accounts}`)

  // 4. 绿色占比 bug 修复：打开看板读取数字
  await page.goto(`${BASE}/console/admin/dashboard`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2000)
  const dashText = await page.locator('body').innerText()
  const ratioMatch = dashText.match(/绿色商品占比[\s\S]{0,80}?([\d.]+)%/)
  const ratio = ratioMatch ? Number(ratioMatch[1]) : null
  check('绿色占比 ≤ 100% (bug已修)', ratio !== null && ratio <= 100, `ratio=${ratio}%`)

  // 5. 公告在管理端可见（消费者发布 → 管理投影）
  await page.goto(`${BASE}/console/admin/announcements`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2000)
  const annText = await page.locator('body').innerText()
  const visibleNotices = backendNoticeTitles.filter((t) => annText.includes(t))
  check('后端公告在管理端可见', visibleNotices.length > 0,
    `可见 ${visibleNotices.length}/${backendNoticeTitles.length}, 例: ${visibleNotices[0] || '无'}`)

  // 6. 无控制台错误
  check('无控制台错误', consoleErrors.length === 0, consoleErrors.slice(0, 2).join(' | '))

} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
