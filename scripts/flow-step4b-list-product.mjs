/**
 * 步骤4b：商家上架已审批商品（后端强制 approved 才可 list，是审批闸门的一部分）
 * 商家端 UI → 后端 POST /merchant/products/{id}/list
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
  await page.goto(`${CONSOLE}/console/login`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '商家登录' }).click()
  await page.getByPlaceholder('请输入账号').fill('merchant01')
  await page.getByPlaceholder('请输入密码').fill('Demo@123456')
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1500)

  await page.goto(`${CONSOLE}/console/merchant/products`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  const listText = await page.locator('body').innerText()
  check('已审批商品在商家端可见', listText.includes(state.productTitle), state.productTitle)
  if (!listText.includes(state.productTitle)) throw new Error('商品未出现在商家列表')

  // 找该行，点击"上架"（页面可能有"上架/下架"切换按钮）
  const row = page.locator('.el-table__row').filter({ hasText: state.productTitle }).first()
  const rowBtns = await row.locator('button').allInnerTexts()
  console.log('ROW_BTNS', JSON.stringify(rowBtns))
  let listBtn = row.getByRole('button', { name: /^上架$/ })
  if (await listBtn.count()) await listBtn.first().click()
  else {
    // 可能是开关/更多菜单
    const toggle = row.locator('.el-switch').first()
    if (await toggle.count()) await toggle.click()
    else throw new Error('未找到上架控件')
  }
  await page.waitForTimeout(800)
  const msgConfirm = page.locator('.el-message-box button').filter({ hasText: /确定|确认|上架/ })
  if (await msgConfirm.count()) await msgConfirm.first().click()
  await page.waitForTimeout(2000)

  // 后端核验
  const login = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@tanhui.example.com', password: 'Demo@123456' })
  }).then((r) => r.json())
  const token = login?.data?.access_token
  const products = await fetch(`${API}/admin/products?page=1&page_size=100`, {
    headers: { Authorization: `Bearer ${token}` }
  }).then((r) => r.json())
  const found = (products?.data?.items || []).find((p) => p.id === state.productId)
  check('后端商品已上架 is_listed=true', found?.is_listed === true, `is_listed=${found?.is_listed}`)

  const consumer = await fetch(`${API}/products?page=1&page_size=100`).then((r) => r.json())
  const visible = (consumer?.data?.items || []).some((p) => p.title === state.productTitle)
  check('消费者端可见该商品', visible, visible ? '已出现在商品列表' : '未出现')

  check('无页面异常', errors.length === 0, errors.slice(0, 2).join(' | '))
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 步骤4b 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
