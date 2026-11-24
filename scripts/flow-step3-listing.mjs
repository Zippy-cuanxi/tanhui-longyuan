/**
 * 流程步骤3：商家上架商品（4174 管理端商家端 UI → 后端 /merchant/products*）
 * 新建商品 → 提交审核（应进入 pending_review，不能直接上线）。
 * 更新 flow-state.json：productId(后端UUID), productMockId, productTitle。
 */
import { chromium } from 'playwright'
import fs from 'node:fs'

const CONSOLE = 'http://127.0.0.1:4174'
const API = 'http://127.0.0.1:8000/api/v1'
const state = JSON.parse(fs.readFileSync('scripts/flow-state.json', 'utf8'))
const STAMP = Date.now().toString().slice(-6)
const productTitle = `流程验证·静宁苹果${STAMP}`

const results = []
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${detail ? ' :: ' + detail : ''}`)
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
const apiCalls = []
page.on('pageerror', (e) => errors.push(e.message))
page.on('response', (res) => {
  if (res.url().includes(':8000/api/v1/merchant/products')) {
    apiCalls.push(`${res.request().method()} ${res.url().split('/api/v1')[1]} -> ${res.status()}`)
  }
})

try {
  // 1. 管理端登录（商家端）
  await page.goto(`${CONSOLE}/console/login`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '商家登录' }).click()
  await page.getByPlaceholder('请输入账号').fill('merchant01')
  await page.getByPlaceholder('请输入密码').fill('Demo@123456')
  await page.locator('form').press('Enter').catch(() => {})
  await page.getByRole('button', { name: /登.*录|登录/ }).first().click().catch(() => {})
  await page.waitForTimeout(1500)
  check('商家端登录', page.url().includes('/console/merchant/'), page.url())

  // 2. 打开发布商品页
  await page.goto(`${CONSOLE}/console/merchant/products/new`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  const h1 = await page.locator('h1, .console-page-title').first().innerText().catch(() => '')
  check('发布商品页可见', /发布商品|新增商品|编辑商品/.test(h1), h1)

  // 3. 填写商品表单（用通用 input/textarea 定位）
  const labels = await page.locator('.el-form-item__label').allInnerTexts().catch(() => [])
  console.log('FORM_LABELS', JSON.stringify(labels))

  // 逐项按 label 填
  async function fillByLabel(labelText, value) {
    const item = page.locator('.el-form-item').filter({ has: page.locator('.el-form-item__label', { hasText: labelText }) }).first()
    const field = item.locator('input, textarea').first()
    if (await field.count()) { await field.fill(value); return true }
    return false
  }
  await fillByLabel('商品名称', productTitle).catch(() => {})
  await fillByLabel('名称', productTitle).catch(() => {})
  await fillByLabel('副标题', '高原苹果 · 流程验证').catch(() => {})
  await fillByLabel('卖点', '高原苹果 · 流程验证').catch(() => {})

  // 用 DOM 直接设值兜底：把所有可见文本输入框依次尝试
  await page.evaluate((title) => {
    const inputs = [...document.querySelectorAll('.el-form input.el-input__inner, .el-form textarea')]
    const set = (el, v) => {
      const d = Object.getOwnPropertyDescriptor(el.__proto__, 'value')
      d.set.call(el, v)
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
    if (inputs[0]) set(inputs[0], title)
    if (inputs[1]) set(inputs[1], '高原苹果 · 流程验证')
  }, productTitle)

  // 分类下拉：选第一个
  const selects = page.locator('.el-select')
  if (await selects.count()) {
    await selects.first().click()
    await page.waitForTimeout(400)
    const opt = page.locator('.el-select-dropdown__item').first()
    if (await opt.count()) await opt.click()
  }

  // SKU：找价格/库存输入
  const formSnapshot = await page.evaluate(() => {
    return [...document.querySelectorAll('.el-form input, .el-form textarea')].map((el, i) => ({
      i, ph: el.getAttribute('placeholder') || '', val: el.value
    }))
  })
  console.log('FORM_FIELDS', JSON.stringify(formSnapshot.slice(0, 12)))

  // 按 placeholder 精确填写 SKU 规格 / 价格 / 库存 + 详情 + 产地
  await page.evaluate(() => {
    const set = (el, v) => {
      const d = Object.getOwnPropertyDescriptor(el.__proto__, 'value')
      d.set.call(el, v)
      el.dispatchEvent(new Event('input', { bubbles: true }))
      el.dispatchEvent(new Event('change', { bubbles: true }))
    }
    document.querySelectorAll('.el-form input, .el-form textarea').forEach((el) => {
      const ph = el.getAttribute('placeholder') || ''
      if (/例如：5kg/.test(ph)) set(el, '5kg 精选装')
      else if (ph === '0.00') set(el, '39.90')
      else if (/请描述产品产地/.test(ph)) set(el, '甘肃静宁高原苹果，脆甜多汁，流程验证商品。')
      else if (/甘肃省平凉/.test(ph)) set(el, '甘肃省平凉市静宁县')
      else if (/高原梯田/.test(ph)) set(el, '高原梯田果园种植')
      else if (/说明绿色种植/.test(ph)) set(el, '绿色种植，减少化肥使用。')
      else if (el.type === 'number' && /库存/.test(ph)) set(el, '100')
    })
  })
  // 库存字段（type=number，值0）
  const numberInputs = page.locator('.el-form input[type="number"]')
  const nCount = await numberInputs.count()
  for (let i = 0; i < nCount; i++) {
    await numberInputs.nth(i).fill('100').catch(() => {})
  }
  await page.waitForTimeout(400)
  const fieldsAfter = await page.evaluate(() =>
    [...document.querySelectorAll('.el-form input, .el-form textarea')].slice(0, 12).map((el) => el.value)
  )
  console.log('FIELDS_AFTER', JSON.stringify(fieldsAfter))

  // 选择商品图片：点"选择图片"打开素材对话框，选第一张
  await page.getByRole('button', { name: /选择图片/ }).first().click()
  await page.waitForTimeout(600)
  const dialogImgs = page.locator('.el-dialog img, .image-picker img, .console-image-grid img')
  const imgCount = await dialogImgs.count()
  console.log('DIALOG_IMG_COUNT', imgCount)
  if (imgCount) {
    await dialogImgs.first().click()
    await page.waitForTimeout(300)
  } else {
    // 兜底：点击对话框内第一个可点击素材项
    const items = page.locator('.el-dialog [class*="item"], .el-dialog [class*="thumb"]')
    if (await items.count()) await items.first().click()
  }
  // 关闭对话框（若有"确定/完成"按钮）
  const confirmImg = page.locator('.el-dialog button').filter({ hasText: /确定|完成|确认/ })
  if (await confirmImg.count()) await confirmImg.first().click()
  else await page.keyboard.press('Escape')
  await page.waitForTimeout(400)
  const chosenImgs = await page.locator('.console-upload-item img').count()
  console.log('CHOSEN_IMGS', chosenImgs)

  // 4. 点"提交审核"（不是"保存草稿"）
  const submitBtn = page.getByRole('button', { name: /提交审核/ }).first()
  const submitCount = await submitBtn.count()
  console.log('SUBMIT_BTN_COUNT', submitCount)
  if (!submitCount) throw new Error('未找到提交审核按钮')
  await submitBtn.click()
  await page.waitForTimeout(2500)
  console.log('API_CALLS', JSON.stringify(apiCalls))
  const errs = await page.locator('.el-form-item__error').allInnerTexts().catch(() => [])
  const toastText = await page.locator('.el-message').allInnerTexts().catch(() => [])
  console.log('FORM_ERRORS', JSON.stringify(errs))
  console.log('TOASTS', JSON.stringify(toastText))

  // 5. 后端核验：商品应存在且 status=pending_review（不能直接 approved/listed）
  const login = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@tanhui.example.com', password: 'Demo@123456' })
  }).then((r) => r.json())
  const token = login?.data?.access_token
  const products = await fetch(`${API}/admin/products?page=1&page_size=100`, {
    headers: { Authorization: `Bearer ${token}` }
  }).then((r) => r.json())
  const found = (products?.data?.items || []).find((p) => p.title === productTitle)
  check('商品落库', Boolean(found), found ? `${found.title} id=${found.id} status=${found.status} listed=${found.is_listed}` : '未找到')
  check('商品处于待审状态', found?.status === 'pending_review', `status=${found?.status}`)
  check('商品未绕过审批直接上架', found?.is_listed === false, `is_listed=${found?.is_listed}`)

  // 6. 消费者端此刻不应看到该商品（验证审批闸门有效）
  const consumerProducts = await fetch(`${API}/products?page=1&page_size=100`).then((r) => r.json())
  const consumerHas = (consumerProducts?.data?.items || []).some((p) => p.title === productTitle)
  check('消费者端暂不可见（审批闸门有效）', !consumerHas, consumerHas ? '不该出现却出现' : '未出现，正确')

  if (found) {
    state.productId = found.id
    state.productTitle = productTitle
    state.productStatus = found.status
    fs.writeFileSync('scripts/flow-state.json', JSON.stringify(state, null, 2))
  }
  check('无页面异常', errors.length === 0, errors.slice(0, 2).join(' | '))
} catch (err) {
  check('脚本执行', false, err instanceof Error ? err.message : String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 步骤3 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
