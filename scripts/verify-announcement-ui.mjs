/** UI 端到端：管理端新建并发布公告 → 消费者 /client/notices 可见。 */
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:5174'
const API = 'http://127.0.0.1:8000/api/v1'
const results = []
const check = (name, ok, detail = '') => { results.push({ ok }); console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${detail ? ' :: ' + detail : ''}`) }

const title = `UI一致性公告-${Date.now().toString().slice(-6)}`
const content = '本公告由管理端界面创建并发布，用于端到端验证数据一致性。'
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const pageErrors = []
page.on('pageerror', (e) => pageErrors.push(e.message))
try {
  await page.goto(`${BASE}/console/login`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '管理员登录' }).click()
  await page.getByPlaceholder('请输入账号').fill('admin_super')
  await page.getByPlaceholder('请输入密码').fill('Demo@123456')
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1200)
  await page.goto(`${BASE}/console/admin/announcements`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1800)

  await page.getByRole('button', { name: /新增|新建/ }).first().click()
  await page.waitForTimeout(400)
  const inputs = page.locator('.el-dialog input, .el-dialog textarea')
  await inputs.nth(0).fill(title)
  await inputs.nth(1).fill(content)
  // 点击"保存并发布"
  const publishBtn = page.locator('.el-dialog__footer button').filter({ hasText: '发布' })
  if (await publishBtn.count()) await publishBtn.first().click()
  else await page.locator('.el-dialog__footer button').last().click()
  await page.waitForTimeout(2000)

  // 检查管理端列表出现该公告
  const annText = await page.locator('body').innerText()
  check('管理端列表显示新公告', annText.includes(title))

  // 检查消费者端 API 可见
  const notices = await fetch(`${API}/client/notices`).then((r) => r.json())
  const found = (Array.isArray(notices) ? notices : []).find((n) => n.title === title)
  check('消费者公告API可见', Boolean(found), found ? `status=published` : '未找到')

  check('无页面异常', pageErrors.length === 0, pageErrors.slice(0, 2).join(' | '))
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}
const passed = results.filter((r) => r.ok).length
console.log(`\n==== 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
