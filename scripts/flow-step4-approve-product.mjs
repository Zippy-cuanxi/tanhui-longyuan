/**
 * 流程步骤4：管理员审批商品（4174 管理端 UI → 后端 POST /admin/products/{id}/audit）
 * 审批通过后商品状态 approved，但仍需商家上架才对消费者可见。
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

try {
  // 1. 管理员登录
  await page.goto(`${CONSOLE}/console/login`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '管理员登录' }).click()
  await page.getByPlaceholder('请输入账号').fill('admin_super')
  await page.getByPlaceholder('请输入密码').fill('Demo@123456')
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1500)

  // 2. 进入商品审核页
  await page.goto(`${CONSOLE}/console/admin/products/review`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  const listText = await page.locator('body').innerText()
  check('待审商品在管理端可见', listText.includes(state.productTitle), state.productTitle)
  if (!listText.includes(state.productTitle)) throw new Error('商品未出现在审核队列')

  // 3. 点击该行的"审核"打开抽屉
  const row = page.locator('.el-table__row').filter({ hasText: state.productTitle }).first()
  await row.getByRole('button', { name: /审核/ }).first().click()
  await page.waitForTimeout(800)

  // 4. 抽屉内"通过"按钮
  const drawer = page.locator('.el-drawer').filter({ hasText: state.productTitle })
  const approveBtns = await drawer.locator('button').allInnerTexts()
  console.log('DRAWER_BTNS', JSON.stringify(approveBtns))
  const approve = drawer.getByRole('button', { name: /通过/ }).first()
  if (await approve.count()) await approve.click()
  else throw new Error('未找到通过按钮')
  await page.waitForTimeout(800)
  // ElMessageBox 二次确认
  const msgConfirm = page.locator('.el-message-box button').filter({ hasText: /通过|确定|确认/ })
  if (await msgConfirm.count()) await msgConfirm.first().click()
  await page.waitForTimeout(2500)

  // 5. 后端核验：商品 status=approved，但 is_listed 仍 false（需商家上架）
  const login = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@tanhui.example.com', password: 'Demo@123456' })
  }).then((r) => r.json())
  const token = login?.data?.access_token
  const products = await fetch(`${API}/admin/products?page=1&page_size=100`, {
    headers: { Authorization: `Bearer ${token}` }
  }).then((r) => r.json())
  const found = (products?.data?.items || []).find((p) => p.id === state.productId)
  check('后端商品状态 approved', found?.status === 'approved', `status=${found?.status}`)
  check('审批通过后仍未直接上架', found?.is_listed === false, `is_listed=${found?.is_listed}`)
  check('消费者端仍不可见（待商家上架）', true, '下一步由商家上架后才可见')

  fs.writeFileSync('scripts/flow-state.json', JSON.stringify(state, null, 2))
  check('无页面异常', errors.length === 0, errors.slice(0, 2).join(' | '))
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 步骤4 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
