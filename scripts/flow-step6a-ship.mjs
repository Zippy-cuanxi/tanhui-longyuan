/**
 * 步骤6a：商家发货（4174 商家端 UI → 后端 /merchant/orders/{id}/ship）
 * 步骤6b：消费者物流可见（后端 /logistics/{orderId}）
 */
import { chromium } from 'playwright'
import fs from 'node:fs'

const CONSOLE = 'http://127.0.0.1:4174'
const API = 'http://127.0.0.1:8000/api/v1'
const state = JSON.parse(fs.readFileSync('scripts/flow-state.json', 'utf8'))
const results = []
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${detail ? ' :: ' + detail : ''}`)
}
const trackingNo = 'SF' + Date.now().toString().slice(-10)

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
page.on('pageerror', (e) => errors.push(e.message))

try {
  await page.goto(`${CONSOLE}/console/login`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '商家登录' }).click()
  await page.getByPlaceholder('请输入账号').fill('merchant01')
  await page.getByPlaceholder('请输入密码').fill('Demo@123456')
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1500)

  await page.goto(`${CONSOLE}/console/merchant/orders`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  const listText = await page.locator('body').innerText()
  const orderNo = state.storeOrderNo || state.orderNo
  const orderVisible = listText.includes(orderNo)
  check('新订单在商家端可见（消费者下单投影）', orderVisible, `${orderNo}（店铺子单号）`)
  if (!orderVisible) throw new Error('订单未投影到商家端')

  // 找该订单行，点"发货"
  const row = page.locator('.el-table__row').filter({ hasText: orderNo }).first()
  const rowBtns = await row.locator('button').allInnerTexts()
  console.log('ROW_BTNS', JSON.stringify(rowBtns))
  const shipBtn = row.getByRole('button', { name: /发货/ }).first()
  if (await shipBtn.count()) await shipBtn.click()
  else throw new Error('未找到发货按钮')
  await page.waitForTimeout(800)

  // 发货抽屉：填快递公司 + 单号
  const drawer = page.locator('.el-drawer').filter({ hasText: /发货/ })
  const selects = drawer.locator('.el-select')
  if (await selects.count()) {
    await selects.first().click()
    await page.waitForTimeout(400)
    const opt = page.locator('.el-select-dropdown__item').filter({ hasText: '顺丰' }).first()
    if (await opt.count()) await opt.click()
    else await page.locator('.el-select-dropdown__item').first().click()
  }
  await drawer.locator('input[type="text"], input:not([type])').last().fill(trackingNo).catch(() => {})
  const confirmShip = drawer.getByRole('button', { name: /确认发货|发货/ }).last()
  if (await confirmShip.count()) await confirmShip.click()
  await page.waitForTimeout(800)
  const msgConfirm = page.locator('.el-message-box button').filter({ hasText: /确定|确认/ })
  if (await msgConfirm.count()) await msgConfirm.first().click()
  await page.waitForTimeout(2500)

  // 后端核验
  const mLogin = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'merchant1@tanhui.example.com', password: 'Passw0rd!123' })
  }).then((r) => r.json())
  const mToken = mLogin?.data?.access_token
  const so = await fetch(`${API}/merchant/orders/${state.orderStoreOrderId}`, {
    headers: { Authorization: `Bearer ${mToken}` }
  }).then((r) => r.json())
  check('后端子单状态 shipped', so?.data?.status === 'shipped', `status=${so?.data?.status}`)

  // 消费者物流可见
  const bLogin = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'buyer@tanhui.example.com', password: 'Passw0rd!123' })
  }).then((r) => r.json())
  const bToken = bLogin?.data?.access_token
  const logistics = await fetch(`${API}/logistics/${state.orderId}`, {
    headers: { Authorization: `Bearer ${bToken}` }
  }).then((r) => r.json())
  const logRaw = JSON.stringify(logistics)
  check('消费者物流含快递单号', logRaw.includes(trackingNo), `tracking=${trackingNo}`)

  state.trackingNo = trackingNo
  fs.writeFileSync('scripts/flow-state.json', JSON.stringify(state, null, 2))
  check('无页面异常', errors.length === 0, errors.slice(0, 2).join(' | '))
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 步骤6a/6b 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
