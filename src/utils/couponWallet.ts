export interface PaymentCoupon {
  id: string
  title: string
  discount: number
  threshold: number
  description: string
  valid_until: string
}

export interface CouponOption {
  coupon: PaymentCoupon
  eligible: boolean
}

const USED_KEY = 'tanhui_used_coupons'
const APPLIED_KEY = 'tanhui_order_coupons'

/** 演示优惠券：支付页按订单金额与使用状态实时筛选。 */
export const DEMO_COUPONS: PaymentCoupon[] = [
  {
    id: 'welcome-5',
    title: '新人立减券',
    discount: 5,
    threshold: 0,
    description: '无门槛，全场通用',
    valid_until: '2026-12-31'
  },
  {
    id: 'full-99-10',
    title: '满 99 减 10',
    discount: 10,
    threshold: 99,
    description: '全场通用，可与积分叠加',
    valid_until: '2026-12-31'
  },
  {
    id: 'full-199-30',
    title: '满 199 减 30',
    discount: 30,
    threshold: 199,
    description: '全场通用，每单限用一张',
    valid_until: '2026-12-31'
  }
]

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function writeJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // 本地存储不可用时仅影响演示状态，不阻断支付流程
  }
}

export function usedCouponIds(): string[] {
  return readJson<string[]>(USED_KEY, [])
}

export function findCoupon(couponId: string | null | undefined): PaymentCoupon | null {
  if (!couponId) return null
  return DEMO_COUPONS.find((coupon) => coupon.id === couponId) || null
}

/** 当前订单可选的优惠券（已使用的券不再出现），并标记是否达到使用门槛。 */
export function listCouponOptions(itemsTotal: number): CouponOption[] {
  const used = new Set(usedCouponIds())
  return DEMO_COUPONS.filter((coupon) => !used.has(coupon.id)).map((coupon) => ({
    coupon,
    eligible: isCouponEligible(coupon, itemsTotal)
  }))
}

export function isCouponEligible(coupon: PaymentCoupon, itemsTotal: number): boolean {
  return itemsTotal >= coupon.threshold
}

/** 优惠券实际减金：不超过当前应付金额，避免出现负数。 */
export function couponDiscountAmount(coupon: PaymentCoupon | null, payAmount: number): number {
  if (!coupon || !Number.isFinite(payAmount) || payAmount <= 0) return 0
  return Math.min(coupon.discount, payAmount)
}

export function appliedCouponId(orderId: string): string {
  const map = readJson<Record<string, string>>(APPLIED_KEY, {})
  return map[orderId] || ''
}

export function rememberAppliedCoupon(orderId: string, couponId: string | null): void {
  const map = readJson<Record<string, string>>(APPLIED_KEY, {})
  if (couponId) map[orderId] = couponId
  else delete map[orderId]
  writeJson(APPLIED_KEY, map)
}

/** 支付成功后核销优惠券，并保留订单与券的关联用于支付成功页展示。 */
export function consumeCoupon(orderId: string, couponId: string): void {
  const used = new Set(usedCouponIds())
  used.add(couponId)
  writeJson(USED_KEY, Array.from(used))
  rememberAppliedCoupon(orderId, couponId)
}
