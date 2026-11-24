/**
 * 后端 DTO → 管理端 mock 类型的映射函数。
 * 只映射桥接权威实体共有的字段；mock 独有字段由调用方保留原值。
 */
import { assetUrl } from '@/api/http'
import type {
  Aftersale,
  Announcement,
  Category,
  MerchantAccount,
  Order,
  OrderStatus,
  Product
} from '../types'
import { mockIdFor, uuidFor } from './identity'

function toIso(value?: string | null): string {
  if (!value) return new Date().toISOString()
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString()
}

function str(value: unknown, fallback = ''): string {
  return value === null || value === undefined ? fallback : String(value)
}

/** 后端 store order 详情 → 管理端 Order。prefix 区分真实订单(r)与演示订单(o)。 */
export function mapOrder(
  raw: Record<string, unknown>,
  storeName: string,
  merchantId: string,
  prefix: 'o' | 'r' = 'r'
): Order {
  const id = str(raw.id)
  const mockId = mockIdFor(id, prefix)
  const itemsRaw = Array.isArray(raw.items) ? (raw.items as Record<string, unknown>[]) : []
  const status = str(raw.status, 'paid') as OrderStatus
  const shippedAt = raw.shipped_at ? toIso(str(raw.shipped_at)) : undefined
  const completedAt = raw.completed_at ? toIso(str(raw.completed_at)) : undefined
  const createdAt = toIso(str(raw.created_at))
  const statusLogs: Order['statusLogs'] = [
    { time: createdAt, action: 'create', status: 'pending_payment', operator: '买家' }
  ]
  if (status !== 'pending_payment' && status !== 'cancelled') {
    statusLogs.push({
      time: createdAt,
      action: 'payment_success',
      status: 'paid',
      operator: '系统'
    })
  }
  if (shippedAt)
    statusLogs.push({ time: shippedAt, action: 'ship', status: 'shipped', operator: '商家' })
  if (completedAt)
    statusLogs.push({
      time: completedAt,
      action: 'confirm_receipt',
      status: 'completed',
      operator: '买家'
    })

  return {
    id: mockId,
    orderNo: str(raw.store_order_no || raw.order_no),
    merchantId,
    storeId: str(raw.store_id),
    storeName,
    buyerName: str(raw.receiver_name, '消费者'),
    buyerPhone: str(raw.receiver_phone),
    buyerEmail: '',
    address: str(raw.address),
    items: itemsRaw.map((item, index) => ({
      id: str(item.id, `${mockId}-i${index + 1}`),
      productId: str(item.product_id),
      title: str(item.title, '商品'),
      spec: str(item.spec, '默认规格'),
      price: str(item.unit_price, '0.00'),
      quantity: Number(item.quantity) || 1,
      image: str(item.image_url)
    })),
    itemsTotal: str(raw.items_total, '0.00'),
    shippingFee: str(raw.shipping_fee, '0.00'),
    payAmount: str(raw.pay_amount, '0.00'),
    refundAmount: str(raw.refund_amount, '0.00'),
    status,
    createdAt,
    paidAt: status === 'pending_payment' || status === 'cancelled' ? undefined : createdAt,
    shippedAt,
    completedAt,
    statusLogs
  }
}

/** 后端 ProductOut / ProductDetailOut → 管理端 Product。 */
export function mapProduct(raw: Record<string, unknown>, fallback: Partial<Product> = {}): Product {
  const id = str(raw.id)
  const mockId = mockIdFor(id, 'g')
  const statusMap: Record<string, Product['status']> = {
    draft: 'draft',
    pending_review: 'pending_review',
    approved: 'approved',
    rejected: 'rejected',
    removed: 'removed'
  }
  const status = statusMap[str(raw.status, 'approved')] || 'approved'
  const imagesRaw = Array.isArray(raw.images) ? (raw.images as Record<string, unknown>[]) : []
  const skusRaw = Array.isArray(raw.skus) ? (raw.skus as Record<string, unknown>[]) : []
  const price = str(raw.min_price, '') || str(skusRaw[0]?.price, '') || fallback.price || '0.00'
  const cover = str(raw.cover_url) || fallback.cover || ''

  return {
    id: mockId,
    merchantId: fallback.merchantId || '',
    storeId: str(raw.store_id),
    storeName: str(raw.store_name, fallback.storeName || ''),
    title: str(raw.title, '商品'),
    subtitle: str(raw.subtitle, fallback.subtitle || ''),
    categoryId: str(raw.category_id, fallback.categoryId || ''),
    categoryName: fallback.categoryName || '',
    description: str(raw.description, fallback.description || ''),
    price,
    minPrice: str(raw.min_price, price),
    stock: fallback.stock ?? 0,
    sales: fallback.sales ?? 0,
    status,
    listed: raw.is_listed === true,
    cover,
    images: imagesRaw.map((img) => str(img.url)).filter(Boolean),
    skus: skusRaw.map((sku, index) => ({
      id: str(sku.id, `${mockId}-sku${index + 1}`),
      spec: str(sku.spec, '默认规格'),
      price: str(sku.price, price),
      stock: fallback.skus?.[index]?.stock ?? 0,
      code: str(sku.code, '')
    })),
    shippingTemplateId: fallback.shippingTemplateId || '',
    greenProfile: fallback.greenProfile || {
      origin: '',
      plantingMode: '',
      description: '',
      status: 'draft'
    },
    aidProjectId: str(raw.aid_project_id, '') || undefined,
    aidProjectName: fallback.aidProjectName,
    auditReason: str(raw.audit_reason, '') || undefined,
    auditedAt: raw.audited_at ? toIso(str(raw.audited_at)) : undefined,
    auditRecords: fallback.auditRecords || [],
    createdAt: toIso(str(raw.created_at)),
    updatedAt: fallback.updatedAt || toIso(str(raw.created_at))
  }
}

