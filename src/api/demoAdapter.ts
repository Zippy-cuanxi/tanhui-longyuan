/**
 * 静态演示适配器（GitHub Pages 专用）
 * ====================================
 * GitHub Pages 只能托管静态文件，无法运行 FastAPI 后端。
 * 当 VITE_STATIC_DEMO=1 时，request() 把请求转到本适配器：
 * - 所有 GET 从内置静态快照读取（public/demo-data.json 由 scripts/export_static_snapshot.py 生成，
 *   构建时通过 virtual:demo-snapshot 打包进 chunk，避免额外的 JSON 请求拖慢首屏）。
 * - 写操作（登录/加购/下单/支付/退款等）在 localStorage 中模拟，保证交互链可演示。
 * 数据为快照，非实时；如需真实后端请本地 npm run dev + 启动 8000 服务。
 */
import type {
  PageData,
  Product,
  ProductDetail,
  CartItem,
  Order,
  Preview,
  Address,
  TokenPair,
  AidProject
} from './types'
import type { MerchantApplyResult } from './index'
import demoSnapshot from 'virtual:demo-snapshot'
import { readPublishedProducts, type DemoPublishedProduct } from './demoCatalog'
import { COUPON_STORE } from '@/utils/couponWallet'

interface Snapshot {
  generated_at: string
  source: string
  categories: Array<Record<string, unknown>>
  stores: Array<Record<string, unknown>>
  products: Array<Record<string, unknown>>
  notices: Array<Record<string, unknown>>
  banners: Array<Record<string, unknown>>
  aid_projects: Array<Record<string, unknown>>
  point_catalog: Array<Record<string, unknown>>
  users: Array<Record<string, unknown>>
  addresses: Array<Record<string, unknown>>
  point_accounts: Array<Record<string, unknown>>
  orders: Array<Record<string, unknown>>
  refunds: Array<Record<string, unknown>>
  cms_config: Record<string, string>
}

let snap: Snapshot | null = null

/** 把站点根相对的图片路径（/images/...、/uploads/...）补上部署 base（GitHub Pages 子路径）。 */
function withBaseUrls<T>(value: T): T {
  const base = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
  const normalize = (v: string): string =>
    v
      .replace(/^\/uploads\/demo\/products\//, '/images/products/')
      .replace(/^\/uploads\/demo\/banners\//, '/images/banners/')
      .replace(/^\/uploads\/demo\/categories\//, '/assets/categories/')
  const fix = (v: unknown): unknown => {
    if (typeof v === 'string' && /^\/(images|assets|uploads)\//.test(v)) {
      return `${base}${normalize(v)}`
    }
    if (Array.isArray(v)) return v.map(fix)
    if (v && typeof v === 'object') {
      const out: Record<string, unknown> = {}
      Object.entries(v as Record<string, unknown>).forEach(([k, val]) => {
        out[k] = fix(val)
      })
      return out
    }
    return v
  }
  return fix(value) as T
}

function getSnapshot(): Promise<Snapshot> {
  if (!snap) snap = withBaseUrls<Snapshot>(demoSnapshot as unknown as Snapshot)
  return Promise.resolve(snap)
}

const DEMO_CART_KEY = 'tanhui_demo_cart'
const DEMO_ORDERS_KEY = 'tanhui_demo_orders'
const DEMO_APPLY_KEY = 'tanhui_demo_apply'
const DEMO_POINTS_KEY = 'tanhui_demo_points'
const DEMO_DONATIONS_KEY = 'tanhui_demo_donations'
const DEMO_TOKEN = 'demo.access.token'
const DEMO_REFRESH = 'demo.refresh.token'
const DEMO_USER_KEY = 'tanhui_demo_user'

function lsGet<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}
function lsSet(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* ignore */
  }
}
function uid(prefix = 'd'): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}
function money(v: number): string {
  return v.toFixed(2)
}

interface DemoPointTxn {
  id: string
  type: string
  amount: number
  balance_after: number
  source_type?: string | null
  source_id?: string | null
  note?: string | null
  created_at: string
}

interface DemoPointState {
  balance: number
  transactions: DemoPointTxn[]
}

/** 当前演示用户 ID（与快照 point_accounts 对齐）。 */
function demoUserId(s: Snapshot): string {
  const email = String(
    lsGet<{ email?: string }>(DEMO_USER_KEY, {}).email || s.users[0]?.email || ''
  )
  return String(s.users.find((u) => u.email === email)?.id || s.users[0]?.id || 'demo-user')
}

