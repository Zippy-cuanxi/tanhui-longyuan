/**
 * 消费者端实时刷新 UI 测试（真实后端）。
 *
 * 前置：
 *   1. 后端：http://127.0.0.1:8000
 *   2. 前端：http://127.0.0.1:5173
 *
 * 场景：消费者页面保持打开 → 外部管理员审核通过新商品 → 无需刷新自动出现。
 * 运行：node scripts/verify-catalog-live-ui.mjs
 */
import { chromium } from 'playwright'

const API = 'http://127.0.0.1:8000/api/v1'
const WEB = 'http://127.0.0.1:5173'
const ADMIN = { email: 'admin@tanhui.example.com', password: 'Demo@123456' }
const MERCHANT = { email: 'merchant1@tanhui.example.com', password: 'Passw0rd!123' }

async function api(path, { method = 'GET', token, body } = {}) {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(`${method} ${path} 失败（HTTP ${response.status}）：${JSON.stringify(payload)}`)
  }
  return payload?.data ?? payload
}

async function login(account) {
  return (await api('/auth/login', { method: 'POST', body: account })).access_token
}

let passed = 0
const failures = []
function check(name, condition, detail = '') {
  if (condition) {
    passed += 1
    console.log(`PASS  ${name}`)
  } else {
    failures.push(`${name}${detail ? `：${detail}` : ''}`)
    console.log(`FAIL  ${name}${detail ? `：${detail}` : ''}`)
  }
}

async function main() {
  const adminToken = await login(ADMIN)
  const merchantToken = await login(MERCHANT)
  const title = `实时刷新测试-${Date.now().toString(36)}`
  const categories = await api('/categories')
  const product = await api('/merchant/products', {
    method: 'POST',
    token: merchantToken,
    body: {
      title,
      subtitle: '消费者端无需刷新自动展示',
      description: '用于验证审核通过后消费者端实时刷新。',
      category_id: categories[0]?.id || null,
      skus: [{ spec: '1kg', price: '29.90', initial_stock: 30 }]
    }
  })
  await api(`/merchant/products/${product.id}/submit`, {
    method: 'POST',
    token: merchantToken
  })

  const browser = await chromium.launch()
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', (error) => errors.push(String(error)))
  page.on('console', (message) => {
    // 新商品可能暂无绿色资料，/green/products/:id 返回 404 属于预期业务分支；
    // 这里只拦截真正的脚本异常与接口错误。
    if (message.type() === 'error' && !message.text().startsWith('Failed to load resource')) {
      errors.push(message.text())
    }
  })

  try {
    await page.goto(`${WEB}/products?keyword=${encodeURIComponent(title)}`, {
      waitUntil: 'networkidle'
    })
    await page.waitForTimeout(600)
    check(
      '审核前消费者端无该商品',
      (await page.locator('.product-card', { hasText: title }).count()) === 0
    )

    await api(`/admin/products/${product.id}/audit`, {
      method: 'POST',
      token: adminToken,
      body: { action: 'approve' }
    })

    const started = Date.now()
    await page.locator('.product-card', { hasText: title }).first().waitFor({ timeout: 12000 })
    check('审核通过后无需刷新自动展示', true, `${Date.now() - started}ms`)
    check('过程中无页面异常', errors.length === 0, errors.slice(0, 3).join(' | '))

    // 清理：下架测试商品
    await api(`/admin/products/${product.id}/audit`, {
      method: 'POST',
      token: adminToken,
      body: { action: 'remove', reason: '自动化 UI 测试清理' }
    }).catch(() => undefined)
  } finally {
    await browser.close()
  }

  console.log(`\n结果：${passed} 项通过，${failures.length} 项失败`)
  if (failures.length) {
    console.log(failures.map((item) => ` - ${item}`).join('\n'))
    process.exitCode = 1
  }
}

main().catch((error) => {
  console.error('测试执行失败：', error)
  process.exitCode = 1
})
