/**
 * 商品审核 → 消费者商城即时同步 功能测试。
 *
 * 前置：后端已启动（默认 http://127.0.0.1:8000），演示账号可用：
 *   管理员 admin@tanhui.example.com / Demo@123456
 *   商家   merchant1@tanhui.example.com / Passw0rd!123
 *
 * 运行：node scripts/verify-audit-mall-sync.mjs
 */
const BASE = (process.env.API_BASE || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')
const ADMIN = { email: 'admin@tanhui.example.com', password: 'Demo@123456' }
const MERCHANT = { email: 'merchant1@tanhui.example.com', password: 'Passw0rd!123' }

let passed = 0
const failures = []

function ok(name, condition, detail = '') {
  if (condition) {
    passed += 1
    console.log(`PASS  ${name}`)
  } else {
    failures.push(`${name}${detail ? `：${detail}` : ''}`)
    console.log(`FAIL  ${name}${detail ? `：${detail}` : ''}`)
  }
}

async function call(path, { method = 'GET', token, body, expect = 200 } = {}) {
  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  })
  const payload = await response.json().catch(() => null)
  if (response.status !== expect) {
    throw new Error(
      `${method} ${path} 期望 HTTP ${expect}，实际 ${response.status}：${JSON.stringify(payload)}`
    )
  }
  return payload?.data ?? payload
}

async function login(account) {
  const data = await call('/auth/login', { method: 'POST', body: account })
  return data.access_token
}

async function createPendingProduct(merchantToken, title) {
  const categories = await call('/categories')
  const category = categories[0]
  const product = await call('/merchant/products', {
    method: 'POST',
    token: merchantToken,
    body: {
      title,
      subtitle: '审核同步自动化测试',
      description: '用于验证审核通过后消费者商城即时展示。',
      category_id: category?.id || null,
      skus: [{ spec: '500g/袋', price: '19.90', initial_stock: 50 }]
    }
  })
  await call(`/merchant/products/${product.id}/submit`, { method: 'POST', token: merchantToken })
  return product
}

async function consumerList(keyword) {
  const page = await call(`/products?keyword=${encodeURIComponent(keyword)}&page_size=50&page=1`)
  return page.items || []
}

async function consumerDetail(id) {
  try {
    return await call(`/products/${id}`)
  } catch {
    return null
  }
}

async function version() {
  const data = await call('/catalog/version')
  return data.version
}