/** 积分账户保存在 localStorage，订单完成/助农资助/兑换都会持久化，刷新页面不丢失。 */
function demoPointState(s: Snapshot): DemoPointState {
  const existing = lsGet<DemoPointState | null>(DEMO_POINTS_KEY, null)
  if (existing && typeof existing.balance === 'number') {
    if (!Array.isArray(existing.transactions)) existing.transactions = []
    return existing
  }
  const userId = demoUserId(s)
  const seed = Number(s.point_accounts.find((p) => String(p.user_id) === userId)?.balance ?? 500)
  const state: DemoPointState = {
    balance: Number.isFinite(seed) ? seed : 500,
    transactions: []
  }
  lsSet(DEMO_POINTS_KEY, state)
  return state
}

function saveDemoPointState(state: DemoPointState): void {
  lsSet(DEMO_POINTS_KEY, state)
}

function addDemoPoints(
  s: Snapshot,
  amount: number,
  type: string,
  note: string,
  sourceType?: string,
  sourceId?: string
): DemoPointTxn {
  const state = demoPointState(s)
  state.balance = Math.max(0, state.balance + amount)
  const txn: DemoPointTxn = {
    id: uid('pt'),
    type,
    amount,
    balance_after: state.balance,
    source_type: sourceType || null,
    source_id: sourceId || null,
    note,
    created_at: new Date().toISOString()
  }
  state.transactions.unshift(txn)
  saveDemoPointState(state)
  return txn
}

function paginate<T>(items: T[], page = 1, page_size = 6): PageData<T> {
  const p = Math.max(1, Number(page) || 1)
  const ps = Math.max(1, Number(page_size) || 6)
  const total = items.length
  return {
    items: items.slice((p - 1) * ps, p * ps),
    pagination: { page: p, page_size: ps, total, total_pages: Math.max(1, Math.ceil(total / ps)) }
  }
}

function parsePath(path: string): { pathname: string; query: URLSearchParams } {
  const [pathname, qs = ''] = path.split('?')
  return { pathname, query: new URLSearchParams(qs) }
}

