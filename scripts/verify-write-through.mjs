/**
 * 写穿透验证：管理端发货 → 后端状态变更 → 消费者物流可见
 * 前置：8000 后端 + 5174 dev server。
 */
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:5174'
const API = 'http://127.0.0.1:8000/api/v1'
const results = []
function check(name, ok, detail = '') {
  results.push({ ok })
  console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${detail ? ' :: ' + detail : ''}`)
}
async function apiJson(path, token) {
  const res = await fetch(`${API}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  return res.text().then((t) => { try { return JSON.parse(t) } catch { return null } })
}

// 后端基线：选一笔 paid 子单
const mLogin = await fetch(`${API}/auth/login`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'merchant1@tanhui.example.com', password: 'Passw0rd!123' })
}).then((r) => r.json())
const mToken = mLogin?.data?.access_token
const paidOrders = (await apiJson('/merchant/orders?status=paid', mToken))?.data?.items || []
const target = paidOrders[0]
check('找到真实待发货订单', Boolean(target), target ? `${target.store_order_no} / ${target.id}` : '无')

const trackingNo = 'SF' + Date.now().toString().slice(-10)
const carrier = '顺丰速运'

// 直接验证后端发货端点（证明管理端调用的同一端点可用且消费者可查）
const shipRes = await fetch(`${API}/merchant/orders/${target.id}/ship`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${mToken}` },
  body: JSON.stringify({ carrier, tracking_no: trackingNo })
})
const shipBody = await shipRes.text().then((t) => { try { return JSON.parse(t) } catch { return null } })
check('后端发货端点成功', shipRes.ok && shipBody?.code === 'OK', `HTTP ${shipRes.status}`)

const afterShip = await apiJson(`/merchant/orders/${target.id}`, mToken)
const status = afterShip?.data?.status
check('后端订单状态变为 shipped', status === 'shipped', `status=${status}`)

// 消费者端物流接口（需订单所属买家 token，按父订单 order_id 查）
// 订单可能属 seed 买家或仿真买家，逐一尝试直到查到（越权会返回 NOT_FOUND）
let logisticsRaw = ''
for (const email of ['buyer@tanhui.example.com', 'simbuyer1@tanhui.example.com', 'simbuyer2@tanhui.example.com', 'simbuyer3@tanhui.example.com']) {
  const login = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password: 'Passw0rd!123' })
  }).then((r) => r.json())
  const token = login?.data?.access_token
  if (!token) continue
  const res = await apiJson(`/logistics/${target.order_id}`, token)
  if (JSON.stringify(res).includes(trackingNo)) { logisticsRaw = JSON.stringify(res); break }
}
check('消费者物流接口含快递单号', logisticsRaw.includes(trackingNo), `tracking=${trackingNo}`)

// 管理端 UI：投影状态应同步（重新同步后该子单 status=shipped）
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage()
await page.goto(`${BASE}/console/login`, { waitUntil: 'networkidle' })
const projection = await page.evaluate(async (orderNo) => {
  const s = await import('/src/console/api/bridge/sync.ts')
  const c = await import('/src/console/api/bridge/client.ts')
  await c.linkBackend('admin')
  await s.syncFromBackend()
  const db = JSON.parse(localStorage.getItem('tanhui_console_db_v1') || '{}')
  const order = (db.orders || []).find((o) => o.orderNo === orderNo)
  return order ? { status: order.status, tracking: order.shipment?.trackingNo } : null
}, target.store_order_no).catch((e) => ({ error: e.message }))
check('管理端投影同步发货状态', projection?.status === 'shipped', JSON.stringify(projection))
await browser.close()

const passed = results.filter((r) => r.ok).length
console.log(`\n==== 汇总: ${passed}/${results.length} 通过 ====`)
process.exit(passed === results.length ? 0 : 1)
