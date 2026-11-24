import { clone, getDb, saveDb } from '@/console/mock/db'
import {
  MockApiError,
  inDateRange,
  mockCall,
  mockPaginate,
  toMoney,
  type MockPageQuery
} from './mock'
import type {
  AnalyticsData,
  Aftersale,
  Announcement,
  Category,
  MerchantBalance,
  MerchantDashboard,
  Notification,
  Order,
  PageResult,
  Product,
  Settlement,
  SettlementAccount,
  SettlementBill,
  ShippingTemplate,
  Sku,
  Store,
  Withdrawal
} from './types'
import { SHIPPING_CARRIERS } from '@/console/constants/labels'
import { formatDateInput } from '@/console/utils/format'
import { ensureSynced } from './bridge'
import { bridgeRequest, unwrap } from './bridge/client'
import { bindId, uuidFor as toUuid } from './bridge/identity'

const AID_PROJECTS = [
  { id: 'aid-1', title: '静宁苹果产业提质计划' },
  { id: 'aid-2', title: '定西马铃薯助农增收计划' },
  { id: 'aid-3', title: '民勤蜜瓜节水种植帮扶' },
  { id: 'aid-4', title: '陇南油橄榄产业帮扶' }
]

export interface ProductDraftInput {
  id?: string
  title: string
  subtitle: string
  categoryId: string
  description: string
  images: string[]
  skus: Array<{ id?: string; spec: string; price: string; stock: number; code?: string }>
  shippingTemplateId: string
  greenProfile: {
    origin: string
    plantingMode: string
    description: string
  }
  aidProjectId?: string
}

export interface MerchantFinanceOverview {
  balance: MerchantBalance
  settlementPending: number
  settlementConfirmed: number
  withdrawalPending: number
  recentSettlements: Settlement[]
}

function findMerchant(merchantId: string) {
  const db = getDb()
  const merchant = db.merchants.find((item) => item.id === merchantId)
  if (!merchant) throw new MockApiError('NOT_FOUND', '商家不存在')
  return { db, merchant }
}

function filterProducts(merchantId: string, query: MockPageQuery): Product[] {
  const { db } = findMerchant(merchantId)
  let items = db.products.filter((item) => item.merchantId === merchantId)
  if (query.status && query.status !== 'all') {
    items = items.filter((item) => item.status === query.status)
  }
  if (query.categoryId) {
    items = items.filter((item) => item.categoryId === query.categoryId)
  }
  const keyword = (query.keyword || '').trim().toLowerCase()
  if (keyword) {
    items = items.filter(
      (item) =>
        item.title.toLowerCase().includes(keyword) || item.subtitle.toLowerCase().includes(keyword)
    )
  }
  return items.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
}

function applyRefundToSettlement(merchantId: string, amount: string): void {
  const db = getDb()
  const settlement = db.settlements.find(
    (item) =>
      item.merchantId === merchantId && (item.status === 'pending' || item.status === 'confirmed')
  )
  if (!settlement) return
  settlement.refundDeduct = toMoney(Number(settlement.refundDeduct) + Number(amount))
  settlement.payable = toMoney(Math.max(0, Number(settlement.payable) - Number(amount)))
}

function logMerchant(
  merchantId: string,
  action: string,
  module: string,
  target: string,
  detail: string,
  risk: 'high' | 'normal' = 'normal'
): void {
  const { db, merchant } = findMerchant(merchantId)
  db.logs.unshift({
    id: `log-${Date.now()}-${Math.random().toString(16).slice(2, 7)}`,
    actor: merchant.username,
    actorName: merchant.ownerName,
    action,
    module,
    target,
    detail,
    ip: '10.0.0.24',
    risk,
    createdAt: new Date().toISOString()
  })
  saveDb()
}

function merchantTrend(merchantId: string, days: number): MerchantDashboard['trend'] {
  const seed = merchantId.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return Array.from({ length: days }, (_, index) => {
    const date = new Date(Date.now() - (days - 1 - index) * 86400000)
    const wave = Math.sin((index + seed) / 2.2) * 4 + 8
    const orders = Math.max(1, Math.round(wave + (index % 3)))
    return {
      date: formatDateInput(date),
      orders,
      sales: toMoney(orders * (128 + ((seed + index * 17) % 260)))
    }
  })
}

