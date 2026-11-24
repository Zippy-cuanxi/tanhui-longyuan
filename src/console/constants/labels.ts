/* 全部状态/枚举中文与颜色集中管理。颜色取自 00 设计规范板。 */

export type StatusTone = 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'muted'

export interface StatusMeta {
  label: string
  tone: StatusTone
  color: string
  bg: string
}

const palette: Record<StatusTone, { color: string; bg: string }> = {
  primary: { color: '#1F7A4D', bg: '#E7F4EC' },
  success: { color: '#2E9E5B', bg: '#E8F6ED' },
  warning: { color: '#E8892B', bg: '#FFF3E4' },
  danger: { color: '#D64545', bg: '#FDECEC' },
  info: { color: '#3B82C4', bg: '#EAF2FB' },
  muted: { color: '#6B7A74', bg: '#EFF3F1' }
}

function meta(label: string, tone: StatusTone): StatusMeta {
  return { label, tone, ...palette[tone] }
}

export const MERCHANT_STATUS: Record<string, StatusMeta> = {
  normal: meta('正常', 'success'),
  pending: meta('审核中', 'warning'),
  rejected: meta('审核驳回', 'danger'),
  frozen: meta('已冻结', 'danger')
}

export const PRODUCT_STATUS: Record<string, StatusMeta> = {
  draft: meta('草稿', 'muted'),
  pending_review: meta('审核中', 'warning'),
  approved: meta('已通过', 'primary'),
  rejected: meta('已驳回', 'danger'),
  removed: meta('平台下架', 'muted')
}

export const ORDER_STATUS: Record<string, StatusMeta> = {
  pending_payment: meta('待付款', 'warning'),
  paid: meta('待发货', 'info'),
  shipped: meta('待收货', 'primary'),
  completed: meta('已完成', 'success'),
  cancelled: meta('已取消', 'muted'),
  refunding: meta('退款中', 'warning'),
  refunded: meta('已退款', 'muted'),
  partially_refunded: meta('部分退款', 'warning')
}

export const AFTERSALE_STATUS: Record<string, StatusMeta> = {
  requested: meta('待处理', 'warning'),
  arbitrating: meta('平台仲裁', 'info'),
  refunded: meta('已退款', 'success'),
  rejected: meta('已驳回', 'danger')
}

export const SETTLEMENT_STATUS: Record<string, StatusMeta> = {
  pending: meta('待确认', 'warning'),
  confirmed: meta('已确认', 'info'),
  paid: meta('已打款', 'success')
}

export const WITHDRAWAL_STATUS: Record<string, StatusMeta> = {
  pending: meta('待审核', 'warning'),
  approved: meta('已通过', 'success'),
  rejected: meta('已驳回', 'danger')
}

export const ANNOUNCEMENT_STATUS: Record<string, StatusMeta> = {
  draft: meta('草稿', 'muted'),
  published: meta('已发布', 'success'),
  offline: meta('已下线', 'muted')
}

export const MEMBER_STATUS: Record<string, StatusMeta> = {
  active: meta('正常', 'success'),
  banned: meta('已封禁', 'danger')
}

export const STORE_STATUS: Record<string, StatusMeta> = {
  active: meta('正常', 'success'),
  suspended: meta('已暂停', 'warning'),
  closed: meta('已关闭', 'muted')
}

export const RISK_LEVEL: Record<string, StatusMeta> = {
  high: meta('高风险', 'danger'),
  normal: meta('常规', 'info')
}

export const ORDER_STATUS_KEYS = Object.keys(ORDER_STATUS)
export const PRODUCT_STATUS_KEYS = Object.keys(PRODUCT_STATUS)
export const AFTERSALE_STATUS_KEYS = Object.keys(AFTERSALE_STATUS)
export const SETTLEMENT_STATUS_KEYS = Object.keys(SETTLEMENT_STATUS)
export const WITHDRAWAL_STATUS_KEYS = Object.keys(WITHDRAWAL_STATUS)

export const SHIPPING_CARRIERS = ['顺丰速运', '京东物流', '中通快递', '圆通速递', '邮政EMS']

export const REJECT_REASONS = [
  '资质材料不清晰',
  '商品图片不合规',
  '商品描述与实物不符',
  '价格异常',
  '类目选择错误',
  '其他原因'
]

export const REFUND_REASONS = [
  '商品破损',
  '与描述不符',
  '少件/漏发',
  '不想要了',
  '发货超时',
  '其他原因'
]

export const AD_PLACEMENTS = ['首页轮播', '全部商品页', '绿色消费专区', '助农项目页']

export function statusMeta(dict: Record<string, StatusMeta>, value?: string | null): StatusMeta {
  if (value && dict[value]) return dict[value]
  return { label: value || '—', tone: 'muted', ...palette.muted }
}
