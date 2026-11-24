/**
 * 后端 → 管理端的权威数据投影。
 *
 * 负责把真实后端实体（订单、商品、退款、公告、商家、店铺、分类）拉取并映射后，
 * 合并进管理端 localStorage 数据源，使管理端页面看到消费者端真实产生的数据。
 *
 * 合并策略：
 * - 后端实体通过 ID 映射成稳定 mockId；若 mock 中已存在同 ID 记录，则用后端权威字段覆盖，
 *   但保留 mock 独有字段（如 greenProfile/stock/sales/auditRecords 等）。
 * - 后端拉不到的实体不删除 mock 演示数据，保证演示体验。
 */
import { getDb, saveDb } from '@/console/mock/db'
import { bridgeRequest, linkBackend, unwrap } from './client'
import { mockIdFor, uuidFor } from './identity'
export { uuidFor as toUuid }
import {
  mapAftersale,
  mapAnnouncement,
  mapCategory,
  mapMerchant,
  mapOrder,
  mapProduct
} from './mappers'
export interface SyncReport {
  ok: boolean
  at: string
  products: number
  orders: number
  aftersales: number
  announcements: number
  categories: number
  merchants: number
  error?: string
}

interface Envelope<T> {
  data?: T
  code?: string
}
interface Page<T> {
  items: T[]
  pagination?: { total?: number }
}

async function pullList<T>(
  path: string,
  role: 'admin' | 'merchant'
): Promise<T[]> {
  const result = await bridgeRequest<Envelope<Page<T>> | Page<T>>(path, { role })
  if (!result.ok || !result.data) return []
  const env = result.data as Envelope<Page<T>>
  if (env.data && Array.isArray(env.data.items)) return env.data.items
  if (Array.isArray((result.data as Page<T>).items)) return (result.data as Page<T>).items
  if (Array.isArray(result.data)) return result.data as unknown as T[]
  return []
}

function upsert<T extends { id: string }>(list: T[], incoming: T): void {
  const index = list.findIndex((item) => item.id === incoming.id)
  if (index >= 0) list[index] = incoming
  else list.unshift(incoming)
}

