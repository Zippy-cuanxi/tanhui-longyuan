/**
 * 流程步骤2：管理员审批商家入驻（4174 preview 管理端 UI → 后端 POST /admin/merchants/{id}/review）
 * 依赖 flow-state.json（步骤1产出），更新 merchantApproved。
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
page.on('pageerror', (e) => errors.push(e.message))
const reviewCalls = []
page.on('response', async (res) => {
  if (res.url().includes('/admin/merchants/') && res.url().includes('/review')) {
    reviewCalls.push({ url: res.url(), status: res.status() })
  }
})

try {
  // 1. 管理端登录（管理员）
  await page.goto(`${CONSOLE}/console/login`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '管理员登录' }).click()
  await page.getByPlaceholder('请输入账号').fill('admin_super')
  await page.getByPlaceholder('请输入密码').fill('Demo@123456')
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1500)
  check('管理端登录', page.url().includes('/console/admin/'), page.url())

  // 2. 进入入驻审核页，触发同步，确认新申请可见
  await page.goto(`${CONSOLE}/console/admin/merchants/review`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  const listText = await page.locator('body').innerText()
  const visible = listText.includes(state.company)
  check('新入驻申请在管理端可见', visible, state.company)

  if (!visible) throw new Error('管理端未投影出新申请，无法继续审批')

  // 3. 找到该行并点击"审核"
  const row = page.locator('.el-table__row').filter({ hasText: state.company }).first()
  const rowText = await row.innerText().catch(() => '')
  console.log('ROW', rowText.slice(0, 200).replace(/\n/g, ' | '))
  await row.getByRole('button', { name: /审核/ }).first().click()
  await page.waitForTimeout(800)

  // 4. 抽屉中点"审核通过"（精确匹配抽屉内的按钮，避免误点页签"已通过"）
  const drawer = page.locator('.el-drawer').filter({ hasText: state.company })
  const approveBtn = drawer.getByRole('button', { name: '审核通过' })
  console.log('APPROVE_BTN_COUNT', await approveBtn.count())
  await approveBtn.first().click()
  await page.waitForTimeout(800)
  // ElMessageBox.confirm 的确认按钮文字同为"审核通过"
  const msgBox = page.locator('.el-message-box')
  const confirmBtn = msgBox.getByRole('button', { name: '审核通过' })
  console.log('MSGBOX_CONFIRM_COUNT', await confirmBtn.count())
  if (await confirmBtn.count()) await confirmBtn.first().click()
  else await msgBox.locator('button').last().click().catch(() => {})
  await page.waitForTimeout(2500)
  console.log('REVIEW_CALLS', JSON.stringify(reviewCalls))

  // 5. 后端核验：merchant 状态应为 approved，且自动创建店铺
  const login = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@tanhui.example.com', password: 'Demo@123456' })
  }).then((r) => r.json())
  const token = login?.data?.access_token
  const merchants = await fetch(`${API}/admin/merchants`, { headers: { Authorization: `Bearer ${token}` } })
    .then((r) => r.json())
  const found = (merchants?.data?.items || []).find((m) => m.company_name === state.company)
  check('后端商家状态 approved', found?.status === 'approved', `status=${found?.status}`)

  const stores = await fetch(`${API}/admin/stores`, { headers: { Authorization: `Bearer ${token}` } })
    .then((r) => r.json())
  const storeForMerchant = (stores?.data?.items || []).find((s) => s.merchant_id === state.merchantId || s.name?.includes(state.company.slice(0, 6)))
  check('审批通过后自动创建店铺', Boolean(storeForMerchant), storeForMerchant ? `${storeForMerchant.name} id=${storeForMerchant.id}` : '未找到')

  state.merchantApproved = found?.status === 'approved'
  state.storeId = storeForMerchant?.id || ''
  state.storeName = storeForMerchant?.name || ''
  fs.writeFileSync('scripts/flow-state.json', JSON.stringify(state, null, 2))
  check('无页面异常', errors.length === 0, errors.slice(0, 2).join(' | '))
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 步骤2 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