/** 当前商家 JWT 对应的后端店铺 ID（用于商品写穿透）。 */
async function backendStoreId(): Promise<string> {
  const result = await bridgeRequest<{ data?: Array<{ id?: string }> }>('/merchant/stores', {
    role: 'merchant'
  })
  const stores = unwrap(result)
  return String(stores?.[0]?.id || '')
}

/** 把管理端分类/助农 mockId 转成后端 UUID（无映射则省略该字段）。 */
function optionalUuid(mockId?: string): string | undefined {
  if (!mockId) return undefined
  const uuid = toUuid(mockId)
  return uuid === mockId ? undefined : uuid
}

export const merchantApi = {
  async dashboard(merchantId: string): Promise<MerchantDashboard> {
    await ensureSynced('merchant')
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const orders = db.orders.filter((item) => item.merchantId === merchantId)
      const products = db.products.filter((item) => item.merchantId === merchantId)
      const today = formatDateInput(new Date())
      const todayOrders = orders.filter(
        (item) => formatDateInput(new Date(item.createdAt)) === today
      )
      const balance = db.balances[merchantId]
      return clone({
        kpis: {
          todayOrders: todayOrders.length,
          todaySales: toMoney(
            todayOrders
              .filter((item) => item.status !== 'pending_payment' && item.status !== 'cancelled')
              .reduce((sum, item) => sum + Number(item.payAmount), 0)
          ),
          pendingShip: orders.filter((item) => item.status === 'paid').length,
          pendingAftersale: db.aftersales.filter(
            (item) => item.merchantId === merchantId && item.status === 'requested'
          ).length,
          availableBalance: balance?.available || '0.00',
          productOnline: products.filter((item) => item.status === 'approved' && item.listed).length
        },
        trend: merchantTrend(merchantId, 7),
        topProducts: products
          .slice()
          .sort((a, b) => b.sales - a.sales)
          .slice(0, 5)
          .map((item) => ({
            title: item.title,
            sales: item.sales,
            amount: toMoney(item.sales * Number(item.price))
          })),
        recentOrders: orders
          .slice()
          .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
          .slice(0, 5),
        updatedAt: new Date().toISOString()
      })
    })
  },

  async products(merchantId: string, query: MockPageQuery): Promise<PageResult<Product>> {
    await ensureSynced('merchant')
    return mockCall(() => {
      const items = filterProducts(merchantId, query)
      return clone(mockPaginate(items, query))
    })
  },

  async productStats(merchantId: string): Promise<Record<string, number>> {
    return mockCall(() => {
      const products = filterProducts(merchantId, {})
      return {
        all: products.length,
        draft: products.filter((item) => item.status === 'draft').length,
        pending_review: products.filter((item) => item.status === 'pending_review').length,
        approved: products.filter((item) => item.status === 'approved').length,
        rejected: products.filter((item) => item.status === 'rejected').length,
        removed: products.filter((item) => item.status === 'removed').length
      }
    })
  },

  async product(merchantId: string, productId: string): Promise<Product> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const product = db.products.find(
        (item) => item.id === productId && item.merchantId === merchantId
      )
      if (!product) throw new MockApiError('NOT_FOUND', '商品不存在')
      return clone(product)
    })
  },

  async categories(): Promise<Category[]> {
    return mockCall(() => clone(getDb().categories.filter((item) => item.enabled)))
  },

  async aidProjects(): Promise<Array<{ id: string; title: string }>> {
    return mockCall(() => clone(AID_PROJECTS))
  },

  async saveProduct(
    merchantId: string,
    input: ProductDraftInput,
    action: 'draft' | 'submit'
  ): Promise<Product> {
    // 后端写穿透：新建商品先 POST /merchant/products，拿到 UUID 并绑定；编辑则 PATCH
    let backendUuid = input.id ? toUuid(input.id) : ''
    const isRealEdit = Boolean(input.id) && backendUuid !== input.id
    const storeId = await backendStoreId()
    if (storeId) {
      const skus = input.skus.map((sku) => ({
        spec: sku.spec,
        code: sku.code || undefined,
        price: sku.price,
        initial_stock: sku.stock
      }))
      let backendResult: Awaited<ReturnType<typeof bridgeRequest>>
      if (isRealEdit) {
        backendResult = await bridgeRequest(`/merchant/products/${backendUuid}`, {
          method: 'PATCH',
          body: { title: input.title, subtitle: input.subtitle, description: input.description },
          role: 'merchant'
        })
      } else {
        backendResult = await bridgeRequest<{ data?: { id?: string }; code?: string }>('/merchant/products', {
          method: 'POST',
          body: {
            title: input.title,
            subtitle: input.subtitle || undefined,
            description: input.description || undefined,
            category_id: optionalUuid(input.categoryId),
            aid_project_id: optionalUuid(input.aidProjectId),
            skus
          },
          role: 'merchant'
        })
        if (backendResult.ok) {
          const payload = backendResult.data as { data?: { id?: string }; code?: string } | null
          const created = payload?.data
          if (created?.id) backendUuid = String(created.id)
        }
      }
      if (!backendResult.ok) {
        throw new MockApiError('BACKEND_ERROR', `商品写入后端失败（HTTP ${backendResult.status}）`)
      }
    }

    const product = await this.saveProductLocal(merchantId, input, action)
    if (backendUuid && backendUuid !== input?.id) bindId(product.id, backendUuid)
    // 提交审核穿透：POST /merchant/products/{id}/submit
    if (action === 'submit' && storeId && backendUuid) {
      const submitResult = await bridgeRequest(`/merchant/products/${backendUuid}/submit`, {
        method: 'POST',
        role: 'merchant'
      })
      if (!submitResult.ok) {
        throw new MockApiError('BACKEND_ERROR', '提交审核写入后端失败')
      }
    }
    return product
  },

  saveProductLocal(
    merchantId: string,
    input: ProductDraftInput,
    action: 'draft' | 'submit'
  ): Promise<Product> {
    return mockCall(() => {
      const { db, merchant } = findMerchant(merchantId)
      const store = db.stores.find((item) => item.merchantId === merchantId)
      if (!store) throw new MockApiError('NOT_FOUND', '店铺不存在')
      const category = db.categories.find((item) => item.id === input.categoryId)
      let product = input.id
        ? db.products.find((item) => item.id === input.id && item.merchantId === merchantId)
        : undefined
      const isNew = !product
      if (!product) {
        product = {
          id: `p-${Date.now()}`,
          merchantId,
          storeId: store.id,
          storeName: store.name,
          title: input.title,
          subtitle: input.subtitle,
          categoryId: input.categoryId,
          categoryName: category?.name || '未分类',
          description: input.description,
          price: input.skus[0]?.price || '0.00',
          minPrice: input.skus[0]?.price || '0.00',
          stock: 0,
          sales: 0,
          status: 'draft',
          listed: false,
          cover: input.images[0] || '',
          images: [],
          skus: [],
          shippingTemplateId: input.shippingTemplateId,
          greenProfile: {
            origin: input.greenProfile.origin,
            plantingMode: input.greenProfile.plantingMode,
            description: input.greenProfile.description,
            status: 'draft'
          },
          auditRecords: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        }
        db.products.unshift(product)
      }
      const old = clone(product)
      product.title = input.title
      product.subtitle = input.subtitle
      product.categoryId = input.categoryId
      product.categoryName = category?.name || product.categoryName
      product.description = input.description
      product.images = [...input.images]
      product.cover = input.images[0] || product.cover
      product.shippingTemplateId = input.shippingTemplateId
      product.greenProfile = {
        origin: input.greenProfile.origin,
        plantingMode: input.greenProfile.plantingMode,
        description: input.greenProfile.description,
        status: action === 'submit' ? 'pending_review' : product.greenProfile.status
      }
      product.aidProjectId = input.aidProjectId
      product.aidProjectName =
        AID_PROJECTS.find((item) => item.id === input.aidProjectId)?.title || undefined
      product.skus = input.skus.map((sku, index) => ({
        id: sku.id || `sku-${Date.now()}-${index}`,
        spec: sku.spec,
        price: sku.price,
        stock: sku.stock,
        code: sku.code || `SKU-${Date.now()}-${index}`
      }))
      product.price = product.skus[0]?.price || '0.00'
      product.minPrice = product.skus
        .map((item) => Number(item.price))
        .reduce((min, value) => Math.min(min, value), Number(product.skus[0]?.price || 0))
        .toFixed(2)
      product.stock = product.skus.reduce((sum, item) => sum + item.stock, 0)
      product.updatedAt = new Date().toISOString()
      if (action === 'submit') {
        product.status = 'pending_review'
        product.listed = false
        product.change =
          !isNew && old.status === 'approved'
            ? [
                ...(old.title !== product.title
                  ? [
                      {
                        field: 'title',
                        label: '商品标题',
                        oldValue: old.title,
                        newValue: product.title
                      }
                    ]
                  : []),
                ...(old.description !== product.description
                  ? [
                      {
                        field: 'description',
                        label: '商品描述',
                        oldValue: old.description,
                        newValue: product.description
                      }
                    ]
                  : []),
                ...(old.cover !== product.cover
                  ? [
                      {
                        field: 'images',
                        label: '商品主图',
                        oldValue: old.cover,
                        newValue: product.cover
                      }
                    ]
                  : [])
              ]
            : undefined
        product.auditRecords.unshift({
          id: `audit-${Date.now()}`,
          action: 'submit',
          operator: merchant.ownerName,
          createdAt: new Date().toISOString()
        })
        product.auditReason = undefined
        product.auditedAt = undefined
      } else {
        product.status = product.status === 'approved' ? 'draft' : 'draft'
        product.listed = false
      }
      saveDb()
      logMerchant(
        merchantId,
        action === 'submit' ? 'product.submit' : 'product.save_draft',
        '商品',
        product.title,
        action === 'submit' ? '商家提交商品审核' : '商家保存商品草稿'
      )
      return clone(product)
    })
  },

  async submitProduct(merchantId: string, productId: string): Promise<Product> {
    // 校验 + 后端穿透（真实商品必须提交到后端审核队列）
    await mockCall(() => {
      const { db } = findMerchant(merchantId)
      const product = db.products.find(
        (item) => item.id === productId && item.merchantId === merchantId
      )
      if (!product) throw new MockApiError('NOT_FOUND', '商品不存在')
      if (!['draft', 'rejected'].includes(product.status)) {
        throw new MockApiError('CONFLICT', '仅草稿或已驳回商品可提交审核')
      }
    })
    const backendId = toUuid(productId)
    if (backendId !== productId) {
      const result = await bridgeRequest(`/merchant/products/${backendId}/submit`, {
        method: 'POST',
        role: 'merchant'
      })
      if (!result.ok) throw new MockApiError('BACKEND_ERROR', '提交审核写入后端失败')
    }
    return mockCall(() => {
      const { db, merchant } = findMerchant(merchantId)
      const product = db.products.find(
        (item) => item.id === productId && item.merchantId === merchantId
      )
      if (!product) throw new MockApiError('NOT_FOUND', '商品不存在')
      product.status = 'pending_review'
      product.listed = false
      product.auditReason = undefined
      product.greenProfile.status = 'pending_review'
      product.updatedAt = new Date().toISOString()
      product.auditRecords.unshift({
        id: `audit-${Date.now()}`,
        action: 'submit',
        operator: merchant.ownerName,
        createdAt: new Date().toISOString()
      })
      saveDb()
      logMerchant(merchantId, 'product.submit', '商品', product.title, '商家提交商品审核')
      return clone(product)
    })
  },

  async updatePriceStock(
    merchantId: string,
    productId: string,
    updates: Array<{ id: string; price: string; stock: number }>
  ): Promise<Product> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const product = db.products.find(
        (item) => item.id === productId && item.merchantId === merchantId
      )
      if (!product) throw new MockApiError('NOT_FOUND', '商品不存在')
      updates.forEach((update) => {
        const sku = product.skus.find((item) => item.id === update.id)
        if (sku) {
          sku.price = update.price
          sku.stock = update.stock
        }
      })
      product.price = product.skus[0]?.price || product.price
      product.minPrice = product.skus
        .map((item) => Number(item.price))
        .reduce((min, value) => Math.min(min, value), Number(product.price))
        .toFixed(2)
      product.stock = product.skus.reduce((sum, item) => sum + item.stock, 0)
      product.updatedAt = new Date().toISOString()
      saveDb()
      return clone(product)
    })
  },

  async toggleListing(merchantId: string, productId: string, listed: boolean): Promise<Product> {
    // 校验 + 后端穿透（上架必须在后端 approved 之后才能成功，后端强制审批顺序）
    await mockCall(() => {
      const { db } = findMerchant(merchantId)
      const product = db.products.find(
        (item) => item.id === productId && item.merchantId === merchantId
      )
      if (!product) throw new MockApiError('NOT_FOUND', '商品不存在')
      if (product.status !== 'approved') {
        throw new MockApiError('CONFLICT', '仅审核通过的商品可上下架')
      }
    })
    const backendId = toUuid(productId)
    if (backendId !== productId) {
      const result = await bridgeRequest(`/merchant/products/${backendId}/${listed ? 'list' : 'delist'}`, {
        method: 'POST',
        role: 'merchant'
      })
      if (!result.ok) {
        throw new MockApiError('BACKEND_ERROR', listed ? '后端上架失败（商品可能尚未审核通过）' : '后端下架失败')
      }
    }
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const product = db.products.find(
        (item) => item.id === productId && item.merchantId === merchantId
      )
      if (!product) throw new MockApiError('NOT_FOUND', '商品不存在')
      product.listed = listed
      product.updatedAt = new Date().toISOString()
      product.auditRecords.unshift({
        id: `audit-${Date.now()}`,
        action: listed ? 'relist' : 'delist',
        operator: '商家',
        createdAt: new Date().toISOString()
      })
      saveDb()
      return clone(product)
    })
  },

  async orders(merchantId: string, query: MockPageQuery): Promise<PageResult<Order>> {
    await ensureSynced('merchant')
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      let items = db.orders.filter((item) => item.merchantId === merchantId)
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      const keyword = (query.keyword || '').trim()
      if (keyword) {
        items = items.filter(
          (item) =>
            item.orderNo.includes(keyword) ||
            item.buyerPhone.includes(keyword) ||
            item.buyerName.includes(keyword)
        )
      }
      if (query.date_from || query.date_to) {
        items = items.filter((item) => inDateRange(item.createdAt, query.date_from, query.date_to))
      }
      items.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      return clone(mockPaginate(items, query))
    })
  },

  async orderStats(merchantId: string): Promise<Record<string, number>> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const items = db.orders.filter((item) => item.merchantId === merchantId)
      return {
        all: items.length,
        pending_payment: items.filter((item) => item.status === 'pending_payment').length,
        paid: items.filter((item) => item.status === 'paid').length,
        shipped: items.filter((item) => item.status === 'shipped').length,
        completed: items.filter((item) => item.status === 'completed').length,
        cancelled: items.filter((item) => item.status === 'cancelled').length,
        refunding: items.filter((item) => item.status === 'refunding').length,
        refunded: items.filter((item) => item.status === 'refunded').length,
        partially_refunded: items.filter((item) => item.status === 'partially_refunded').length
      }
    })
  },

  async order(merchantId: string, orderId: string): Promise<Order> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const order = db.orders.find((item) => item.id === orderId && item.merchantId === merchantId)
      if (!order) throw new MockApiError('NOT_FOUND', '订单不存在')
      return clone(order)
    })
  },

  async shipOrder(
    merchantId: string,
    orderId: string,
    carrier: string,
    trackingNo: string
  ): Promise<Order> {
    // 校验放在本地，随后穿透后端；后端成功才更新本地，保证消费者端物流同步。
    await mockCall(() => {
      const { db } = findMerchant(merchantId)
      const order = db.orders.find((item) => item.id === orderId && item.merchantId === merchantId)
      if (!order) throw new MockApiError('NOT_FOUND', '订单不存在')
      if (order.status !== 'paid') {
        throw new MockApiError('ORDER_STATE_INVALID', '仅待发货订单可发货')
      }
      if (!SHIPPING_CARRIERS.includes(carrier)) {
        throw new MockApiError('VALIDATION_ERROR', '请选择有效的快递公司')
      }
      if (!/^[A-Za-z0-9-]{6,32}$/.test(trackingNo)) {
        throw new MockApiError('VALIDATION_ERROR', '快递单号需为 6–32 位字母、数字或短横线')
      }
    })

    const backendOrderId = toUuid(orderId)
    const backendResult = await bridgeRequest(
      `/merchant/orders/${backendOrderId}/ship`,
      { method: 'POST', body: { carrier, tracking_no: trackingNo }, role: 'merchant' }
    )

    // 后端不可达或该订单为纯演示数据时，保留原 mock 行为，不阻断演示流程。
    const isRealOrder = backendOrderId !== orderId
    if (isRealOrder && !backendResult.ok) {
      throw new MockApiError('BACKEND_ERROR', '发货写入后端失败，请稍后重试')
    }

    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const order = db.orders.find((item) => item.id === orderId && item.merchantId === merchantId)
      if (!order) throw new MockApiError('NOT_FOUND', '订单不存在')
      const now = new Date().toISOString()
      order.status = 'shipped'
      order.shippedAt = now
      order.shipment = {
        carrier,
        trackingNo,
        shippedAt: now,
        status: 'shipped',
        tracks: [
          { time: now, text: `${carrier} 已揽收` },
          { time: now, text: '包裹已发出，等待运输' }
        ]
      }
      order.statusLogs.push({
        time: now,
        action: 'ship',
        status: 'shipped',
        operator: '商家',
        note: `${carrier} ${trackingNo}`
      })
      saveDb()
      logMerchant(merchantId, 'order.ship', '订单', order.orderNo, `发货：${carrier} ${trackingNo}`)
      return clone(order)
    })
  },

  async aftersales(merchantId: string, query: MockPageQuery): Promise<PageResult<Aftersale>> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      let items = db.aftersales.filter((item) => item.merchantId === merchantId)
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      const keyword = (query.keyword || '').trim()
      if (keyword) {
        items = items.filter(
          (item) => item.refundNo.includes(keyword) || item.orderNo.includes(keyword)
        )
      }
      items.sort((a, b) =>
        query.status === 'requested'
          ? new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
          : new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      )
      return clone(mockPaginate(items, query))
    })
  },

  async aftersaleStats(merchantId: string): Promise<Record<string, number>> {
    return mockCall(() => {
      const items = getDb().aftersales.filter((item) => item.merchantId === merchantId)
      return {
        all: items.length,
        requested: items.filter((item) => item.status === 'requested').length,
        arbitrating: items.filter((item) => item.status === 'arbitrating').length,
        refunded: items.filter((item) => item.status === 'refunded').length,
        rejected: items.filter((item) => item.status === 'rejected').length
      }
    })
  },

  async handleAftersale(
    merchantId: string,
    aftersaleId: string,
    action: 'approve' | 'reject',
    reason?: string
  ): Promise<Aftersale> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const aftersale = db.aftersales.find(
        (item) => item.id === aftersaleId && item.merchantId === merchantId
      )
      if (!aftersale) throw new MockApiError('NOT_FOUND', '售后单不存在')
      if (aftersale.status !== 'requested') {
        throw new MockApiError('CONFLICT', '售后单已被处理')
      }
      if (action === 'reject' && !reason?.trim()) {
        throw new MockApiError('VALIDATION_ERROR', '拒绝原因必填')
      }
      const order = db.orders.find((item) => item.id === aftersale.orderId)
      const now = new Date().toISOString()
      aftersale.handledAt = now
      if (action === 'approve') {
        aftersale.status = 'refunded'
        aftersale.adminReason = '商家同意退款'
        if (order) {
          const fully = Number(aftersale.amount) >= Number(order.payAmount)
          order.refundAmount = toMoney(Number(order.refundAmount) + Number(aftersale.amount))
          order.status = fully ? 'refunded' : 'partially_refunded'
          order.statusLogs.push({
            time: now,
            action: 'refund_approve',
            status: order.status,
            operator: '商家'
          })
          aftersale.orderRefundAmount = order.refundAmount
        }
        applyRefundToSettlement(merchantId, aftersale.amount)
      } else {
        aftersale.status = 'arbitrating'
        aftersale.merchantReason = reason?.trim()
        if (order) {
          order.status = 'refunding'
          order.statusLogs.push({
            time: now,
            action: 'refund_reject',
            status: 'refunding',
            operator: '商家',
            note: reason
          })
        }
      }
      saveDb()
      logMerchant(
        merchantId,
        action === 'approve' ? 'aftersale.approve' : 'aftersale.reject',
        '售后',
        aftersale.refundNo,
        action === 'approve' ? `商家同意退款 ¥${aftersale.amount}` : `商家拒绝退款：${reason}`
      )
      return clone(aftersale)
    })
  },

  async financeOverview(merchantId: string): Promise<MerchantFinanceOverview> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const settlements = db.settlements.filter((item) => item.merchantId === merchantId)
      const withdrawals = db.withdrawals.filter((item) => item.merchantId === merchantId)
      return clone({
        balance: db.balances[merchantId],
        settlementPending: settlements.filter((item) => item.status === 'pending').length,
        settlementConfirmed: settlements.filter((item) => item.status === 'confirmed').length,
        withdrawalPending: withdrawals.filter((item) => item.status === 'pending').length,
        recentSettlements: settlements
          .slice()
          .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
          .slice(0, 5)
      })
    })
  },

  async settlements(merchantId: string, query: MockPageQuery): Promise<PageResult<Settlement>> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      let items = db.settlements.filter((item) => item.merchantId === merchantId)
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      items.sort((a, b) => new Date(b.periodEnd).getTime() - new Date(a.periodEnd).getTime())
      return clone(mockPaginate(items, query))
    })
  },

  async settlementStats(merchantId: string): Promise<Record<string, number>> {
    return mockCall(() => {
      const items = getDb().settlements.filter((item) => item.merchantId === merchantId)
      return {
        all: items.length,
        pending: items.filter((item) => item.status === 'pending').length,
        confirmed: items.filter((item) => item.status === 'confirmed').length,
        paid: items.filter((item) => item.status === 'paid').length
      }
    })
  },

  async settlementBills(merchantId: string, settlementId: string): Promise<SettlementBill[]> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const settlement = db.settlements.find(
        (item) => item.id === settlementId && item.merchantId === merchantId
      )
      if (!settlement) throw new MockApiError('NOT_FOUND', '结算单不存在')
      const orders = db.orders
        .filter((item) => item.merchantId === merchantId)
        .slice(0, Math.min(6, settlement.orderCount))
      return orders.map((order, index) => ({
        id: `${settlement.id}-${index}`,
        orderNo: order.orderNo,
        storeOrderNo: `SO${order.orderNo.slice(2)}`,
        paidAt: order.paidAt || order.createdAt,
        amount: order.itemsTotal,
        commission: toMoney(Number(order.itemsTotal) * 0.05),
        payable: toMoney(Number(order.itemsTotal) * 0.95)
      }))
    })
  },

  async withdrawals(merchantId: string, query: MockPageQuery): Promise<PageResult<Withdrawal>> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      let items = db.withdrawals.filter((item) => item.merchantId === merchantId)
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      items.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      return clone(mockPaginate(items, query))
    })
  },

  async withdrawalStats(merchantId: string): Promise<Record<string, number>> {
    return mockCall(() => {
      const items = getDb().withdrawals.filter((item) => item.merchantId === merchantId)
      return {
        all: items.length,
        pending: items.filter((item) => item.status === 'pending').length,
        approved: items.filter((item) => item.status === 'approved').length,
        rejected: items.filter((item) => item.status === 'rejected').length
      }
    })
  },

  async applyWithdrawal(merchantId: string, amount: string): Promise<Withdrawal> {
    return mockCall(() => {
      const { db, merchant } = findMerchant(merchantId)
      const balance = db.balances[merchantId]
      const value = Number(amount)
      if (!Number.isFinite(value) || value <= 0) {
        throw new MockApiError('VALIDATION_ERROR', '提现金额必须大于 0')
      }
      if (value > Number(balance.available)) {
        throw new MockApiError('VALIDATION_ERROR', '提现金额不能超过可提现余额')
      }
      const account = db.settlementAccounts[merchantId]
      const withdrawal: Withdrawal = {
        id: `wd-${Date.now()}`,
        merchantId,
        amount: toMoney(value),
        accountName: account?.accountName || merchant.ownerName,
        bankName: account?.bankName || '中国农业银行',
        accountNo: account?.accountNo || '—',
        status: 'pending',
        createdAt: new Date().toISOString()
      }
      db.withdrawals.unshift(withdrawal)
      balance.available = toMoney(Number(balance.available) - value)
      balance.frozen = toMoney(Number(balance.frozen) + value)
      saveDb()
      logMerchant(
        merchantId,
        'withdrawal.apply',
        '财务',
        withdrawal.id,
        `申请提现 ¥${toMoney(value)}`
      )
      return clone(withdrawal)
    })
  },

  async settlementAccount(merchantId: string): Promise<SettlementAccount> {
    return mockCall(() => {
      const account = getDb().settlementAccounts[merchantId]
      if (!account) throw new MockApiError('NOT_FOUND', '结算账户不存在')
      return clone(account)
    })
  },

  async saveSettlementAccount(
    merchantId: string,
    payload: SettlementAccount
  ): Promise<SettlementAccount> {
    return mockCall(() => {
      const db = getDb()
      db.settlementAccounts[merchantId] = { ...payload, merchantId }
      saveDb()
      logMerchant(merchantId, 'settlement_account.update', '财务', merchantId, '更新结算账户')
      return clone(db.settlementAccounts[merchantId])
    })
  },

  async shop(merchantId: string): Promise<Store> {
    return mockCall(() => {
      const store = getDb().stores.find((item) => item.merchantId === merchantId)
      if (!store) throw new MockApiError('NOT_FOUND', '店铺不存在')
      return clone(store)
    })
  },

  async saveShop(
    merchantId: string,
    payload: { name: string; logo: string; description: string; region: string }
  ): Promise<Store> {
    return mockCall(() => {
      const db = getDb()
      const store = db.stores.find((item) => item.merchantId === merchantId)
      if (!store) throw new MockApiError('NOT_FOUND', '店铺不存在')
      store.name = payload.name
      store.logo = payload.logo
      store.description = payload.description
      store.region = payload.region
      saveDb()
      logMerchant(merchantId, 'store.update', '店铺', store.name, '更新店铺资料')
      return clone(store)
    })
  },

  async saveShippingTemplates(merchantId: string, templates: ShippingTemplate[]): Promise<Store> {
    return mockCall(() => {
      const db = getDb()
      const store = db.stores.find((item) => item.merchantId === merchantId)
      if (!store) throw new MockApiError('NOT_FOUND', '店铺不存在')
      store.shippingTemplates = templates.map((item, index) => ({
        ...item,
        id: item.id || `ship-${merchantId}-${Date.now()}-${index}`
      }))
      saveDb()
      logMerchant(merchantId, 'store.shipping_update', '店铺', store.name, '更新运费模板')
      return clone(store)
    })
  },

  async notifications(merchantId: string): Promise<Notification[]> {
    return mockCall(() => {
      findMerchant(merchantId)
      return clone(
        getDb()
          .notifications.slice()
          .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      )
    })
  },

  async markNotificationRead(merchantId: string, notificationId: string): Promise<void> {
    return mockCall(() => {
      findMerchant(merchantId)
      const db = getDb()
      const item = db.notifications.find((notification) => notification.id === notificationId)
      if (item) item.read = true
      saveDb()
    })
  },

  async markAllNotificationsRead(merchantId: string): Promise<void> {
    return mockCall(() => {
      findMerchant(merchantId)
      const db = getDb()
      db.notifications.forEach((item) => {
        item.read = true
      })
      saveDb()
    })
  },

  async notices(): Promise<Announcement[]> {
    return mockCall(() =>
      clone(
        getDb()
          .announcements.filter((item) => item.status === 'published')
          .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      )
    )
  },

  async analytics(merchantId: string, range: '7' | '30'): Promise<AnalyticsData> {
    return mockCall(() => {
      const { db } = findMerchant(merchantId)
      const days = range === '7' ? 7 : 30
      const trend = merchantTrend(merchantId, days)
      const products = db.products.filter((item) => item.merchantId === merchantId)
      const categoryMap = new Map<string, number>()
      products.forEach((item) => {
        categoryMap.set(
          item.categoryName,
          (categoryMap.get(item.categoryName) || 0) + item.sales * Number(item.price)
        )
      })
      const totalSales = [...categoryMap.values()].reduce((sum, value) => sum + value, 0)
      return clone({
        range: `近 ${days} 天`,
        kpis: [
          {
            label: '支付订单',
            value: String(trend.reduce((sum, item) => sum + item.orders, 0)),
            hint: '演示统计'
          },
          {
            label: '销售额',
            value: `¥${toMoney(trend.reduce((sum, item) => sum + Number(item.sales), 0))}`,
            hint: '服务端计价口径'
          },
          {
            label: '在售商品',
            value: String(
              products.filter((item) => item.status === 'approved' && item.listed).length
            ),
            hint: '审核通过且上架'
          },
          {
            label: '好评率',
            value: '—',
            hint: '评价接口未接入'
          }
        ],
        trend,
        categoryShare: [...categoryMap.entries()].map(([name, value]) => ({
          name,
          value: totalSales ? Math.round((value / totalSales) * 100) : 0
        }))
      })
    })
  }
}

export type { Sku }