async function main() {
  const stamp = Date.now().toString(36)
  const approveTitle = `审核同步测试-通过-${stamp}`
  const rejectTitle = `审核同步测试-驳回-${stamp}`
  const removeTitle = `审核同步测试-下架-${stamp}`

  const adminToken = await login(ADMIN)
  const merchantToken = await login(MERCHANT)

  // ---------- 场景一：审核通过即时展示 ----------
  const approveProduct = await createPendingProduct(merchantToken, approveTitle)
  const beforeVersion = await version()
  ok('待审核商品不在商城列表', (await consumerList(approveTitle)).length === 0)
  ok('待审核商品详情不可访问', (await consumerDetail(approveProduct.id)) === null)

  const approved = await call(`/admin/products/${approveProduct.id}/audit`, {
    method: 'POST',
    token: adminToken,
    body: { action: 'approve' }
  })
  ok('审核通过接口返回已上架', approved.status === 'approved' && approved.is_listed === true)
  ok('审核通过同步状态为成功', approved.sync_status === 'success', approved.sync_message || '')

  const visible = await consumerList(approveTitle)
  ok(
    '审核通过后商城立即出现商品',
    visible.some((item) => item.id === approveProduct.id)
  )
  const detail = await consumerDetail(approveProduct.id)
  ok('审核通过后商品详情立即可见', Boolean(detail))
  ok('商城商品带价格与分类', Boolean(detail?.skus?.length))
  const categoryList = await call(
    `/products?category_id=${encodeURIComponent(detail?.category_id || '')}&page_size=100&page=1`
  )
  ok(
    '审核通过后对应分类列表可见',
    (categoryList.items || []).some((item) => item.id === approveProduct.id)
  )
  const newest = await call('/products?sort=created_desc&page_size=100&page=1')
  ok(
    '审核通过后新品列表可见',
    (newest.items || []).some((item) => item.id === approveProduct.id)
  )
  const afterVersion = await version()
  ok(
    '目录版本在审核通过后发生变化',
    afterVersion !== beforeVersion,
    `${beforeVersion} -> ${afterVersion}`
  )

  // ---------- 场景二：并发读取一致性 ----------
  const reads = await Promise.all(Array.from({ length: 10 }, () => consumerList(approveTitle)))
  ok(
    '多用户并发读取结果一致',
    reads.every((items) => items.filter((item) => item.id === approveProduct.id).length === 1)
  )

  // ---------- 场景三：重复/并发审核不会产生重复商品 ----------
  const approvals = await Promise.all(
    Array.from({ length: 5 }, () =>
      fetch(`${BASE}/admin/products/${approveProduct.id}/audit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${adminToken}`
        },
        body: JSON.stringify({ action: 'approve' })
      }).then((response) => response.status)
    )
  )
  ok(
    '重复审核被状态校验拦截（全部 409）',
    approvals.every((status) => status === 409),
    approvals.join(',')
  )
  ok(
    '并发重复审核未产生重复商品',
    (await consumerList(approveTitle)).filter((item) => item.id === approveProduct.id).length === 1
  )

  // ---------- 场景四：驳回商品不可见 ----------
  const rejectProduct = await createPendingProduct(merchantToken, rejectTitle)
  await call(`/admin/products/${rejectProduct.id}/audit`, {
    method: 'POST',
    token: adminToken,
    body: { action: 'reject', reason: '自动化测试驳回' }
  })
  ok('驳回商品不出现在商城列表', (await consumerList(rejectTitle)).length === 0)
  ok('驳回商品详情不可访问', (await consumerDetail(rejectProduct.id)) === null)

  // ---------- 场景五：已下架商品即时移除 ----------
  const removeProduct = await createPendingProduct(merchantToken, removeTitle)
  await call(`/admin/products/${removeProduct.id}/audit`, {
    method: 'POST',
    token: adminToken,
    body: { action: 'approve' }
  })
  ok('下架测试商品审核后可见', (await consumerList(removeTitle)).length === 1)
  const versionBeforeRemove = await version()
  await call(`/admin/products/${removeProduct.id}/audit`, {
    method: 'POST',
    token: adminToken,
    body: { action: 'remove', reason: '自动化测试下架' }
  })
  ok('平台下架后商城立即移除', (await consumerList(removeTitle)).length === 0)
  ok('平台下架后详情不可访问', (await consumerDetail(removeProduct.id)) === null)
  ok('下架后目录版本发生变化', (await version()) !== versionBeforeRemove)

  // ---------- 场景六：非上架状态全量过滤 ----------
  const hiddenStatuses = ['pending_review', 'rejected', 'removed']
  const hiddenIds = new Set()
  for (const status of hiddenStatuses) {
    const page = await call(`/admin/products?status=${status}&page_size=100`, { token: adminToken })
    for (const item of page.items || []) hiddenIds.add(item.id)
  }
  const consumerAll = await call('/products?page_size=100&page=1')
  const leaked = (consumerAll.items || []).filter((item) => hiddenIds.has(item.id))
  ok(
    '待审核/驳回/下架商品全部被商城过滤',
    leaked.length === 0,
    leaked.map((p) => p.title).join(',')
  )

  // 清理：把通过测试的商品下架，避免测试数据长期占用商城展示位
  await call(`/admin/products/${approveProduct.id}/audit`, {
    method: 'POST',
    token: adminToken,
    body: { action: 'remove', reason: '自动化测试清理' }
  }).catch(() => undefined)

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
