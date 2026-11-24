/**
 * 步骤6d：管理员审核购买后流程 - 售后仲裁（4174 管理端 UI → 后端 /admin/refunds/{id}/handle）
 * 管理员裁决"支持退款"，验证后端退款单 refunded + 消费者端可见。
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

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
const reviewCalls = []
page.on('pageerror', (e) => errors.push(e.message))
page.on('response', (res) => {
  if (res.url().includes('/api/v1/admin/refunds/') && res.url().includes('/handle')) {
    reviewCalls.push(`${res.request().method()} ${res.url().split('/api/v1')[1]} -> ${res.status()}`)
  }
})

try {
  await page.goto(`${CONSOLE}/console/login`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '管理员登录' }).click()
  await page.getByPlaceholder('请输入账号').fill('admin_super')
  await page.getByPlaceholder('请输入密码').fill('Demo@123456')
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1500)

  await page.goto(`${CONSOLE}/console/admin/aftersales`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  const listText = await page.locator('body').innerText()
  check('退款单在管理端售后列表可见', listText.includes(state.refundNo), state.refundNo)
  if (!listText.includes(state.refundNo)) throw new Error('退款单未出现在售后列表')

  // 找该行，点击"裁决"
  const row = page.locator('.el-table__row').filter({ hasText: state.refundNo }).first()
  const rowBtns = await row.locator('button').allInnerTexts()
  console.log('ROW_BTNS', JSON.stringify(rowBtns))
  const arbitrateBtn = row.getByRole('button', { name: /裁决/ }).first()
  if (await arbitrateBtn.count()) await arbitrateBtn.click()
  else {
    // 点详情打开抽屉再裁决
    await row.getByRole('button', { name: /详情/ }).first().click()
    await page.waitForTimeout(800)
    await page.getByRole('button', { name: /支持退款/ }).first().click()
  }
  await page.waitForTimeout(600)

  // 裁决理由弹窗
  const reasonBox = page.locator('.el-dialog, .el-message-box').filter({ hasText: /裁决理由|退款/ })
  const reasonInput = reasonBox.locator('textarea, input').first()
  if (await reasonInput.count()) await reasonInput.fill('流程验证：核实符合退款条件，支持退款。')
  const supportsBtn = reasonBox.getByRole('button', { name: /支持退款|确.*认|确定/ }).last()
  if (await supportsBtn.count()) await supportsBtn.click()
  await page.waitForTimeout(1000)
  const msgConfirm = page.locator('.el-message-box button').filter({ hasText: /确定|确认/ })
  if (await msgConfirm.count()) await msgConfirm.first().click()
  await page.waitForTimeout(2500)
  console.log('REVIEW_CALLS', JSON.stringify(reviewCalls))

  // 后端核验
  const login = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@tanhui.example.com', password: 'Demo@123456' })
  }).then((r) => r.json())
  const token = login?.data?.access_token
  const refunds = await fetch(`${API}/admin/refunds?page=1&page_size=100`, {
    headers: { Authorization: `Bearer ${token}` }
  }).then((r) => r.json())
  const found = (refunds?.data?.items || []).find((r) => r.id === state.refundId)
  check('后端退款单 refunded', found?.status === 'refunded', `status=${found?.status} result=${found?.result_note}`)

  // 消费者端退款记录可见
  const bLogin = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'buyer@tanhui.example.com', password: 'Passw0rd!123' })
  }).then((r) => r.json())
  const bToken = bLogin?.data?.access_token
  const myRefunds = await fetch(`${API}/orders/${state.orderId}/refunds`, {
    headers: { Authorization: `Bearer ${bToken}` }
  }).then((r) => r.json())
  const consumerSees = JSON.stringify(myRefunds).includes(state.refundId)
  check('消费者端可见退款结果', consumerSees, consumerSees ? '退款记录含该退款单' : '未找到')

  check('无页面异常', errors.length === 0, errors.slice(0, 2).join(' | '))
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 步骤6d 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