export async function demoRequest<T>(
  path: string,
  options: { method?: string; body?: unknown } = {}
): Promise<T> {
  const s = await getSnapshot()
  const { pathname, query } = parsePath(path)
  const method = (options.method || 'GET').toUpperCase()
  const body = (options.body || {}) as Record<string, unknown>

  // ---- 认证 ----
  if (pathname === '/auth/login' && method === 'POST') {
    const email = String(body.email || '')
    const tokenPair: TokenPair = {
      access_token: DEMO_TOKEN,
      refresh_token: DEMO_REFRESH,
      token_type: 'Bearer',
      expires_in: 86400
    }
    lsSet(DEMO_USER_KEY, { email, loggedIn: true })
    return tokenPair as unknown as T
  }
  if (pathname === '/auth/refresh' && method === 'POST') {
    return {
      access_token: DEMO_TOKEN,
      refresh_token: DEMO_REFRESH,
      token_type: 'Bearer',
      expires_in: 86400
    } as unknown as T
  }
  if (pathname === '/auth/logout') {
    localStorage.removeItem(DEMO_USER_KEY)
    return null as T
  }
  if (pathname === '/users/me') {
    const email = String(
      lsGet<{ email?: string }>(DEMO_USER_KEY, {}).email ||
        s.users[0]?.email ||
        'buyer@tanhui.example.com'
    )
    const user = s.users.find((u) => u.email === email) || s.users[0] || { id: uid(), email }
    return {
      user: { ...user, is_active: true, is_email_verified: true, mfa_enabled: false }
    } as unknown as T
  }

  // ---- 分类 ----
  if (pathname === '/categories' && method === 'GET') {
    return s.categories.map((c) => ({
      id: c.id,
      parent_id: c.parent_id || null,
      name: c.name,
      icon_url: c.icon_url || null,
      sort: Number(c.sort) || 0
    })) as unknown as T
  }

  // ---- 商品 ----
  function toProduct(p: Record<string, unknown>): Product {
    return {
      id: String(p.id),
      store_id: String(p.store_id),
      category_id: p.category_id ? String(p.category_id) : null,
      aid_project_id: null,
      title: String(p.title),
      subtitle: p.subtitle ? String(p.subtitle) : null,
      is_listed: true,
      created_at: String(p.created_at),
      min_price: p.min_price != null ? money(Number(p.min_price)) : null,
      cover_url: p.cover_url ? String(p.cover_url) : null,
      store_name: p.store_name ? String(p.store_name) : null
    }
  }
  /** 管理端分类名 → 消费者端分类（演示快照中个别命名不同）。 */
  const CATEGORY_ALIAS: Record<string, string> = { 甘味文创: '文创礼品' }
  function resolvePublishedCategoryId(name: string): string | null {
    const hit = s.categories.find((c) => String(c.name) === (CATEGORY_ALIAS[name] || name))
    return hit ? String(hit.id) : null
  }
  function toPublishedProduct(p: DemoPublishedProduct): Product {
    return {
      id: p.id,
      store_id: p.store_id,
      category_id: resolvePublishedCategoryId(p.category_name),
      aid_project_id: null,
      title: p.title,
      subtitle: p.subtitle,
      is_listed: true,
      created_at: p.created_at,
      min_price: money(p.min_price),
      cover_url: p.cover_url,
      store_name: p.store_name
    }
  }
  function toPublishedDetail(p: DemoPublishedProduct): ProductDetail {
    return {
      ...toPublishedProduct(p),
      description: p.description,
      status: 'approved',
      audit_reason: null,
      audited_at: p.created_at,
      skus: p.skus.map((sku) => ({
        id: sku.id,
        product_id: p.id,
        spec: sku.spec,
        code: sku.code,
        price: money(sku.price),
        is_active: true
      })),
      images: p.images
        .slice()
        .sort((a, b) => a.sort - b.sort)
        .map((img) => ({ id: img.id, url: img.url, sort: img.sort }))
    }
  }
  if (pathname === '/products' && method === 'GET') {
    // 快照 + 管理端审核通过后发布的商品；同名商品以快照为准，避免重复展示。
    const snapshotItems = s.products.map(toProduct)
    const snapshotTitles = new Set(snapshotItems.map((p) => p.title.trim()))
    const publishedItems = readPublishedProducts()
      .filter((p) => !snapshotTitles.has(p.title.trim()))
      .map(toPublishedProduct)
    let items = [...publishedItems, ...snapshotItems]
    const categoryId = query.get('category_id')
    const storeId = query.get('store_id')
    const keyword = (query.get('keyword') || '').trim().toLowerCase()
    const sort = query.get('sort')
    if (categoryId) items = items.filter((p) => p.category_id === categoryId)
    if (storeId) items = items.filter((p) => p.store_id === storeId)
    if (keyword) items = items.filter((p) => String(p.title).toLowerCase().includes(keyword))
    if (sort === 'price_asc')
      items = items.slice().sort((a, b) => Number(a.min_price || 0) - Number(b.min_price || 0))
    else
      items = items.slice().sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
    return paginate(
      items,
      Number(query.get('page') || 1),
      Number(query.get('page_size') || 6)
    ) as unknown as T
  }
  const productMatch = pathname.match(/^\/products\/([^/]+)$/)
  if (productMatch && method === 'GET') {
    const productId = decodeURIComponent(productMatch[1])
    const p = s.products.find((x) => x.id === productId)
    if (!p) {
      const published = readPublishedProducts().find((x) => x.id === productId)
      if (published) return toPublishedDetail(published) as unknown as T
      throw new Error('商品不存在')
    }
    const detail: ProductDetail = {
      ...toProduct(p),
      description: String(p.description || ''),
      status: 'approved',
      audit_reason: null,
      audited_at: null,
      skus: ((p.skus as Array<Record<string, unknown>>) || []).map((sku) => ({
        id: String(sku.id),
        product_id: String(p.id),
        spec: String(sku.spec),
        code: sku.code ? String(sku.code) : null,
        price: money(Number(sku.price)),
        is_active: true
      })),
      images: ((p.images as Array<Record<string, unknown>>) || []).map((img) => ({
        id: String(img.id),
        url: String(img.url),
        sort: Number(img.sort) || 0
      }))
    }
    return detail as unknown as T
  }

  // ---- 公告 / Banner / 助农 ----
  if (pathname === '/client/notices' && method === 'GET') {
    return s.notices.map((n) => ({
      id: n.id,
      title: n.title,
      content: n.content,
      published_at: n.published_at ? String(n.published_at).replace(' ', 'T') + 'Z' : null
    })) as unknown as T
  }
  if (pathname === '/client/banners' && method === 'GET') {
    return s.banners.map((b) => ({
      id: b.id,
      title: b.title,
      image_url: b.image_url,
      link_type: 'internal',
      link_url: b.link_url || '/products'
    })) as unknown as T
  }
  // ---- 助农项目：列表按分页结构返回，详情按单对象返回（与真实后端对齐）----
  function toAidProject(a: Record<string, unknown>): AidProject {
    return {
      id: String(a.id),
      cooperative_id: a.cooperative_id ? String(a.cooperative_id) : '',
      title: String(a.title),
      cover_url: a.cover_url ? String(a.cover_url) : null,
      description: a.description ? String(a.description) : null,
      goal_amount: a.goal_amount != null ? money(Number(a.goal_amount)) : null,
      raised_amount: money(Number(a.raised_amount)),
      status: String(a.status || 'published'),
      published_at: a.published_at ? String(a.published_at).replace(' ', 'T') + 'Z' : null
    }
  }
  if (pathname === '/aid/projects' && method === 'GET') {
    return paginate(
      (s.aid_projects || []).map(toAidProject),
      Number(query.get('page') || 1),
      Number(query.get('page_size') || 12)
    ) as unknown as T
  }
  const aidProjectMatch = pathname.match(/^\/aid\/projects\/([^/]+)$/)
  if (aidProjectMatch && method === 'GET') {
    const project = (s.aid_projects || []).find(
      (a) => String(a.id) === decodeURIComponent(aidProjectMatch[1])
    )
    if (!project) throw new Error('助农项目不存在或已下线')
    return toAidProject(project) as unknown as T
  }
  const greenMatch = pathname.match(/^\/green\/products\/([^/]+)$/)
  if (greenMatch && method === 'GET') {
    const greenId = decodeURIComponent(greenMatch[1])
    const p = s.products.find((x) => x.id === greenId)
    const published = p ? null : readPublishedProducts().find((x) => x.id === greenId) || null
    const g = (p?.green as Record<string, unknown> | undefined) || {}
    return {
      profile: {
        id: uid('g'),
        product_id: greenId,
        origin: String(g.origin || published?.origin || '甘肃'),
        planting_mode: g.planting_mode ? String(g.planting_mode) : published?.planting_mode || null,
        certifications: [],
        description: g.description ? String(g.description) : published?.green_description || null,
        status: 'approved'
      },
      carbon_assessment: {
        co2e_per_unit: '0.42',
        unit: 'kgCO2e',
        methodology: '仿真测算',
        verified: true,
        assessed_at: new Date().toISOString()
      }
    } as unknown as T
  }

  // ---- 购物车（localStorage 模拟）----
  if (pathname === '/cart' && method === 'GET') {
    const items = lsGet<CartItem[]>(DEMO_CART_KEY, [])
    const checked = items.filter((i) => i.checked)
    return {
      items,
      total_quantity: items.reduce((sum, i) => sum + i.quantity, 0),
      checked_subtotal: money(
        checked.reduce((sum, i) => sum + Number(i.current_price) * i.quantity, 0)
      )
    } as unknown as T
  }
  if (pathname === '/cart/items' && method === 'POST') {
    const skuId = String(body.sku_id || '')
    const quantity = Number(body.quantity) || 1
    let foundSku: Record<string, unknown> | undefined
    let parent: Record<string, unknown> | undefined
    for (const p of s.products) {
      const sku = ((p.skus as Array<Record<string, unknown>>) || []).find((x) => x.id === skuId)
      if (sku) {
        foundSku = sku
        parent = p
        break
      }
    }
    if (!foundSku || !parent) throw new Error('SKU不存在')
    const items = lsGet<CartItem[]>(DEMO_CART_KEY, [])
    const existing = items.find((i) => i.sku_id === skuId)
    if (existing) existing.quantity += quantity
    else
      items.push({
        id: uid('ci'),
        sku_id: skuId,
        product_id: String(parent.id),
        product_title: String(parent.title),
        spec: String(foundSku.spec),
        image_url: (parent.cover_url as string) || null,
        current_price: money(Number(foundSku.price)),
        quantity,
        checked: true,
        stock_available: 500,
        store_id: String(parent.store_id),
        store_name: String(parent.store_name || '')
      })
    lsSet(DEMO_CART_KEY, items)
    return items[items.length - 1] as unknown as T
  }
  const cartItemMatch = pathname.match(/^\/cart\/items\/([^/]+)$/)
  if (cartItemMatch) {
    const items = lsGet<CartItem[]>(DEMO_CART_KEY, [])
    const idx = items.findIndex((i) => i.id === decodeURIComponent(cartItemMatch[1]))
    if (method === 'DELETE') {
      if (idx >= 0) items.splice(idx, 1)
    }
    if (method === 'PATCH' && idx >= 0) {
      if (body.quantity != null) items[idx].quantity = Math.max(1, Number(body.quantity))
      if (body.checked != null) items[idx].checked = Boolean(body.checked)
    }
    lsSet(DEMO_CART_KEY, items)
    return (idx >= 0 ? items[idx] : null) as unknown as T
  }

  // ---- 地址 ----
  function myAddresses(): Address[] {
    const email = String(
      lsGet<{ email?: string }>(DEMO_USER_KEY, {}).email || s.users[0]?.email || ''
    )
    const uidCur = s.users.find((u) => u.email === email)?.id || s.users[0]?.id
    return s.addresses
      .filter((a) => a.user_id === uidCur)
      .map((a) => ({
        id: String(a.id),
        receiver: String(a.receiver),
        phone: String(a.phone),
        province: String(a.province),
        city: String(a.city),
        district: a.district ? String(a.district) : null,
        detail: String(a.detail),
        is_default: Boolean(a.is_default)
      }))
  }
  if (pathname === '/users/me/addresses' && method === 'GET') return myAddresses() as unknown as T
  if (pathname === '/users/me/addresses' && method === 'POST') {
    const a = { id: uid('addr'), ...body, is_default: false } as Address
    const all = lsGet<Address[]>('tanhui_demo_addresses', myAddresses())
    all.push(a)
    lsSet('tanhui_demo_addresses', all)
    return a as unknown as T
  }

  // ---- 积分 ----
  if (pathname === '/points/account' && method === 'GET') {
    const state = demoPointState(s)
    const earned = state.transactions
      .filter((t) => t.amount > 0)
      .reduce((sum, t) => sum + t.amount, 0)
    const spent = state.transactions
      .filter((t) => t.amount < 0)
      .reduce((sum, t) => sum + Math.abs(t.amount), 0)
    return {
      balance: state.balance,
      total_earned: earned,
      total_spent: spent,
      updated_at: new Date().toISOString()
    } as unknown as T
  }
  if (pathname === '/points/transactions' && method === 'GET') {
    const type = query.get('type_')
    const items = demoPointState(s).transactions.filter((t) => !type || t.type === type)
    return paginate(
      items,
      Number(query.get('page') || 1),
      Number(query.get('page_size') || 20)
    ) as unknown as T
  }
  if (pathname === '/points/redemption-catalog' && method === 'GET')
    return s.point_catalog as unknown as T

  // ---- 订单 ----
  function allOrders(): Order[] {
    const extra = lsGet<Order[]>(DEMO_ORDERS_KEY, [])
    const base = s.orders.map((o) => ({
      ...o,
      store_orders: ((o.store_orders as Array<Record<string, unknown>>) || []).map((so) => ({
        ...so,
        items: (so.items as unknown[]) || []
      }))
    })) as unknown as Order[]
    return [...extra, ...base]
  }
  if (pathname === '/orders/preview' && method === 'POST') {
    const items = (body.items as Array<{ sku_id: string; quantity: number }>) || []
    const previewItems = items.map((it) => {
      let sku: Record<string, unknown> | undefined
      let parent: Record<string, unknown> | undefined
      for (const p of s.products) {
        const found = ((p.skus as Array<Record<string, unknown>>) || []).find(
          (x) => x.id === it.sku_id
        )
        if (found) {
          sku = found
          parent = p
          break
        }
      }
      const unit = Number(sku?.price || 0)
      return {
        sku_id: it.sku_id,
        title: String(parent?.title || ''),
        spec: String(sku?.spec || ''),
        unit_price: money(unit),
        quantity: it.quantity,
        subtotal: money(unit * it.quantity)
      }
    })
    const itemsTotal = previewItems.reduce((sum, i) => sum + Number(i.subtotal), 0)
    const shipping = itemsTotal >= 99 ? 0 : 8
    const usePoints = Boolean(body.use_points)
    const pointsDeduct = usePoints ? Math.min(10, itemsTotal) : 0
    const groupBy = new Map<string, typeof previewItems>()
    previewItems.forEach((i) => {
      const p = s.products.find((x) =>
        ((x.skus as Array<Record<string, unknown>>) || []).some((sk) => sk.id === i.sku_id)
      )
      const sid = String(p?.store_id || 'store')
      if (!groupBy.has(sid)) groupBy.set(sid, [])
      groupBy.get(sid)!.push(i)
    })
    const stores = Array.from(groupBy.entries()).map(([storeId, its]) => {
      const sub = its.reduce((sum, i) => sum + Number(i.subtotal), 0)
      return {
        store_id: storeId,
        store_name: String(s.products.find((x) => x.store_id === storeId)?.store_name || ''),
        items_total: money(sub),
        shipping_fee: money(sub >= 99 ? 0 : 8),
        items: its
      }
    })
    return {
      items_total: money(itemsTotal),
      shipping_fee: money(shipping),
      points_deduct: money(pointsDeduct),
      points_used: usePoints ? 1000 : 0,
      pay_amount: money(itemsTotal + shipping - pointsDeduct),
      stores
    } as unknown as T
  }
  if (pathname === '/orders' && method === 'POST') {
    const extra = lsGet<Order[]>(DEMO_ORDERS_KEY, [])
    const addr = myAddresses().find((a) => a.id === body.address_id) || myAddresses()[0]
    const items = (body.items as Array<{ sku_id: string; quantity: number }>) || []
    const preview = await demoRequest<Preview>('/orders/preview', {
      method: 'POST',
      body: { items, use_points: Boolean(body.use_points) }
    })
    const order: Order = {
      id: uid('o'),
      order_no: `SIM-TH${Date.now()}`,
      status: 'pending_payment',
      receiver_name: addr.receiver,
      receiver_phone: addr.phone,
      address: `${addr.province}${addr.city}${addr.district || ''}${addr.detail}`,
      items_total: preview.items_total,
      shipping_fee: preview.shipping_fee,
      points_deduct: preview.points_deduct,
      points_used: preview.points_used,
      pay_amount: preview.pay_amount,
      currency: 'CNY',
      remark: body.remark ? String(body.remark) : null,
      cancel_reason: null,
      paid_at: null,
      completed_at: null,
      cancelled_at: null,
      created_at: new Date().toISOString(),
      store_orders: preview.stores.map((st) => ({
        id: uid('so'),
        store_order_no: `SIM-TS${Date.now()}`,
        store_id: st.store_id,
        status: 'pending_payment',
        items_total: st.items_total,
        shipping_fee: st.shipping_fee,
        pay_amount: money(Number(st.items_total) + Number(st.shipping_fee)),
        refund_amount: '0.00',
        shipped_at: null,
        completed_at: null,
        items: st.items.map((it) => ({
          id: uid('oi'),
          sku_id: it.sku_id,
          product_id: String(
            s.products.find((x) =>
              ((x.skus as Array<Record<string, unknown>>) || []).some((sk) => sk.id === it.sku_id)
            )?.id || ''
          ),
          title: it.title,
          spec: it.spec,
          image_url: null,
          unit_price: it.unit_price,
          quantity: it.quantity,
          subtotal: it.subtotal
        }))
      }))
    }
    extra.unshift(order)
    lsSet(DEMO_ORDERS_KEY, extra)
    lsSet(DEMO_CART_KEY, [])
    return order as unknown as T
  }
  if (pathname === '/orders' && method === 'GET') {
    const status = query.get('status')
    let items = allOrders().map(demoOrderPoints)
    if (status && status !== 'all') items = items.filter((o) => o.status === status)
    items = items.slice().sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
    return paginate(
      items,
      Number(query.get('page') || 1),
      Number(query.get('page_size') || 10)
    ) as unknown as T
  }
  function demoOrderPoints(o: Order): Order {
    const estimate = Math.max(0, Math.floor(Number(o.pay_amount) || 0))
    const txn = demoPointState(s).transactions.find(
      (t) => t.source_type === 'order_completion' && t.source_id === o.id
    )
    const earned = txn ? txn.amount : o.status === 'completed' ? estimate : 0
    return { ...o, points_estimate: estimate, points_earned: earned }
  }

  const orderMatch = pathname.match(/^\/orders\/([^/]+)$/)
  if (orderMatch && method === 'GET') {
    const o = allOrders().find((x) => x.id === decodeURIComponent(orderMatch[1]))
    if (!o) throw new Error('订单不存在')
    return demoOrderPoints(o) as unknown as T
  }
  const orderCancel = pathname.match(/^\/orders\/([^/]+)\/cancel$/)
  if (orderCancel && method === 'POST') {
    const extra = lsGet<Order[]>(DEMO_ORDERS_KEY, [])
    const o = extra.find((x) => x.id === decodeURIComponent(orderCancel[1]))
    if (o) {
      o.status = 'cancelled'
      o.cancel_reason = String(body.reason || '用户取消')
      o.cancelled_at = new Date().toISOString()
      lsSet(DEMO_ORDERS_KEY, extra)
    }
    return (o || null) as unknown as T
  }
  const orderConfirm = pathname.match(/^\/orders\/([^/]+)\/confirm-receipt$/)
  if (orderConfirm && method === 'POST') {
    const orderId = decodeURIComponent(orderConfirm[1])
    const extra = lsGet<Order[]>(DEMO_ORDERS_KEY, [])
    const o = extra.find((x) => x.id === orderId)
    if (!o) {
      const base = allOrders().find((x) => x.id === orderId)
      if (base) return demoOrderPoints({ ...base, status: 'completed' }) as unknown as T
      throw new Error('订单不存在')
    }
    const now = new Date().toISOString()
    o.status = 'completed'
    o.completed_at = now
    o.store_orders.forEach((so) => {
      so.status = 'completed'
      so.completed_at = now
    })
    const estimate = Math.max(0, Math.floor(Number(o.pay_amount) || 0))
    const existed = demoPointState(s).transactions.find(
      (t) => t.source_type === 'order_completion' && t.source_id === o.id
    )
    const earned = existed
      ? existed.amount
      : addDemoPoints(s, estimate, 'earn', `订单 ${o.order_no} 完成发放`, 'order_completion', o.id)
          .amount
    lsSet(DEMO_ORDERS_KEY, extra)
    return { ...o, points_estimate: estimate, points_earned: earned } as unknown as T
  }
  const refundMatch = pathname.match(/^\/orders\/([^/]+)\/refunds$/)
  if (refundMatch && method === 'POST') {
    return {
      id: uid('rf'),
      order_id: decodeURIComponent(refundMatch[1]),
      amount: String(body.amount || '0.00'),
      reason: String(body.reason || ''),
      status: 'requested',
      created_at: new Date().toISOString()
    } as unknown as T
  }
  if (refundMatch && method === 'GET') return [] as unknown as T

  // ---- 支付 ----
  const payInit = pathname.match(/^\/payments\/([^/]+)\/init$/)
  if (payInit && method === 'POST') {
    return {
      id: uid('pay'),
      pay_no: `PAY${Date.now()}`,
      order_id: decodeURIComponent(payInit[1]),
      amount: '0.00',
      currency: 'CNY',
      status: 'pending',
      provider: 'mock_sandbox',
      expires_at: new Date(Date.now() + 1800000).toISOString()
    } as unknown as T
  }
  if (pathname === '/payments/mock/pay' && method === 'POST') {
    // 把本地新单标记为已支付，并按 1 元 = 1 积分发放（幂等）
    const extra = lsGet<Order[]>(DEMO_ORDERS_KEY, [])
    extra.forEach((o) => {
      if (o.status === 'pending_payment') {
        o.status = 'paid'
        o.paid_at = new Date().toISOString()
        o.store_orders.forEach((so) => {
          so.status = 'paid'
        })
        const existed = demoPointState(s).transactions.find(
          (t) => t.source_type === 'order_completion' && t.source_id === o.id
        )
        if (!existed) {
          const points = Math.max(0, Math.floor(Number(o.pay_amount) || 0))
          addDemoPoints(
            s,
            points,
            'earn',
            `订单 ${o.order_no} 支付成功发放`,
            'order_completion',
            o.id
          )
        }
      }
    })
    lsSet(DEMO_ORDERS_KEY, extra)
    return { status: 'success', paid_at: new Date().toISOString() } as unknown as T
  }

  // ---- 物流 ----
  const logisticsMatch = pathname.match(/^\/logistics\/([^/]+)$/)
  if (logisticsMatch && method === 'GET') {
    const oid = decodeURIComponent(logisticsMatch[1])
    const all = allOrders()
    const o = all.find((x) => x.id === oid)
    const shipments: Array<Record<string, unknown>> = []
    o?.store_orders.forEach((so) => {
      const sh = (so as unknown as Record<string, unknown>).shipments as
        Array<Record<string, unknown>> | undefined
      if (sh) shipments.push(...sh)
    })
    return shipments as unknown as T
  }

  // ---- 通知 ----
  if (pathname === '/notifications' && method === 'GET') return [] as unknown as T
  if (pathname === '/notifications/read-all' && method === 'POST') return null as T

  // ---- 入驻申请 ----
  if (pathname === '/merchant/apply' && method === 'POST') {
    const result: MerchantApplyResult = {
      id: uid('m'),
      status: 'pending_review',
      company_name: String(body.company_name || ''),
      store_name: String(body.store_name || '')
    }
    const existing = lsGet<MerchantApplyResult[]>(DEMO_APPLY_KEY, [])
    existing.push(result)
    lsSet(DEMO_APPLY_KEY, existing)
    return result as unknown as T
  }
  if (pathname === '/merchant/merchants/me' && method === 'GET')
    return lsGet<MerchantApplyResult[]>(DEMO_APPLY_KEY, []) as unknown as T

  // ---- 助农捐赠 / 积分兑换（模拟并持久化到 localStorage）----
  if (pathname === '/aid/donations/me' && method === 'GET')
    return lsGet<Array<Record<string, unknown>>>(DEMO_DONATIONS_KEY, []) as unknown as T
  if (pathname.match(/^\/aid\/projects\/[^/]+\/donations$/) && method === 'GET') {
    const projectId = decodeURIComponent(pathname.split('/')[3] || '')
    const items = lsGet<Array<Record<string, unknown>>>(DEMO_DONATIONS_KEY, [])
      .filter((d) => String(d.project_id) === projectId)
      .map((d) => ({
        id: d.id,
        donor: d.display_mode === 'named' ? d.display_name || '爱心人士' : '匿名爱心人士',
        display_mode: d.display_mode,
        amount: d.amount,
        created_at: d.created_at
      }))
    return items as unknown as T
  }
  if (pathname.match(/^\/aid\/projects\/[^/]+\/donations$/) && method === 'POST') {
    const projectId = decodeURIComponent(pathname.split('/')[3] || '')
    const amount = Number(body.amount)
    if (!Number.isFinite(amount) || amount <= 0) {
      throw new Error('请输入有效的资助金额')
    }
    const project = s.aid_projects.find((p) => String(p.id) === projectId)
    const points = Math.floor(amount * 3)
    const donation = {
      id: uid('don'),
      project_id: projectId,
      project_title: String(project?.title || '助农项目'),
      amount: money(amount),
      points_earned: points,
      display_mode: body.display_mode === 'named' ? 'named' : 'anonymous',
      display_name: body.display_name ? String(body.display_name) : null,
      created_at: new Date().toISOString()
    }
    const all = lsGet<Array<Record<string, unknown>>>(DEMO_DONATIONS_KEY, [])
    all.unshift(donation)
    lsSet(DEMO_DONATIONS_KEY, all)
    const txn = addDemoPoints(
      s,
      points,
      'earn',
      `资助助农项目获得 ${points} 绿色积分`,
      'aid_donation',
      donation.id
    )
    return { ...donation, balance: txn.balance_after } as unknown as T
  }
  // 兼容旧版 /donate 路径
  if (pathname.match(/^\/aid\/projects\/[^/]+\/donate$/) && method === 'POST') {
    return { id: uid('don'), points_earned: 10, mock: true } as unknown as T
  }
  if (pathname === '/points/redemptions' && method === 'POST') {
    const code = String(body.reward_code || '')
    const reward = s.point_catalog.find((r) => String(r.reward_code) === code)
    const storeItem = COUPON_STORE.find((item) => item.reward_code === code)
    const cost = Number(storeItem?.points ?? reward?.points ?? 500)
    if (demoPointState(s).balance < cost) {
      const error = new Error('绿色积分余额不足') as Error & { code?: string }
      error.code = 'POINTS_INSUFFICIENT'
      throw error
    }
    const txn = addDemoPoints(
      s,
      -cost,
      'spend',
      `兑换「${String(storeItem?.coupon.title || reward?.name || code)}」`,
      'redemption'
    )
    return {
      reward_code: code,
      reward_name: String(storeItem?.coupon.title || reward?.name || '演示权益'),
      points_spent: cost,
      voucher_code: 'DEMO-2026',
      balance: txn.balance_after,
      mock: true
    } as unknown as T
  }
  if (pathname === '/auth/sessions' && method === 'GET') return [] as unknown as T
  if (pathname === '/auth/sessions/revoke-all' && method === 'POST') return null as T

  // 未覆盖的 GET 返回空集合，写操作返回 null（避免页面崩溃）
  if (method === 'GET') {
    if (
      pathname.includes('notices') ||
      pathname.includes('list') ||
      pathname.includes('transactions')
    ) {
      return paginate([], 1, 20) as unknown as T
    }
    return [] as unknown as T
  }
  return null as T
}