/** 后端 Refund → 管理端 Aftersale。 */
export function mapAftersale(
  raw: Record<string, unknown>,
  storeName: string,
  merchantId: string
): Aftersale {
  const id = str(raw.id)
  const mockId = mockIdFor(id, 'as')
  const statusMap: Record<string, Aftersale['status']> = {
    requested: 'requested',
    pending: 'requested',
    arbitrating: 'arbitrating',
    approved: 'refunded',
    refunded: 'refunded',
    rejected: 'rejected'
  }
  return {
    id: mockId,
    refundNo: str(raw.refund_no),
    orderId: str(raw.order_id),
    orderNo: str(raw.store_order_no || raw.order_no),
    merchantId,
    storeId: str(raw.store_id),
    storeName,
    buyerName: '消费者',
    buyerPhone: '',
    amount: str(raw.amount, '0.00'),
    reason: str(raw.reason, '退款申请'),
    evidence: [],
    status: statusMap[str(raw.status)] || 'requested',
    adminReason: str(raw.result_note, '') || undefined,
    createdAt: toIso(str(raw.created_at)),
    handledAt: raw.handled_at ? toIso(str(raw.handled_at)) : undefined,
    orderPayAmount: str(raw.pay_amount, '0.00'),
    orderRefundAmount: str(raw.refund_amount, '0.00')
  }
}

/** 后端 Announcement(client) → 管理端 Announcement。 */
export function mapAnnouncement(raw: Record<string, unknown>): Announcement {
  const id = str(raw.id)
  const mockId = mockIdFor(id, 'ann')
  return {
    id: mockId,
    title: str(raw.title, '公告'),
    content: str(raw.content),
    status: raw.published_at ? 'published' : 'draft',
    author: '平台运营',
    createdAt: toIso(str(raw.created_at)),
    publishedAt: raw.published_at ? toIso(str(raw.published_at)) : undefined
  }
}

/** 后端 Category → 管理端 Category。 */
export function mapCategory(raw: Record<string, unknown>): Category {
  const id = str(raw.id)
  const mockId = mockIdFor(id, 'cat')
  return {
    id: mockId,
    name: str(raw.name, '分类'),
    parentId: raw.parent_id ? mockForId(str(raw.parent_id)) : undefined,
    productCount: 0,
    sort: Number(raw.sort) || 0,
    enabled: true
  }
}

function mockForId(uuid: string): string {
  // 延迟引入避免循环
  const map = loadMap()
  return map[uuid] || uuid
}

function loadMap(): Record<string, string> {
  try {
    const raw = localStorage.getItem('tanhui_console_id_map_v1')
    if (!raw) return {}
    return (JSON.parse(raw) as { uuidToMock: Record<string, string> }).uuidToMock || {}
  } catch {
    return {}
  }
}

/** 后端 MerchantOut → 管理端 MerchantAccount（状态词汇对齐管理端）。 */
export function mapMerchant(
  raw: Record<string, unknown>,
  fallback: Partial<MerchantAccount> = {}
): MerchantAccount {
  const id = str(raw.id)
  const mockId = mockIdFor(id, 'm')
  const statusMap: Record<string, MerchantAccount['status']> = {
    pending_review: 'pending',
    approved: 'normal',
    active: 'normal',
    rejected: 'rejected',
    frozen: 'frozen'
  }
  const status = statusMap[str(raw.status)] || 'pending'
  return {
    id: mockId,
    username: fallback.username || `${str(raw.company_name, 'merchant').slice(0, 12)}-${mockId}`,
    password: fallback.password || 'Demo@123456',
    companyName: str(raw.company_name, '商家'),
    storeName: str(raw.initial_store_name, fallback.storeName || str(raw.company_name, '商家')),
    ownerName: str(raw.legal_person, fallback.ownerName || '负责人'),
    phone: str(raw.contact_phone, fallback.phone || ''),
    email: fallback.email || '',
    region: str(raw.region, fallback.region || ''),
    licenseNo: str(raw.license_no, ''),
    licenseImage: fallback.licenseImage || str(raw.license_url, ''),
    status,
    rejectReason: str(raw.reject_reason, '') || undefined,
    frozenReason: fallback.frozenReason,
    createdAt: toIso(str(raw.created_at)),
    reviewedAt: raw.reviewed_at ? toIso(str(raw.reviewed_at)) : undefined,
    avatar: fallback.avatar || assetUrl('/console-assets/images/avatar-merchant.png')
  }
}

/** 反向：管理端 ID → 后端 UUID。 */
export const toUuid = uuidFor
