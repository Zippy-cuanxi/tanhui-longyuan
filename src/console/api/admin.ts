import { assetUrl } from '@/api/http'
import { appendLog, clone, getDb, saveDb } from '@/console/mock/db'
import {
  MockApiError,
  byDateDesc,
  inDateRange,
  mockCall,
  mockPaginate,
  toMoney,
  type MockPageQuery
} from './mock'
import type {
  AdminAccount,
  AdminDashboard,
  AdminRole,
  Aftersale,
  Announcement,
  Category,
  Member,
  MerchantAccount,
  OperationLog,
  Order,
  PageResult,
  Product,
  Settlement,
  SettlementBill,
  Store,
  Withdrawal
} from './types'
import { formatDateInput } from '@/console/utils/format'
import { ensureSynced } from './bridge'
import { bridgeRequest, unwrap } from './bridge/client'
import { bindId, uuidFor as toUuid } from './bridge/identity'
import { publishDemoProduct, unpublishDemoProduct } from '@/api/demoCatalog'
import { notifyCatalogChanged } from '@/utils/catalogBus'

export interface AdminMerchantRow extends MerchantAccount {
  storeId: string
  storeStatus: Store['status']
  penaltyCount: number
}

export interface MerchantPenalty {
  id: string
  reason: string
  operator: string
  createdAt: string
  type: 'freeze' | 'reject' | 'warn'
}

export interface MerchantDetail {
  merchant: MerchantAccount
  store: Store | null
  penalties: MerchantPenalty[]
}

export interface AdminWithdrawalRow extends Withdrawal {
  merchantName: string
  storeName: string
}

export interface MemberDetail {
  member: Member
  orders: Order[]
  aftersales: Aftersale[]
}

export interface CategoryInput {
  id?: string
  name: string
  parentId?: string
  sort: number
  enabled: boolean
}

export interface AnnouncementInput {
  id?: string
  title: string
  content: string
}

export interface AdminAccountInput {
  username: string
  name: string
  roleCode: AdminAccount['roleCode']
}

export interface CommissionSettings {
  rate: string
  cycle: string
  minWithdrawal: string
  autoConfirm: boolean
}

export interface SettlementPreview {
  storeId: string
  storeName: string
  periodStart: string
  periodEnd: string
  orderCount: number
  ordersTotal: string
  commission: string
  payable: string
}

function currentAdmin(): AdminAccount {
  if (typeof localStorage !== 'undefined') {
    const raw =
      localStorage.getItem('tanhui_console_session') ||
      sessionStorage.getItem('tanhui_console_session')
    if (raw) {
      try {
        const session = JSON.parse(raw) as {
          role?: string
          account?: AdminAccount
        }
        if (session.role === 'admin' && session.account) return session.account
      } catch {
        // ignore
      }
    }
  }
  return getDb().admins[0]
}

function adminLog(
  action: string,
  module: string,
  target: string,
  detail: string,
  risk: 'high' | 'normal' = 'high'
): void {
  const admin = currentAdmin()
  appendLog({
    actor: admin.username,
    actorName: admin.name,
    action,
    module,
    target,
    detail,
    risk
  })
}

function buildPenalties(merchant: MerchantAccount): MerchantPenalty[] {
  const db = getDb()
  const items: MerchantPenalty[] = db.logs
    .filter(
      (log) =>
        log.risk === 'high' &&
        log.target === merchant.companyName &&
        (log.action === 'merchant.review' || log.action === 'merchant.freeze')
    )
    .slice(0, 4)
    .map((log) => ({
      id: log.id,
      reason: log.detail,
      operator: log.actorName,
      createdAt: log.createdAt,
      type: log.action === 'merchant.freeze' ? 'freeze' : 'reject'
    }))
  if (merchant.rejectReason) {
    items.unshift({
      id: `penalty-reject-${merchant.id}`,
      reason: merchant.rejectReason,
      operator: '平台审核员',
      createdAt: merchant.reviewedAt || merchant.createdAt,
      type: 'reject'
    })
  }
  if (merchant.frozenReason) {
    items.unshift({
      id: `penalty-freeze-${merchant.id}`,
      reason: merchant.frozenReason,
      operator: '平台管理员',
      createdAt: merchant.reviewedAt || merchant.createdAt,
      type: 'freeze'
    })
  }
  return items
}

function merchantRow(merchant: MerchantAccount): AdminMerchantRow {
  const db = getDb()
  const store = db.stores.find((item) => item.merchantId === merchant.id)
  return {
    ...merchant,
    storeId: store?.id || '',
    storeStatus: store?.status || 'suspended',
    penaltyCount: buildPenalties(merchant).length
  }
}

function applySettlementRefund(merchantId: string, amount: string): void {
  const db = getDb()
  const settlement = db.settlements.find(
    (item) =>
      item.merchantId === merchantId && (item.status === 'pending' || item.status === 'confirmed')
  )
  if (!settlement) return
  settlement.refundDeduct = toMoney(Number(settlement.refundDeduct) + Number(amount))
  settlement.payable = toMoney(Math.max(0, Number(settlement.payable) - Number(amount)))
}

function adminTrend(days: number): AdminDashboard['trend'] {
  return Array.from({ length: days }, (_, index) => {
    const date = new Date(Date.now() - (days - 1 - index) * 86400000)
    const gmv = 7200 + Math.sin(index / 2.7) * 2100 + ((index * 137) % 3200)
    return {
      date: formatDateInput(date),
      gmv: toMoney(gmv),
      orders: Math.max(4, Math.round(gmv / 235))
    }
  })
}

function findStore(id: string): Store {
  const store = getDb().stores.find((item) => item.id === id)
  if (!store) throw new MockApiError('NOT_FOUND', '店铺不存在')
  return store
}

