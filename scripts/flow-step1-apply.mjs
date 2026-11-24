/**
 * 流程步骤1：商家入驻申请（消费者端 UI → 后端 POST /merchant/apply）
 * 输出 step1-state.json 供后续步骤使用。
 */
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:5174'
const API = 'http://127.0.0.1:8000/api/v1'
const STAMP = Date.now().toString().slice(-10)
const company = `陇原流程验证合作社${STAMP.slice(-4)}`
const creditCode = `91620000MA${STAMP.padStart(8, '0').slice(0, 8)}` // 18位
const phone = `139${STAMP.slice(0, 8)}`
const contact = '流程测试联系人'

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
  // 1. 消费者登录（后端 apply 要求已登录用户）
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('请输入邮箱').fill('buyer@tanhui.example.com').catch(async () => {
    const inputs = page.locator('input')
    await inputs.nth(0).fill('buyer@tanhui.example.com')
  })
  await page.getByPlaceholder('请输入密码').fill('Passw0rd!123').catch(async () => {
    await page.locator('input[type="password"]').first().fill('Passw0rd!123')
  })
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1500)
  const loggedIn = !(await page.url()).includes('/login')
  check('消费者登录', loggedIn, page.url())

  // 2. 打开入驻页
  await page.goto(`${BASE}/join`, { waitUntil: 'networkidle' })
  const formVisible = await page.locator('#join-form').count()
  check('入驻表单可见', formVisible > 0)

  // 3. 填写表单
  await page.locator('#join-form input, #join-form select').count()
  await page.evaluate(({ company, creditCode, phone, contact }) => {
    const set = (el, val) => {
      const desc = Object.getOwnPropertyDescriptor(el.__proto__, 'value')
      desc.set.call(el, val)
      el.dispatchEvent(new Event('input', { bubbles: true }))
      el.dispatchEvent(new Event('change', { bubbles: true }))
    }
    const byId = (id) => document.getElementById(id)
    if (byId('join-entity-name')) set(byId('join-entity-name'), company)
    if (byId('join-credit-code')) set(byId('join-credit-code'), creditCode)
    if (byId('join-contact')) set(byId('join-contact'), contact)
    if (byId('join-phone')) set(byId('join-phone'), phone)
  }, { company, creditCode, phone, contact })

  // 用 Playwright 原生 fill（对 Vue v-model 更可靠）
  await page.locator('input[id*="entity"], input[placeholder*="主体"]').first().fill(company).catch(() => {})
  await page.locator('input[id*="credit"], input[placeholder*="信用"]').first().fill(creditCode).catch(() => {})
  await page.locator('input[id*="contact"], input[placeholder*="联系人"]').first().fill(contact).catch(() => {})
  await page.locator('input[id*="phone"], input[placeholder*="手机"]').first().fill(phone).catch(() => {})
  await page.locator('select[id*="city"]').first().selectOption({ index: 1 }).catch(() => {})
  await page.waitForTimeout(300)
  await page.locator('select[id*="district"]').first().selectOption({ index: 1 }).catch(() => {})

  // 证照上传：全局 file input（DOM 结构在 #join-form section 之外）
  const fileInput = page.locator('input[type="file"].join-file-input')
  const png = Buffer.from('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c6360000002000100', 'hex')
  // 营业执照 + 食品经营许可证：两次 setInputFiles 触发 onFileChange，按 uploadTarget 分流
  for (const [label, name] of [['营业执照', 'license.png'], ['食品经营许可证', 'food.png']]) {
    const uploadBtn = page.getByRole('button', { name: new RegExp(label) }).first()
    if (await uploadBtn.count()) await uploadBtn.click().catch(() => {})
    await fileInput.setInputFiles({ name, mimeType: 'image/png', buffer: png }).catch(() => {})
    await page.waitForTimeout(150)
  }
  const certState = await page.locator('.join-cert-copy small').allInnerTexts().catch(() => [])
  console.log('CERT_STATE', JSON.stringify(certState))
  await page.locator('.join-agree input[type="checkbox"]').check().catch(() => {})

  const formState = await page.evaluate(() => {
    const vals = {}
    document.querySelectorAll('#join-form input, #join-form select').forEach((el, i) => {
      vals[el.id || el.getAttribute('placeholder') || `i${i}`] = el.value
    })
    return vals
  })
  console.log('FORM_STATE', JSON.stringify(formState))

  // 4. 提交
  await page.getByRole('button', { name: /提交入驻申请/ }).click()
  await page.waitForTimeout(2000)
  const bodyText = await page.locator('body').innerText()
  check('提交反馈', bodyText.includes('已提交') || bodyText.includes('等待管理员审核') || bodyText.includes('失败') || bodyText.includes('登录'),
    bodyText.split('\n').filter((l) => l.includes('提交') || l.includes('审核') || l.includes('登录')).slice(0, 3).join(' | '))

  // 5. 后端核验：用 admin token 查商家列表是否出现该申请
  const adminLogin = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@tanhui.example.com', password: 'Demo@123456' })
  }).then((r) => r.json())
  const token = adminLogin?.data?.access_token
  const merchants = await fetch(`${API}/admin/merchants`, { headers: { Authorization: `Bearer ${token}` } })
    .then((r) => r.json())
  const list = merchants?.data?.items || []
  const found = list.find((m) => m.company_name === company)
  check('后端入驻申请落库', Boolean(found), found ? `${found.company_name} status=${found.status} id=${found.id}` : `未找到，共${list.length}条`)

  fs.writeFileSync('scripts/flow-state.json', JSON.stringify({
    company, creditCode, phone, contact,
    merchantId: found?.id || '',
    status: found?.status || '',
    step1Ok: Boolean(found)
  }, null, 2))
  check('无页面异常', errors.length === 0, errors.slice(0, 2).join(' | '))
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 步骤1 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length && results.find((r) => r.name === '后端入驻申请落库')?.ok ? 0 : 1)