/** 拉取后端权威数据并合并进管理端数据源。 */
export async function syncFromBackend(): Promise<SyncReport> {
  const report: SyncReport = {
    ok: false,
    at: new Date().toISOString(),
    products: 0,
    orders: 0,
    aftersales: 0,
    announcements: 0,
    categories: 0,
    merchants: 0
  }
  // 同步统一用管理员令牌拉取 /admin/* 权威数据（与商家端的 merchant 令牌互不干扰）
  const adminToken = await linkBackend('admin')
  if (!adminToken) {
    report.error = '后端管理员认证不可用'
    return report
  }
  const db = getDb()

  try {
    // --- 店铺与商家：建立 storeName / merchantId 关联 ---
    const storesResult = await bridgeRequest<Envelope<Page<Record<string, unknown>> | Array<Record<string, unknown>>>>(
      '/admin/stores',
      { role: 'admin' }
    )
    const storesPayload = unwrap(storesResult)
    const stores: Array<Record<string, unknown>> = Array.isArray(storesPayload)
      ? storesPayload
      : (storesPayload as Page<Record<string, unknown>>)?.items || []
    const storeNameById = new Map<string, string>()
    const merchantIdByStore = new Map<string, string>()
    const demoMerchantId = db.merchants[0]?.id || 'm01'
    stores.forEach((store) => {
      const sid = String(store.id || '')
      storeNameById.set(sid, String(store.name || '陇原甄选旗舰店'))
      // 后端真实店铺统一归属到演示商家账号 merchant01(m01)，使商家端可见真实数据
      merchantIdByStore.set(sid, demoMerchantId)
      // 同步店铺到 mock（保留 mock 独有字段）
      const mockSid = mockIdFor(sid, 's')
      const existing = db.stores.find((s) => s.id === mockSid)
      if (existing) {
        existing.name = String(store.name || existing.name)
        existing.region = String(store.region || existing.region)
        existing.description = String(store.description || existing.description)
        existing.status = store.status === 'active' ? 'active' : 'suspended'
      }
    })

    // --- 商家（入驻申请/审核实体）---
    const merchants = await pullList<Record<string, unknown>>(
      '/admin/merchants?page=1&page_size=100',
      'admin'
    )
    merchants.forEach((raw) => {
      const mapped = mapMerchant(raw, {})
      const existing = db.merchants.find((m) => m.id === mapped.id)
      if (existing) {
        existing.companyName = mapped.companyName
        existing.storeName = mapped.storeName || existing.storeName
        existing.ownerName = mapped.ownerName || existing.ownerName
        existing.phone = mapped.phone || existing.phone
        existing.region = mapped.region || existing.region
        existing.licenseNo = mapped.licenseNo || existing.licenseNo
        existing.status = mapped.status
        existing.rejectReason = mapped.rejectReason
        existing.reviewedAt = mapped.reviewedAt
      } else {
        db.merchants.unshift(mapped)
      }
      report.merchants += 1
    })

    // --- 商品 ---
    const products = await pullList<Record<string, unknown>>(
      '/admin/products?page=1&page_size=100',
      'admin'
    )
    products.forEach((raw) => {
      // 后端商品归属演示商家 m01，使商家端（merchant01）可见真实商品
      const mapped = mapProduct(raw, { merchantId: demoMerchantId, storeName: storeNameById.get(String(raw.store_id || '')) || '' })
      const existing = db.products.find((p) => p.title === mapped.title && p.id.startsWith('p'))
      if (existing) {
        // 保留 mock 独有字段，覆盖后端权威字段
        existing.title = mapped.title
        existing.subtitle = mapped.subtitle || existing.subtitle
        existing.description = mapped.description || existing.description
        existing.price = mapped.price
        existing.minPrice = mapped.minPrice
        existing.status = mapped.status
        existing.listed = mapped.listed
        existing.cover = mapped.cover || existing.cover
        existing.categoryId = mapped.categoryId || existing.categoryId
        existing.storeName = mapped.storeName || existing.storeName
        if (mapped.images.length) existing.images = mapped.images
        if (mapped.skus.length) {
          existing.skus = existing.skus.map((sku, i) =>
            mapped.skus[i] ? { ...sku, price: mapped.skus[i].price, spec: mapped.skus[i].spec } : sku
          )
        }
      } else {
        db.products.unshift(mapped)
      }
      report.products += 1
    })

    // --- 分类 ---
    const categories = await pullList<Record<string, unknown>>('/categories', 'admin')
    categories.forEach((raw) => {
      const mockId = mockIdFor(String(raw.id), 'cat')
      const existing = db.categories.find((c) => c.id === mockId)
      const mapped = mapCategory(raw)
      if (existing) {
        existing.name = mapped.name
        existing.sort = mapped.sort
      } else {
        db.categories.push(mapped)
      }
      report.categories += 1
    })

    // --- 订单：列表 + 逐单详情（含收货人/明细） ---
    const orderList = await pullList<Record<string, unknown>>(
      '/admin/orders?page=1&page_size=100',
      'admin'
    )
    for (const brief of orderList.slice(0, 40)) {
      const oid = String(brief.id || '')
      const detailResult = await bridgeRequest<Envelope<{ store_orders?: Record<string, unknown>[] }>>(
        `/admin/orders/${oid}`,
        { role: 'admin' }
      )
      const detail = unwrap(detailResult) as { store_orders?: Record<string, unknown>[] } | null
      const children = detail?.store_orders?.length
        ? detail.store_orders
        : [{ ...brief, id: oid, order_no: brief.order_no }]
      for (const child of children) {
        const sid = String(child.store_id || '')
        const storeName = storeNameById.get(sid) || '陇原甄选旗舰店'
        const merchantId = merchantIdByStore.get(sid) || db.merchants[0]?.id || ''
        const mapped = mapOrder(child, storeName, merchantId, 'r')
        const existing = db.orders.find((o) => o.id === mapped.id)
        if (existing) {
          existing.orderNo = mapped.orderNo
          existing.status = mapped.status
          existing.payAmount = mapped.payAmount
          existing.itemsTotal = mapped.itemsTotal
          existing.shippingFee = mapped.shippingFee
          existing.refundAmount = mapped.refundAmount
          existing.shipment = mapped.shipment || existing.shipment
          existing.shippedAt = mapped.shippedAt || existing.shippedAt
          existing.buyerName = mapped.buyerName || existing.buyerName
          existing.address = mapped.address || existing.address
          existing.items = mapped.items.length ? mapped.items : existing.items
          existing.createdAt = mapped.createdAt
        } else {
          db.orders.unshift(mapped)
        }
        report.orders += 1
      }
    }

    // --- 退款/售后 ---
    const refunds = await pullList<Record<string, unknown>>(
      '/admin/refunds?page=1&page_size=100',
      'admin'
    )
    refunds.forEach((raw) => {
      const mapped = mapAftersale(raw, db.stores[0]?.name || '', db.merchants[0]?.id || '')
      upsert(db.aftersales as Array<{ id: string }>, mapped as unknown as { id: string })
      report.aftersales += 1
    })

    // --- 公告：client/notices 只返回已发布 ---
    const notices = await pullList<Record<string, unknown>>('/client/notices', 'admin')
    notices.forEach((raw) => {
      const mapped = mapAnnouncement(raw)
      const existing = db.announcements.find((a) => a.id === mapped.id)
      if (existing) {
        existing.title = mapped.title
        existing.content = mapped.content
        existing.status = 'published'
        existing.publishedAt = mapped.publishedAt
      } else {
        db.announcements.unshift(mapped)
      }
      report.announcements += 1
    })

    saveDb()
    report.ok = true
  } catch (error) {
    report.error = error instanceof Error ? error.message : String(error)
  }
  return report
}

/** 写穿透：后端调用成功才执行本地变更；失败返回 false。 */
export async function writeThrough(
  backendCall: () => Promise<{ ok: boolean; status: number }>,
  localMutate: () => void
): Promise<boolean> {
  const result = await backendCall()
  if (!result.ok) return false
  localMutate()
  saveDb()
  return true
}


