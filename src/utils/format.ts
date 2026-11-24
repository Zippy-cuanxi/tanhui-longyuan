import { assetUrl } from '@/api/http'
import type { Product } from '@/api/types'

export function money(value?: string | number | null): string {
  if (value === null || value === undefined || value === '') return '—'
  const text = String(value)
  if (!/^-?\d+(\.\d{1,4})?$/.test(text)) return text
  const negative = text.startsWith('-')
  const [integer, fraction = ''] = (negative ? text.slice(1) : text).split('.')
  const decimals = fraction.length > 2 ? fraction.slice(0, 2) : fraction.padEnd(2, '0')
  return `${negative ? '-' : ''}${integer}.${decimals}`
}

export function integer(value?: number | null): string {
  if (value === null || value === undefined) return '0'
  return new Intl.NumberFormat('zh-CN').format(value)
}

export function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`
}

export function toDateInput(iso?: string | null): string {
  if (!iso) return ''
  return iso.slice(0, 10)
}

export const ORDER_STATUS_LABELS: Record<string, string> = {
  pending_payment: '待付款',
  paid: '待发货',
  shipped: '待收货',
  completed: '已完成',
  cancelled: '已取消',
  refunding: '退款中',
  refunded: '已退款',
  partially_refunded: '部分退款'
}

export function orderStatusLabel(status?: string | null): string {
  return (status && ORDER_STATUS_LABELS[status]) || status || '未知状态'
}

export function orderStatusTone(status?: string | null): string {
  switch (status) {
    case 'pending_payment':
      return 'warning'
    case 'paid':
      return 'info'
    case 'shipped':
      return 'primary'
    case 'completed':
      return 'success'
    case 'refunding':
    case 'partially_refunded':
      return 'warning'
    case 'refunded':
    case 'cancelled':
      return 'muted'
    default:
      return 'muted'
  }
}

export const REFUND_STATUS_LABELS: Record<string, string> = {
  requested: '待处理',
  approved: '已通过',
  refunded: '已退款',
  rejected: '已驳回'
}

export function refundStatusLabel(status?: string | null): string {
  return (status && REFUND_STATUS_LABELS[status]) || status || '—'
}

export const POINT_TYPE_LABELS: Record<string, string> = {
  earn: '获得',
  spend: '消费',
  reverse: '冲正',
  adjust: '调整'
}

export function pointTypeLabel(type?: string | null): string {
  return (type && POINT_TYPE_LABELS[type]) || type || '积分'
}

export const NOTIFICATION_TYPE_LABELS: Record<string, string> = {
  order_created: '订单创建',
  order_paid: '支付成功',
  order_shipped: '订单发货',
  order_completed: '订单完成',
  order_cancelled: '订单取消',
  refund_requested: '退款申请',
  refund_done: '退款完成',
  refund_rejected: '退款驳回'
}

export function notificationTypeLabel(type?: string | null): string {
  return (type && NOTIFICATION_TYPE_LABELS[type]) || '通知'
}

export const DESIGN_CATEGORY_ORDER = [
  '水果生鲜',
  '粮油杂粮',
  '特色食品',
  '中药材',
  '甘肃特产',
  '文创礼品'
]

export function categoryIcon(name?: string | null): string {
  const text = name || ''
  if (/水果|生鲜|苹果|蜜瓜/.test(text)) return assetUrl('/images/categories/flat/fruit.png')
  if (/粮油|杂粮|马铃薯|土豆|米面/.test(text)) return assetUrl('/images/categories/flat/grains.png')
  if (/文创|礼品|非遗/.test(text)) return assetUrl('/images/categories/flat/culture.png')
  if (/积分|绿色/.test(text)) return assetUrl('/images/categories/flat/points.png')
  return assetUrl('/images/categories/flat/food.png')
}

export function linearCategoryIcon(name?: string | null): string {
  const text = name || ''
  if (/水果|生鲜|苹果|蜜瓜/.test(text)) return assetUrl('/images/categories/linear/fruit.png')
  if (/粮油|杂粮|马铃薯|土豆|米面/.test(text)) return assetUrl('/images/categories/linear/grains.png')
  if (/文创|礼品|非遗/.test(text)) return assetUrl('/images/categories/linear/culture.png')
  if (/积分|绿色/.test(text)) return assetUrl('/images/categories/linear/points.png')
  return assetUrl('/images/categories/linear/food.png')
}

export function productFallbackImage(title?: string | null): string {
  const text = title || ''
  if (/苹果/.test(text)) return assetUrl('/images/products/jingning-apple.webp')
  if (/马铃薯|土豆/.test(text)) return assetUrl('/images/products/dingxi-potato.webp')
  if (/蜜瓜/.test(text)) return assetUrl('/images/products/minqin-melon.webp')
  if (/枸杞/.test(text)) return assetUrl('/images/products/gansu-goji.webp')
  if (/小枣|枣/.test(text)) return assetUrl('/images/products/linze-jujube.webp')
  if (/百合/.test(text)) return assetUrl('/images/products/lanzhou-lily.webp')
  if (/当归/.test(text)) return assetUrl('/images/products/minxian-danggui.webp')
  return assetUrl('/images/products/jingning-apple.webp')
}

export function productImage(product?: Partial<Product> | null): string {
  return assetUrl(product?.cover_url, productFallbackImage(product?.title))
}

export function pointsCopy(text?: string | null): string {
  return (text || '').replace(/绿豆/g, '绿色积分')
}

export function productFallbackGallery(title?: string | null): string[] {
  const base = productFallbackImage(title).replace(/\.webp$/, '')
  return [1, 2, 3, 4].map((index) => `${base}-${index}.webp`)
}

export function errorText(error: unknown): string {
  const err = error as { code?: string; message?: string } | null
  const map: Record<string, string> = {
    NETWORK_ERROR: '无法连接后端服务，请确认后端已启动。',
    TIMEOUT: '请求超时，请稍后重试。',
    UNAUTHENTICATED: '请先登录后再操作。',
    TOKEN_EXPIRED: '登录状态已过期，请重新登录。',
    FORBIDDEN: '当前账号无权执行该操作。',
    INSUFFICIENT_STOCK: '库存不足，请调整购买数量。',
    PRICE_CHANGED: '商品价格已变化，请重新确认订单。',
    PRODUCT_NOT_PURCHASABLE: '商品当前不可购买。',
    ORDER_STATE_INVALID: '订单当前状态不允许该操作。',
    POINTS_INSUFFICIENT: '绿色积分余额不足。',
    REFUND_NOT_ALLOWED: '当前订单不支持该退款操作。',
    REFUND_EXCEED_LIMIT: '退款金额超出可退限额。',
    IDEMPOTENCY_CONFLICT: '请勿重复提交相同订单。',
    STORE_REQUIRED: '请先选择店铺。',
    CMS_PAGE_NOT_PUBLISHED: '页面配置暂未发布。'
  }
  return pointsCopy((err?.code && map[err.code]) || err?.message || '操作未完成，请稍后重试。')
}

export function percent(raised?: string | null, goal?: string | null): number {
  if (!raised || !goal) return 0
  const r = Number(raised)
  const g = Number(goal)
  if (!Number.isFinite(r) || !Number.isFinite(g) || g <= 0) return 0
  return Math.max(0, Math.min(100, Math.round((r / g) * 100)))
}

export function orderProgress(status?: string | null): number {
  switch (status) {
    case 'pending_payment':
      return 0
    case 'paid':
      return 1
    case 'shipped':
      return 2
    case 'completed':
      return 3
    default:
      return -1
  }
}

export function formatPhone(phone?: string | null): string {
  if (!phone) return ''
  if (/^\d{11}$/.test(phone)) return `${phone.slice(0, 3)}****${phone.slice(7)}`
  return phone
}