export const adminApi = {
  async dashboard(): Promise<AdminDashboard> {
    await ensureSynced('admin')
    return mockCall(() => {
      const db = getDb()
      const effectiveOrders = db.orders.filter(
        (item) => item.status !== 'pending_payment' && item.status !== 'cancelled'
      )
      const gmvPay = effectiveOrders.reduce(
        (sum, item) => sum + Number(item.payAmount) - Number(item.refundAmount),
        0
      )
      const paidOrders = db.orders.filter(
        (item) => item.status !== 'pending_payment' && item.status !== 'cancelled'
      ).length
      const refunded = db.orders.filter(
        (item) =>
          item.status === 'refunded' ||
          item.status === 'partially_refunded' ||
          item.status === 'refunding'
      ).length
      const categoryMap = new Map<string, { amount: number; quantity: number }>()
      db.products.forEach((item) => {
        const entry = categoryMap.get(item.categoryName) || { amount: 0, quantity: 0 }
        entry.amount += item.sales * Number(item.price)
        entry.quantity += item.sales
        categoryMap.set(item.categoryName, entry)
      })
      const storeMap = new Map<string, { amount: number; orders: number }>()
      db.orders.forEach((item) => {
        const entry = storeMap.get(item.storeName) || { amount: 0, orders: 0 }
        if (item.status !== 'pending_payment' && item.status !== 'cancelled') {
          entry.amount += Number(item.payAmount) - Number(item.refundAmount)
          entry.orders += 1
        }
        storeMap.set(item.storeName, entry)
      })
      const listedProducts = db.products.filter(
        (item) => item.status === 'approved' && item.listed
      ).length
      const greenListedProducts = db.products.filter(
        (item) =>
          item.status === 'approved' && item.listed && item.greenProfile.status === 'approved'
      ).length
      const statusOrder = [
        'pending_payment',
        'paid',
        'shipped',
        'completed',
        'refunding',
        'refunded',
        'partially_refunded',
        'cancelled'
      ]
      return clone({
        kpis: {
          gmvPay: toMoney(gmvPay),
          paidOrders,
          aov: toMoney(paidOrders ? gmvPay / paidOrders : 0),
          payRate: Number(((paidOrders / Math.max(1, db.orders.length)) * 100).toFixed(1)),
          refundRate: Number(((refunded / Math.max(1, paidOrders)) * 100).toFixed(1)),
          newUsers: 12
        },
        todos: {
          productAudits: db.products.filter((item) => item.status === 'pending_review').length,
          merchantReviews: db.merchants.filter((item) => item.status === 'pending').length,
          refunds: db.aftersales.filter(
            (item) => item.status === 'requested' || item.status === 'arbitrating'
          ).length,
          greenReviews: db.products.filter((item) => item.greenProfile.status === 'pending_review')
            .length,
          settlementPending: db.settlements.filter((item) => item.status === 'pending').length,
          stockAlerts: db.products.filter((item) => item.status === 'approved' && item.stock < 10)
            .length
        },
        trend: adminTrend(30),
        orderStatus: statusOrder.map((status) => ({
          status,
          count: db.orders.filter((item) => item.status === status).length
        })),
        categoryTop: [...categoryMap.entries()]
          .map(([name, value]) => ({
            name,
            amount: toMoney(value.amount),
            quantity: value.quantity
          }))
          .sort((a, b) => Number(b.amount) - Number(a.amount))
          .slice(0, 6),
        storeTop: [...storeMap.entries()]
          .map(([name, value]) => ({
            name,
            amount: toMoney(value.amount),
            orders: value.orders
          }))
          .sort((a, b) => Number(b.amount) - Number(a.amount))
          .slice(0, 10),
        originTop: db.origins
          .slice()
          .sort((a, b) => b.totals.sales - a.totals.sales)
          .slice(0, 6)
          .map((item) => ({
            name: item.name,
            location: item.location,
            sales: item.totals.sales,
            aid: item.totals.aid
          })),
        aid: { projects: 4, raised: '320000.00', goal: '1500000.00' },
        green: {
          greenProducts: greenListedProducts,
          listedProducts,
          ratio: listedProducts
            ? Math.min(100, Number(((greenListedProducts / listedProducts) * 100).toFixed(1)))
            : 0
        },
        points: {
          balanceTotal: db.members.reduce((sum, item) => sum + item.points, 0),
          earned: db.members.reduce((sum, item) => sum + item.points, 0) + 12800,
          spent: 12800
        },
        updatedAt: new Date().toISOString()
      })
    })
  },

  async merchants(query: MockPageQuery): Promise<PageResult<AdminMerchantRow>> {
    await ensureSynced('admin')
    return mockCall(() => {
      const db = getDb()
      let items = db.merchants.slice()
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      const keyword = (query.keyword || '').trim().toLowerCase()
      if (keyword) {
        items = items.filter(
          (item) =>
            item.companyName.toLowerCase().includes(keyword) ||
            item.storeName.toLowerCase().includes(keyword) ||
            item.username.toLowerCase().includes(keyword) ||
            item.ownerName.toLowerCase().includes(keyword) ||
            item.phone.includes(keyword)
        )
      }
      if (query.date_from || query.date_to) {
        items = items.filter((item) => inDateRange(item.createdAt, query.date_from, query.date_to))
      }
      items.sort(byDateDesc)
      const page = mockPaginate(
        items.map((item) => merchantRow(item)),
        query
      )
      return clone(page)
    })
  },

  async merchantStats(): Promise<Record<string, number>> {
    return mockCall(() => {
      const merchants = getDb().merchants
      return {
        all: merchants.length,
        normal: merchants.filter((item) => item.status === 'normal').length,
        pending: merchants.filter((item) => item.status === 'pending').length,
        rejected: merchants.filter((item) => item.status === 'rejected').length,
        frozen: merchants.filter((item) => item.status === 'frozen').length
      }
    })
  },

  async merchantDetail(id: string): Promise<MerchantDetail> {
    return mockCall(() => {
      const db = getDb()
      const merchant = db.merchants.find((item) => item.id === id)
      if (!merchant) throw new MockApiError('NOT_FOUND', '商家不存在')
      const store = db.stores.find((item) => item.merchantId === merchant.id) || null
      return clone({ merchant, store, penalties: buildPenalties(merchant) })
    })
  },

  async reviewMerchant(
    id: string,
    action: 'approve' | 'reject' | 'freeze' | 'unfreeze',
    reason?: string
  ): Promise<AdminMerchantRow> {
    // 本地校验（不修改数据）
    await mockCall(() => {
      const db = getDb()
      const merchant = db.merchants.find((item) => item.id === id)
      if (!merchant) throw new MockApiError('NOT_FOUND', '商家不存在')
      if ((action === 'reject' || action === 'freeze') && !reason?.trim()) {
        throw new MockApiError('VALIDATION_ERROR', '请填写原因')
      }
      if (action === 'freeze' && merchant.status === 'frozen') {
        throw new MockApiError('CONFLICT', '该商家已处于冻结状态')
      }
      if (action === 'unfreeze' && merchant.status !== 'frozen') {
        throw new MockApiError('CONFLICT', '仅已冻结商家可解冻')
      }
      if (action === 'approve' && merchant.status !== 'pending' && merchant.status !== 'rejected') {
        throw new MockApiError('CONFLICT', '当前状态不可审核通过')
      }
      if (action === 'reject' && merchant.status !== 'pending' && merchant.status !== 'rejected') {
        throw new MockApiError('CONFLICT', '当前状态不可驳回')
      }
    })

    // 真实商家：穿透后端审核，后端成功才更新本地；后端不支持则阻断，杜绝"假审批"
    const backendId = toUuid(id)
    if (backendId !== id) {
      const result = await bridgeRequest(`/admin/merchants/${backendId}/review`, {
        method: 'POST',
        body: { action, reason: reason?.trim() || undefined },
        role: 'admin'
      })
      if (!result.ok)
        throw new MockApiError('BACKEND_ERROR', `后端审核失败（HTTP ${result.status}）`)
    }

    return mockCall(() => {
      const db = getDb()
      const merchant = db.merchants.find((item) => item.id === id)
      if (!merchant) throw new MockApiError('NOT_FOUND', '商家不存在')
      const store = db.stores.find((item) => item.merchantId === merchant.id)
      const now = new Date().toISOString()
      if (action === 'approve') {
        if (merchant.status !== 'pending' && merchant.status !== 'rejected') {
          throw new MockApiError('CONFLICT', '当前状态不可审核通过')
        }
        merchant.status = 'normal'
        merchant.rejectReason = undefined
        merchant.frozenReason = undefined
        merchant.reviewedAt = now
        if (store) {
          store.status = 'active'
          store.qualifications.forEach((item) => {
            if (item.status === 'pending') item.status = 'approved'
          })
        }
        adminLog('merchant.review', '商家', merchant.companyName, '入驻审核通过', 'high')
      } else if (action === 'reject') {
        if (merchant.status !== 'pending' && merchant.status !== 'rejected') {
          throw new MockApiError('CONFLICT', '当前状态不可驳回')
        }
        merchant.status = 'rejected'
        merchant.rejectReason = reason?.trim()
        merchant.reviewedAt = now
        if (store) store.status = 'suspended'
        adminLog('merchant.review', '商家', merchant.companyName, `入驻审核驳回：${reason}`, 'high')
      } else if (action === 'freeze') {
        merchant.status = 'frozen'
        merchant.frozenReason = reason?.trim()
        merchant.reviewedAt = now
        if (store) store.status = 'suspended'
        adminLog('merchant.freeze', '商家', merchant.companyName, `冻结商家：${reason}`, 'high')
      } else {
        merchant.status = 'normal'
        merchant.frozenReason = undefined
        merchant.reviewedAt = now
        if (store) store.status = 'active'
        adminLog('merchant.freeze', '商家', merchant.companyName, '解除商家冻结', 'high')
      }
      saveDb()
      return clone(merchantRow(merchant))
    })
  },

  async products(query: MockPageQuery): Promise<PageResult<Product>> {
    await ensureSynced('admin')
    return mockCall(() => {
      const db = getDb()
      let items = db.products.slice()
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      if (query.storeId) {
        items = items.filter((item) => item.storeId === query.storeId)
      }
      if (query.categoryId) {
        items = items.filter((item) => item.categoryId === query.categoryId)
      }
      const keyword = (query.keyword || '').trim().toLowerCase()
      if (keyword) {
        items = items.filter(
          (item) =>
            item.title.toLowerCase().includes(keyword) ||
            item.storeName.toLowerCase().includes(keyword)
        )
      }
      if (query.date_from || query.date_to) {
        items = items.filter((item) => inDateRange(item.createdAt, query.date_from, query.date_to))
      }
      items.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
      return clone(mockPaginate(items, query))
    })
  },

  async productStats(): Promise<Record<string, number>> {
    return mockCall(() => {
      const products = getDb().products
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

  async product(id: string): Promise<Product> {
    return mockCall(() => {
      const product = getDb().products.find((item) => item.id === id)
      if (!product) throw new MockApiError('NOT_FOUND', '商品不存在')
      return clone(product)
    })
  },

  async auditProduct(id: string, action: 'approve' | 'reject', reason?: string): Promise<Product> {
    await mockCall(() => {
      const db = getDb()
      const product = db.products.find((item) => item.id === id)
      if (!product) throw new MockApiError('NOT_FOUND', '商品不存在')
      if (product.status !== 'pending_review') {
        throw new MockApiError('CONFLICT', '该商品不在待审核状态')
      }
      if (action === 'reject' && !reason?.trim()) {
        throw new MockApiError('VALIDATION_ERROR', '驳回原因必填')
      }
    })
    const backendId = toUuid(id)
    let syncInfo: Pick<Product, 'syncStatus' | 'syncAttempts' | 'syncError' | 'syncMessage'> = {}
    if (backendId !== id) {
      const result = await bridgeRequest<{
        data?: {
          sync_status?: string
          sync_attempts?: number
          sync_error?: string
          sync_message?: string
        }
      }>(`/admin/products/${backendId}/audit`, {
        method: 'POST',
        body: { action, reason: reason?.trim() || undefined },
        role: 'admin'
      })
      if (!result.ok)
        throw new MockApiError(
          'BACKEND_ERROR',
          result.message
            ? `后端商品审核失败：${result.message}`
            : `后端商品审核失败（HTTP ${result.status}）`
        )
      const payload = result.data?.data
      if (payload?.sync_status === 'success' || payload?.sync_status === 'failed') {
        syncInfo = {
          syncStatus: payload.sync_status,
          syncAttempts: payload.sync_attempts,
          syncError: payload.sync_error,
          syncMessage: payload.sync_message
        }
      }
    }
    const updated = await mockCall(() => {
      const db = getDb()
      const product = db.products.find((item) => item.id === id)
      if (!product) throw new MockApiError('NOT_FOUND', '商品不存在')
      const admin = currentAdmin()
      const now = new Date().toISOString()
      if (action === 'approve') {
        product.status = 'approved'
        // 审核通过即上架，确保消费者端「全部商品」立即可见（与真实后端一致）。
        product.listed = true
        product.auditReason = undefined
        if (product.greenProfile.status === 'pending_review') {
          product.greenProfile.status = 'approved'
        }
        product.auditRecords.unshift({
          id: `audit-${Date.now()}`,
          action: 'approve',
          operator: admin.name,
          createdAt: now
        })
        adminLog('product.audit', '商品', product.title, '商品审核通过', 'normal')
      } else {
        product.status = 'rejected'
        product.listed = false
        product.auditReason = reason?.trim()
        product.greenProfile.status = 'rejected'
        product.auditRecords.unshift({
          id: `audit-${Date.now()}`,
          action: 'reject',
          operator: admin.name,
          reason: reason?.trim(),
          createdAt: now
        })
        adminLog('product.audit', '商品', product.title, `商品审核驳回：${reason}`, 'normal')
      }
      product.auditedAt = now
      product.updatedAt = now
      // 静态演示（GitHub Pages）没有后端：把审核结果写入消费者端发布区并广播。
      if (import.meta.env.VITE_STATIC_DEMO === '1') {
        if (action === 'approve') publishDemoProduct(product)
        else unpublishDemoProduct(product.id)
      }
      saveDb()
      return clone({ ...product, ...syncInfo })
    })
    // 真实后端：本地管理端与消费者端同源时立即广播，其他客户端由版本轮询兜底。
    if (backendId !== id) notifyCatalogChanged()
    return updated
  },

  async removeProduct(id: string, reason: string): Promise<Product> {
    const backendId = toUuid(id)
    if (backendId !== id) {
      const result = await bridgeRequest(`/admin/products/${backendId}/audit`, {
        method: 'POST',
        body: { action: 'remove', reason: reason.trim() },
        role: 'admin'
      })
      if (!result.ok) throw new MockApiError('BACKEND_ERROR', '后端强制下架失败')
    }
    const removed = await mockCall(() => {
      const db = getDb()
      const product = db.products.find((item) => item.id === id)
      if (!product) throw new MockApiError('NOT_FOUND', '商品不存在')
      if (!reason.trim()) throw new MockApiError('VALIDATION_ERROR', '下架原因必填')
      const admin = currentAdmin()
      product.status = 'removed'
      product.listed = false
      product.auditReason = reason.trim()
      product.updatedAt = new Date().toISOString()
      product.auditRecords.unshift({
        id: `audit-${Date.now()}`,
        action: 'remove',
        operator: admin.name,
        reason: reason.trim(),
        createdAt: new Date().toISOString()
      })
      saveDb()
      if (import.meta.env.VITE_STATIC_DEMO === '1') unpublishDemoProduct(product.id)
      adminLog('product.remove', '商品', product.title, `平台强制下架：${reason}`, 'high')
      return clone(product)
    })
    if (backendId !== id) notifyCatalogChanged()
    return removed
  },

  async categories(): Promise<Category[]> {
    return mockCall(() =>
      clone(
        getDb()
          .categories.slice()
          .sort((a, b) => a.sort - b.sort)
      )
    )
  },

  async saveCategory(input: CategoryInput): Promise<Category> {
    return mockCall(() => {
      const db = getDb()
      if (!input.name.trim()) throw new MockApiError('VALIDATION_ERROR', '分类名称必填')
      let category = input.id ? db.categories.find((item) => item.id === input.id) : undefined
      if (!category) {
        category = {
          id: `cat-${Date.now()}`,
          name: input.name.trim(),
          parentId: input.parentId,
          productCount: 0,
          sort: input.sort,
          enabled: input.enabled
        }
        db.categories.push(category)
      } else {
        category.name = input.name.trim()
        category.parentId = input.parentId
        category.sort = input.sort
        category.enabled = input.enabled
      }
      saveDb()
      adminLog('category.save', '系统', category.name, `保存商品分类：${category.name}`, 'normal')
      return clone(category)
    })
  },

  async orders(query: MockPageQuery): Promise<PageResult<Order>> {
    await ensureSynced('admin')
    return mockCall(() => {
      const db = getDb()
      let items = db.orders.slice()
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      if (query.storeId) {
        items = items.filter((item) => item.storeId === query.storeId)
      }
      const keyword = (query.keyword || '').trim()
      if (keyword) {
        items = items.filter(
          (item) =>
            item.orderNo.includes(keyword) ||
            item.buyerName.includes(keyword) ||
            item.buyerPhone.includes(keyword) ||
            item.storeName.includes(keyword)
        )
      }
      if (query.date_from || query.date_to) {
        items = items.filter((item) => inDateRange(item.createdAt, query.date_from, query.date_to))
      }
      items.sort(byDateDesc)
      return clone(mockPaginate(items, query))
    })
  },

  async orderStats(): Promise<Record<string, number>> {
    return mockCall(() => {
      const orders = getDb().orders
      const statuses = [
        'pending_payment',
        'paid',
        'shipped',
        'completed',
        'cancelled',
        'refunding',
        'refunded',
        'partially_refunded'
      ]
      const counts: Record<string, number> = { all: orders.length }
      statuses.forEach((status) => {
        counts[status] = orders.filter((item) => item.status === status).length
      })
      return counts
    })
  },

  async order(id: string): Promise<Order> {
    return mockCall(() => {
      const order = getDb().orders.find((item) => item.id === id)
      if (!order) throw new MockApiError('NOT_FOUND', '订单不存在')
      return clone(order)
    })
  },

  async aftersales(query: MockPageQuery): Promise<PageResult<Aftersale>> {
    await ensureSynced('admin')
    return mockCall(() => {
      const db = getDb()
      let items = db.aftersales.slice()
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      if (query.storeId) {
        items = items.filter((item) => item.storeId === query.storeId)
      }
      const keyword = (query.keyword || '').trim()
      if (keyword) {
        items = items.filter(
          (item) =>
            item.refundNo.includes(keyword) ||
            item.orderNo.includes(keyword) ||
            item.buyerName.includes(keyword) ||
            item.storeName.includes(keyword)
        )
      }
      if (query.date_from || query.date_to) {
        items = items.filter((item) => inDateRange(item.createdAt, query.date_from, query.date_to))
      }
      items.sort((a, b) => {
        if (a.status === 'arbitrating' && b.status !== 'arbitrating') return -1
        if (b.status === 'arbitrating' && a.status !== 'arbitrating') return 1
        return byDateDesc(a, b)
      })
      return clone(mockPaginate(items, query))
    })
  },

  async aftersaleStats(): Promise<Record<string, number>> {
    return mockCall(() => {
      const items = getDb().aftersales
      return {
        all: items.length,
        requested: items.filter((item) => item.status === 'requested').length,
        arbitrating: items.filter((item) => item.status === 'arbitrating').length,
        refunded: items.filter((item) => item.status === 'refunded').length,
        rejected: items.filter((item) => item.status === 'rejected').length
      }
    })
  },

  async arbitrateAftersale(
    id: string,
    action: 'refund' | 'reject',
    reason: string
  ): Promise<Aftersale> {
    await mockCall(() => {
      const db = getDb()
      const aftersale = db.aftersales.find((item) => item.id === id)
      if (!aftersale) throw new MockApiError('NOT_FOUND', '售后单不存在')
      if (!['arbitrating', 'requested'].includes(aftersale.status)) {
        throw new MockApiError('CONFLICT', '仅待处理/仲裁中的售后单可裁决')
      }
      if (!reason.trim()) throw new MockApiError('VALIDATION_ERROR', '裁决理由必填')
    })
    // 后端退款处理：action refund→approve，reject→reject；仅真实退款单穿透
    const backendId = toUuid(id)
    if (backendId !== id) {
      const result = await bridgeRequest(`/admin/refunds/${backendId}/handle`, {
        method: 'POST',
        body: { action: action === 'refund' ? 'approve' : 'reject', note: reason.trim() },
        role: 'admin'
      })
      if (!result.ok)
        throw new MockApiError('BACKEND_ERROR', `后端退款裁决失败（HTTP ${result.status}）`)
    }
    return mockCall(() => {
      const db = getDb()
      const aftersale = db.aftersales.find((item) => item.id === id)
      if (!aftersale) throw new MockApiError('NOT_FOUND', '售后单不存在')
      const admin = currentAdmin()
      const order = db.orders.find((item) => item.id === aftersale.orderId)
      const now = new Date().toISOString()
      aftersale.status = action === 'refund' ? 'refunded' : 'rejected'
      aftersale.adminReason = reason.trim()
      aftersale.handledAt = now
      if (order) {
        if (action === 'refund') {
          order.refundAmount = toMoney(Number(order.refundAmount) + Number(aftersale.amount))
          order.status =
            Number(order.refundAmount) >= Number(order.payAmount)
              ? 'refunded'
              : 'partially_refunded'
          order.statusLogs.push({
            time: now,
            action: 'arbitrate_refund',
            status: order.status,
            operator: admin.name,
            note: reason
          })
          applySettlementRefund(aftersale.merchantId, aftersale.amount)
        } else {
          order.refundAmount = '0.00'
          order.status = order.completedAt ? 'completed' : order.shipment ? 'shipped' : 'paid'
          order.statusLogs.push({
            time: now,
            action: 'arbitrate_reject',
            status: order.status,
            operator: admin.name,
            note: reason
          })
        }
        aftersale.orderRefundAmount = order.refundAmount
      }
      saveDb()
      adminLog(
        'aftersale.arbitrate',
        '售后',
        aftersale.refundNo,
        `${action === 'refund' ? '支持退款' : '驳回退款'}：${reason}`,
        'high'
      )
      return clone(aftersale)
    })
  },

  async origins(keyword?: string) {
    return mockCall(() => {
      let items = getDb().origins.slice()
      if (keyword?.trim()) {
        const word = keyword.trim()
        items = items.filter(
          (item) =>
            item.name.includes(word) ||
            item.location.includes(word) ||
            item.productName.includes(word)
        )
      }
      items.sort((a, b) => b.totals.sales - a.totals.sales)
      return clone(items)
    })
  },

  async originMonths(): Promise<string[]> {
    return mockCall(() => clone(getDb().originMonths))
  },

  async updateOrigin(
    id: string,
    payload: { tagline: string; productCount: number }
  ): Promise<{ id: string }> {
    return mockCall(() => {
      const db = getDb()
      const origin = db.origins.find((item) => item.id === id)
      if (!origin) throw new MockApiError('NOT_FOUND', '产地不存在')
      origin.tagline = payload.tagline
      origin.productCount = payload.productCount
      saveDb()
      adminLog('origin.update', '助农', origin.name, '更新产地展示信息', 'normal')
      return clone({ id })
    })
  },

  async members(query: MockPageQuery): Promise<PageResult<Member>> {
    return mockCall(() => {
      const db = getDb()
      let items = db.members.slice()
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      const keyword = (query.keyword || '').trim().toLowerCase()
      if (keyword) {
        items = items.filter(
          (item) =>
            item.nickname.toLowerCase().includes(keyword) ||
            item.phone.includes(keyword) ||
            item.email.toLowerCase().includes(keyword)
        )
      }
      items.sort(byDateDesc)
      return clone(mockPaginate(items, query))
    })
  },

  async memberStats(): Promise<Record<string, number>> {
    return mockCall(() => {
      const members = getDb().members
      return {
        all: members.length,
        active: members.filter((item) => item.status === 'active').length,
        banned: members.filter((item) => item.status === 'banned').length
      }
    })
  },

  async memberDetail(id: string): Promise<MemberDetail> {
    return mockCall(() => {
      const db = getDb()
      const member = db.members.find((item) => item.id === id)
      if (!member) throw new MockApiError('NOT_FOUND', '用户不存在')
      return clone({
        member,
        orders: db.orders.filter((item) => item.buyerPhone === member.phone).slice(0, 8),
        aftersales: db.aftersales.filter((item) => item.buyerPhone === member.phone).slice(0, 5)
      })
    })
  },

  async announcements(query: MockPageQuery): Promise<PageResult<Announcement>> {
    await ensureSynced('admin')
    return mockCall(() => {
      const db = getDb()
      let items = db.announcements.slice()
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      const keyword = (query.keyword || '').trim().toLowerCase()
      if (keyword) {
        items = items.filter(
          (item) =>
            item.title.toLowerCase().includes(keyword) ||
            item.content.toLowerCase().includes(keyword)
        )
      }
      items.sort(byDateDesc)
      return clone(mockPaginate(items, query))
    })
  },

  async announcementStats(): Promise<Record<string, number>> {
    return mockCall(() => {
      const items = getDb().announcements
      return {
        all: items.length,
        draft: items.filter((item) => item.status === 'draft').length,
        published: items.filter((item) => item.status === 'published').length,
        offline: items.filter((item) => item.status === 'offline').length
      }
    })
  },

  async saveAnnouncement(input: AnnouncementInput): Promise<Announcement> {
    if (!input.title.trim() || !input.content.trim()) {
      throw new MockApiError('VALIDATION_ERROR', '标题与内容必填')
    }
    const backendId = input.id ? toUuid(input.id) : ''
    const isReal = backendId !== (input.id || '')
    let backendUuid = isReal ? backendId : ''
    if (isReal) {
      // 真实公告：无法经本接口改正文（后端无更新端点），仅保留本地编辑。
      return mockCall(() => this.saveAnnouncementLocal(input))
    }
    // 新建公告：先在后端创建草稿，拿到 UUID 后建立 ID 映射，确保发布后消费者可见。
    const createResult = await bridgeRequest<{ data?: { id?: string }; code?: string }>(
      '/cms/announcements',
      {
        method: 'POST',
        body: { title: input.title.trim(), content: input.content.trim() },
        role: 'admin'
      }
    )
    const created = unwrap(createResult)
    if (created?.id) backendUuid = String(created.id)
    return mockCall(() => {
      const announcement = this.saveAnnouncementLocal(input)
      // 立即（同步）绑定 mockId ↔ 后端 UUID，避免随后 publish 时映射未就绪
      if (backendUuid) bindId(announcement.id, backendUuid)
      return announcement
    })
  },

  saveAnnouncementLocal(input: AnnouncementInput): Announcement {
    const db = getDb()
    const admin = currentAdmin()
    let announcement = input.id ? db.announcements.find((item) => item.id === input.id) : undefined
    if (!announcement) {
      announcement = {
        id: `ann-${Date.now()}`,
        title: input.title.trim(),
        content: input.content.trim(),
        status: 'draft',
        author: admin.name,
        createdAt: new Date().toISOString()
      }
      db.announcements.unshift(announcement)
    } else {
      announcement.title = input.title.trim()
      announcement.content = input.content.trim()
    }
    saveDb()
    adminLog('cms.announcement_save', '内容', announcement.title, '保存平台公告', 'normal')
    return clone(announcement)
  },

  async publishAnnouncement(id: string): Promise<Announcement> {
    const backendId = toUuid(id)
    const isReal = backendId !== id
    if (isReal) {
      const result = await bridgeRequest(`/cms/announcements/${backendId}/publish`, {
        method: 'POST',
        role: 'admin'
      })
      if (!result.ok) throw new MockApiError('BACKEND_ERROR', '后端发布公告失败，请稍后重试')
    }
    return mockCall(() => {
      const db = getDb()
      const announcement = db.announcements.find((item) => item.id === id)
      if (!announcement) throw new MockApiError('NOT_FOUND', '公告不存在')
      announcement.status = 'published'
      announcement.publishedAt = new Date().toISOString()
      saveDb()
      adminLog('cms.announcement_publish', '内容', announcement.title, '发布平台公告', 'normal')
      return clone(announcement)
    })
  },

  async offlineAnnouncement(id: string): Promise<Announcement> {
    const backendId = toUuid(id)
    const isReal = backendId !== id
    if (isReal) {
      const result = await bridgeRequest(`/cms/announcements/${backendId}/offline`, {
        method: 'POST',
        role: 'admin'
      })
      if (!result.ok) throw new MockApiError('BACKEND_ERROR', '后端下线公告失败，请稍后重试')
    }
    return mockCall(() => {
      const db = getDb()
      const announcement = db.announcements.find((item) => item.id === id)
      if (!announcement) throw new MockApiError('NOT_FOUND', '公告不存在')
      announcement.status = 'offline'
      saveDb()
      adminLog('cms.announcement_offline', '内容', announcement.title, '下线平台公告', 'normal')
      return clone(announcement)
    })
  },

  async settlements(query: MockPageQuery): Promise<PageResult<Settlement>> {
    return mockCall(() => {
      const db = getDb()
      let items = db.settlements.slice()
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      if (query.storeId) {
        items = items.filter((item) => item.storeId === query.storeId)
      }
      const keyword = (query.keyword || '').trim()
      if (keyword) {
        items = items.filter(
          (item) => item.settlementNo.includes(keyword) || item.storeName.includes(keyword)
        )
      }
      items.sort(byDateDesc)
      return clone(mockPaginate(items, query))
    })
  },

  async settlementStats(): Promise<Record<string, number>> {
    return mockCall(() => {
      const items = getDb().settlements
      return {
        all: items.length,
        pending: items.filter((item) => item.status === 'pending').length,
        confirmed: items.filter((item) => item.status === 'confirmed').length,
        paid: items.filter((item) => item.status === 'paid').length
      }
    })
  },

  async settlementBills(id: string): Promise<SettlementBill[]> {
    return mockCall(() => {
      const db = getDb()
      const settlement = db.settlements.find((item) => item.id === id)
      if (!settlement) throw new MockApiError('NOT_FOUND', '结算单不存在')
      const orders = db.orders
        .filter((item) => item.storeId === settlement.storeId)
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

  async confirmSettlement(id: string): Promise<Settlement> {
    return mockCall(() => {
      const db = getDb()
      const settlement = db.settlements.find((item) => item.id === id)
      if (!settlement) throw new MockApiError('NOT_FOUND', '结算单不存在')
      if (settlement.status !== 'pending') {
        throw new MockApiError('CONFLICT', '仅待确认结算单可确认')
      }
      settlement.status = 'confirmed'
      settlement.confirmedAt = new Date().toISOString()
      saveDb()
      adminLog(
        'finance.settlement_confirm',
        '财务',
        settlement.settlementNo,
        `确认结算 ¥${settlement.payable}`,
        'normal'
      )
      return clone(settlement)
    })
  },

  async paySettlement(id: string): Promise<Settlement> {
    return mockCall(() => {
      const db = getDb()
      const settlement = db.settlements.find((item) => item.id === id)
      if (!settlement) throw new MockApiError('NOT_FOUND', '结算单不存在')
      if (settlement.status !== 'confirmed') {
        throw new MockApiError('CONFLICT', '仅已确认结算单可打款')
      }
      settlement.status = 'paid'
      settlement.paidAt = new Date().toISOString()
      const balance = db.balances[settlement.merchantId]
      if (balance) {
        balance.available = toMoney(Number(balance.available) + Number(settlement.payable))
        balance.pendingSettlement = toMoney(
          Math.max(0, Number(balance.pendingSettlement) - Number(settlement.payable))
        )
        balance.total = toMoney(
          Number(balance.available) + Number(balance.frozen) + Number(balance.pendingSettlement)
        )
      }
      saveDb()
      adminLog(
        'finance.settlement_pay',
        '财务',
        settlement.settlementNo,
        `结算打款 ¥${settlement.payable}`,
        'normal'
      )
      return clone(settlement)
    })
  },

  async previewSettlement(
    storeId: string,
    periodStart: string,
    periodEnd: string
  ): Promise<SettlementPreview> {
    return mockCall(() => {
      const db = getDb()
      const store = findStore(storeId)
      if (!periodStart || !periodEnd) {
        throw new MockApiError('VALIDATION_ERROR', '请选择结算周期')
      }
      const start = new Date(`${periodStart}T00:00:00+08:00`).getTime()
      const end = new Date(`${periodEnd}T23:59:59+08:00`).getTime()
      if (end < start) throw new MockApiError('VALIDATION_ERROR', '结束日期不能早于开始日期')
      const orders = db.orders.filter((item) => {
        const time = new Date(item.createdAt).getTime()
        return (
          item.storeId === storeId &&
          time >= start &&
          time <= end &&
          item.status !== 'pending_payment' &&
          item.status !== 'cancelled'
        )
      })
      const ordersTotal = orders.reduce(
        (sum, item) => sum + Number(item.payAmount) - Number(item.refundAmount),
        0
      )
      const commission = ordersTotal * (Number(db.commissionRate) / 100)
      return clone({
        storeId,
        storeName: store.name,
        periodStart,
        periodEnd,
        orderCount: orders.length,
        ordersTotal: toMoney(ordersTotal),
        commission: toMoney(commission),
        payable: toMoney(ordersTotal - commission)
      })
    })
  },

  async generateSettlement(
    storeId: string,
    periodStart: string,
    periodEnd: string
  ): Promise<Settlement> {
    return mockCall(() => {
      const db = getDb()
      const store = findStore(storeId)
      if (!periodStart || !periodEnd) {
        throw new MockApiError('VALIDATION_ERROR', '请选择结算周期')
      }
      const start = new Date(`${periodStart}T00:00:00+08:00`).getTime()
      const end = new Date(`${periodEnd}T23:59:59+08:00`).getTime()
      if (end < start) throw new MockApiError('VALIDATION_ERROR', '结束日期不能早于开始日期')
      const duplicate = db.settlements.find(
        (item) =>
          item.storeId === storeId &&
          new Date(item.periodStart).getTime() === start &&
          new Date(item.periodEnd).getTime() === end
      )
      if (duplicate) throw new MockApiError('CONFLICT', '该店铺与周期已存在结算单')
      const orders = db.orders.filter((item) => {
        const time = new Date(item.createdAt).getTime()
        return (
          item.storeId === storeId &&
          time >= start &&
          time <= end &&
          item.status !== 'pending_payment' &&
          item.status !== 'cancelled'
        )
      })
      const ordersTotal = orders.reduce(
        (sum, item) => sum + Number(item.payAmount) - Number(item.refundAmount),
        0
      )
      const commission = ordersTotal * (Number(db.commissionRate) / 100)
      const settlement: Settlement = {
        id: `st-${Date.now()}`,
        settlementNo: `ST${new Date().getFullYear()}${String(Date.now()).slice(-6)}`,
        merchantId: store.merchantId,
        storeId: store.id,
        storeName: store.name,
        periodStart: new Date(start).toISOString(),
        periodEnd: new Date(end).toISOString(),
        orderCount: orders.length,
        ordersTotal: toMoney(ordersTotal),
        commission: toMoney(commission),
        payable: toMoney(ordersTotal - commission),
        refundDeduct: '0.00',
        status: 'pending',
        createdAt: new Date().toISOString()
      }
      db.settlements.unshift(settlement)
      saveDb()
      adminLog(
        'finance.settlement_generate',
        '财务',
        settlement.settlementNo,
        `生成结算单：${store.name} ${periodStart} 至 ${periodEnd}`,
        'normal'
      )
      return clone(settlement)
    })
  },

  async withdrawals(query: MockPageQuery): Promise<PageResult<AdminWithdrawalRow>> {
    return mockCall(() => {
      const db = getDb()
      let items = db.withdrawals.slice()
      if (query.status && query.status !== 'all') {
        items = items.filter((item) => item.status === query.status)
      }
      const keyword = (query.keyword || '').trim().toLowerCase()
      if (keyword) {
        items = items.filter((item) => {
          const merchant = db.merchants.find((entry) => entry.id === item.merchantId)
          return (
            item.accountName.toLowerCase().includes(keyword) ||
            item.bankName.toLowerCase().includes(keyword) ||
            Boolean(merchant?.companyName.toLowerCase().includes(keyword))
          )
        })
      }
      items.sort(byDateDesc)
      const rows: AdminWithdrawalRow[] = items.map((item) => {
        const merchant = db.merchants.find((entry) => entry.id === item.merchantId)
        const store = db.stores.find((entry) => entry.merchantId === item.merchantId)
        return {
          ...item,
          merchantName: merchant?.companyName || '—',
          storeName: store?.name || '—'
        }
      })
      return clone(mockPaginate(rows, query))
    })
  },

  async withdrawalStats(): Promise<Record<string, number>> {
    return mockCall(() => {
      const items = getDb().withdrawals
      return {
        all: items.length,
        pending: items.filter((item) => item.status === 'pending').length,
        approved: items.filter((item) => item.status === 'approved').length,
        rejected: items.filter((item) => item.status === 'rejected').length
      }
    })
  },

  async reviewWithdrawal(
    id: string,
    action: 'approve' | 'reject',
    reason?: string
  ): Promise<AdminWithdrawalRow> {
    return mockCall(() => {
      const db = getDb()
      const withdrawal = db.withdrawals.find((item) => item.id === id)
      if (!withdrawal) throw new MockApiError('NOT_FOUND', '提现单不存在')
      if (withdrawal.status !== 'pending') {
        throw new MockApiError('CONFLICT', '该提现单已处理')
      }
      if (action === 'reject' && !reason?.trim()) {
        throw new MockApiError('VALIDATION_ERROR', '驳回原因必填')
      }
      const balance = db.balances[withdrawal.merchantId]
      const amount = Number(withdrawal.amount)
      if (balance) {
        balance.frozen = toMoney(Math.max(0, Number(balance.frozen) - amount))
        if (action === 'approve') {
          balance.withdrawn = toMoney(Number(balance.withdrawn) + amount)
        } else {
          balance.available = toMoney(Number(balance.available) + amount)
        }
        balance.total = toMoney(
          Number(balance.available) + Number(balance.frozen) + Number(balance.pendingSettlement)
        )
      }
      withdrawal.status = action === 'approve' ? 'approved' : 'rejected'
      withdrawal.handledAt = new Date().toISOString()
      withdrawal.reason = action === 'reject' ? reason?.trim() : undefined
      saveDb()
      const merchant = db.merchants.find((item) => item.id === withdrawal.merchantId)
      adminLog(
        'withdrawal.review',
        '财务',
        merchant?.companyName || withdrawal.id,
        `${action === 'approve' ? '通过' : '驳回'}提现 ¥${withdrawal.amount}${
          action === 'reject' ? `：${reason}` : ''
        }`,
        'high'
      )
      const store = db.stores.find((item) => item.merchantId === withdrawal.merchantId)
      return clone({
        ...withdrawal,
        merchantName: merchant?.companyName || '—',
        storeName: store?.name || '—'
      })
    })
  },

  async commission(): Promise<CommissionSettings> {
    return mockCall(() => {
      const db = getDb()
      return {
        rate: db.commissionRate,
        cycle: db.settings.settleCycle || 'T+7',
        minWithdrawal: db.settings.minWithdrawal || '100.00',
        autoConfirm: db.settings.autoConfirm === '1'
      }
    })
  },

  async saveCommission(payload: CommissionSettings): Promise<CommissionSettings> {
    return mockCall(() => {
      const db = getDb()
      const rate = Number(payload.rate)
      if (!Number.isFinite(rate) || rate < 0 || rate > 30) {
        throw new MockApiError('VALIDATION_ERROR', '平台佣金比例需为 0–30 之间')
      }
      db.commissionRate = rate.toFixed(2)
      db.settings.settleCycle = payload.cycle
      db.settings.minWithdrawal = payload.minWithdrawal
      db.settings.autoConfirm = payload.autoConfirm ? '1' : '0'
      saveDb()
      adminLog(
        'finance.commission_update',
        '财务',
        '平台佣金设置',
        `佣金比例 ${db.commissionRate}%，结算周期 ${payload.cycle}`,
        'high'
      )
      return clone(payload)
    })
  },

  async admins(): Promise<AdminAccount[]> {
    return mockCall(() => clone(getDb().admins))
  },

  async createAdmin(input: AdminAccountInput): Promise<AdminAccount> {
    return mockCall(() => {
      const db = getDb()
      if (!input.username.trim() || !input.name.trim()) {
        throw new MockApiError('VALIDATION_ERROR', '账号与姓名必填')
      }
      if (db.admins.some((item) => item.username === input.username.trim())) {
        throw new MockApiError('CONFLICT', '管理账号已存在')
      }
      const role = db.roles.find((item) => item.code === input.roleCode)
      if (!role) throw new MockApiError('VALIDATION_ERROR', '角色不存在')
      const admin: AdminAccount = {
        id: `a-${Date.now()}`,
        username: input.username.trim(),
        name: input.name.trim(),
        roleCode: role.code,
        roleName: role.name,
        permissions: role.permissions,
        status: 'active',
        avatar: assetUrl('/console-assets/images/avatar-admin.webp'),
        lastLoginAt: '—',
        createdAt: new Date().toISOString()
      }
      db.admins.push(admin)
      saveDb()
      adminLog('rbac.admin_create', '系统', admin.username, `创建管理员账号：${admin.name}`, 'high')
      return clone(admin)
    })
  },

  async toggleAdmin(id: string): Promise<AdminAccount> {
    return mockCall(() => {
      const db = getDb()
      const admin = db.admins.find((item) => item.id === id)
      if (!admin) throw new MockApiError('NOT_FOUND', '管理员不存在')
      const current = currentAdmin()
      if (current.id === id && admin.status === 'active') {
        throw new MockApiError('CONFLICT', '不能禁用当前登录账号')
      }
      admin.status = admin.status === 'active' ? 'disabled' : 'active'
      saveDb()
      adminLog(
        'rbac.admin_toggle',
        '系统',
        admin.username,
        `${admin.status === 'active' ? '启用' : '禁用'}管理员账号`,
        'high'
      )
      return clone(admin)
    })
  },

  async resetAdminPassword(id: string): Promise<void> {
    return mockCall(() => {
      const db = getDb()
      const admin = db.admins.find((item) => item.id === id)
      if (!admin) throw new MockApiError('NOT_FOUND', '管理员不存在')
      admin.password = 'Demo@123456'
      saveDb()
      adminLog('rbac.admin_reset_password', '系统', admin.username, '重置管理员密码', 'high')
    })
  },

  async roles(): Promise<AdminRole[]> {
    return mockCall(() => clone(getDb().roles))
  },

  async updateRolePermissions(
    code: AdminAccount['roleCode'],
    permissions: string[]
  ): Promise<AdminRole> {
    return mockCall(() => {
      const db = getDb()
      const role = db.roles.find((item) => item.code === code)
      if (!role) throw new MockApiError('NOT_FOUND', '角色不存在')
      if (role.code === 'super_admin') {
        throw new MockApiError('CONFLICT', '超级管理员权限不可修改')
      }
      role.permissions = [...permissions]
      db.admins
        .filter((item) => item.roleCode === code)
        .forEach((item) => {
          item.permissions = [...permissions]
        })
      saveDb()
      adminLog(
        'rbac.role_update',
        '系统',
        role.name,
        `修改角色权限：${permissions.join(', ') || '无'}`,
        'high'
      )
      return clone(role)
    })
  },

  async logs(query: MockPageQuery): Promise<PageResult<OperationLog>> {
    return mockCall(() => {
      const db = getDb()
      let items = db.logs.slice()
      if (query.module && query.module !== 'all') {
        items = items.filter((item) => item.module === query.module)
      }
      if (query.risk && query.risk !== 'all') {
        items = items.filter((item) => item.risk === query.risk)
      }
      const keyword = (query.keyword || '').trim().toLowerCase()
      if (keyword) {
        items = items.filter(
          (item) =>
            item.actor.toLowerCase().includes(keyword) ||
            item.actorName.toLowerCase().includes(keyword) ||
            item.action.toLowerCase().includes(keyword) ||
            item.target.toLowerCase().includes(keyword) ||
            item.detail.toLowerCase().includes(keyword)
        )
      }
      if (query.date_from || query.date_to) {
        items = items.filter((item) => inDateRange(item.createdAt, query.date_from, query.date_to))
      }
      items.sort(byDateDesc)
      return clone(mockPaginate(items, query))
    })
  },

  async settings(): Promise<Record<string, string>> {
    return mockCall(() => clone(getDb().settings))
  },

  async saveSettings(payload: Record<string, string>): Promise<Record<string, string>> {
    return mockCall(() => {
      const db = getDb()
      const allowed = ['platformName', 'servicePhone', 'serviceEmail', 'address', 'icp', 'notice']
      allowed.forEach((key) => {
        if (typeof payload[key] === 'string') db.settings[key] = payload[key]
      })
      saveDb()
      adminLog('settings.update', '系统', '平台基础配置', '更新平台基础设置', 'high')
      return clone(db.settings)
    })
  },

  async storeOptions(): Promise<Array<{ id: string; name: string; merchantId: string }>> {
    return mockCall(() =>
      clone(
        getDb().stores.map((item) => ({
          id: item.id,
          name: item.name,
          merchantId: item.merchantId
        }))
      )
    )
  }
}
