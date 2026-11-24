/**
 * 步骤6c：消费者申请退款（5174 消费者端 → 后端 POST /orders/{id}/refunds）
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
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' })
  await page.locator('input').nth(0).fill('buyer@tanhui.example.com')
  await page.locator('input[type="password"]').first().fill('Passw0rd!123')
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1500)

  // 申请退款页
  await page.goto(`${BASE}/account/orders/${state.orderId}/refund`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  check('退款申请页打开', page.url().includes('/refund'), page.url())

  // 选择店铺子单（radio）
  const radios = page.locator('input[type="radio"][name="store-order"]')
  const radioCount = await radios.count()
  console.log('RADIO_COUNT', radioCount)
  if (radioCount) await radios.first().check()
  await page.waitForTimeout(400)

  // 填原因
  const reasonInput = page.locator('textarea, input[placeholder*="原因"]').first()
  if (await reasonInput.count()) await reasonInput.fill('流程验证：商品与描述不符，申请退款。')
  // 确认金额已自动填充
  const amountVal = await page.locator('input[type="number"]').first().inputValue().catch(() => '')
  console.log('AMOUNT', amountVal)

  const submitBtn = page.getByRole('button', { name: /提交退款申请/ }).first()
  if (await submitBtn.count()) await submitBtn.click()
  else throw new Error('未找到提交退款申请按钮')
  await page.waitForTimeout(2000)
  const pageText = await page.locator('body').innerText()
  console.log('AFTER_SUBMIT', pageText.split('\n').filter((l) => l.includes('退款申请已提交') || l.includes('请填写') || l.includes('请选择')).slice(0, 3).join(' | '))

  // 后端核验：退款单 status=requested
  const login = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@tanhui.example.com', password: 'Demo@123456' })
  }).then((r) => r.json())
  const token = login?.data?.access_token
  const refunds = await fetch(`${API}/admin/refunds?page=1&page_size=100`, {
    headers: { Authorization: `Bearer ${token}` }
  }).then((r) => r.json())
  const found = (refunds?.data?.items || []).find((r) => r.order_id === state.orderId)
  check('后端退款单创建 status=requested', found?.status === 'requested', found ? `id=${found.id} status=${found.status} amount=${found.amount}` : '未找到')

  if (found) {
    state.refundId = found.id
    state.refundNo = found.refund_no
    fs.writeFileSync('scripts/flow-state.json', JSON.stringify(state, null, 2))
  }
  check('无页面异常', errors.length === 0, errors.slice(0, 2).join(' | '))
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 步骤6c 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
