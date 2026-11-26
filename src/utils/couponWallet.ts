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

export interface CouponStoreItem {
  coupon: PaymentCoupon
  points: number
  reward_code: string
}

const WALLET_KEY = 'tanhui_coupon_wallet'
const LEGACY_USED_KEY = 'tanhui_used_coupons'
const APPLIED_KEY = 'tanhui_order_coupons'

/** 演示用户初始券包：与优惠券商店共用同一套券。 */
const INITIAL_OWNED: Record<string, number> = {
  'welcome-5': 1,
  'full-99-10': 1,
  'full-199-30': 1
}

/** 优惠券基础信息：支付页按券包数量展示，商店按积分兑换。 */
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
    id: 'full-59-6',
    title: '满 59 减 6',
    discount: 6,
    threshold: 59,
    description: '全场通用，可与积分叠加',
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
  },
  {
    id: 'full-299-50',
    title: '满 299 减 50',
    discount: 50,
    threshold: 299,
    description: '全场通用，每单限用一张',
    valid_until: '2026-12-31'
  }
]

function couponById(id: string): PaymentCoupon {
  const coupon = DEMO_COUPONS.find((item) => item.id === id)
  if (!coupon) throw new Error(`未知优惠券：${id}`)
  return coupon
}

/** 优惠券商店：使用绿色积分兑换，兑换后进入支付页券包。 */
export const COUPON_STORE: CouponStoreItem[] = [
  { coupon: couponById('welcome-5'), points: 500, reward_code: 'coupon_5' },
  { coupon: couponById('full-59-6'), points: 600, reward_code: 'coupon_6' },
  { coupon: couponById('full-99-10'), points: 900, reward_code: 'coupon_10' },
  { coupon: couponById('full-199-30'), points: 1800, reward_code: 'coupon_30' },
  { coupon: couponById('full-299-50'), points: 2500, reward_code: 'coupon_50' }
]

interface WalletState {
  owned: Record<string, number>
}

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

function loadWallet(): WalletState {
  const saved = readJson<WalletState | null>(WALLET_KEY, null)
  if (saved && saved.owned) return saved

  // 兼容旧版“已使用券”记录，迁移为券包数量
  const legacyUsed = new Set(readJson<string[]>(LEGACY_USED_KEY, []))
  const owned: Record<string, number> = {}
  Object.entries(INITIAL_OWNED).forEach(([id, count]) => {
    owned[id] = legacyUsed.has(id) ? Math.max(0, count - 1) : count
  })
  const state: WalletState = { owned }
  writeJson(WALLET_KEY, state)
  return state
}

function saveWallet(state: WalletState): void {
  writeJson(WALLET_KEY, state)
}

export function ownedCouponCount(couponId: string): number {
  return loadWallet().owned[couponId] || 0
}

export function addCouponToWallet(couponId: string, count = 1): void {
  const state = loadWallet()
  state.owned[couponId] = (state.owned[couponId] || 0) + count
  saveWallet(state)
}

export function findCoupon(couponId: string | null | undefined): PaymentCoupon | null {
  if (!couponId) return null
  return DEMO_COUPONS.find((coupon) => coupon.id === couponId) || null
}

/** 当前订单可选的优惠券（券包中数量大于 0），并标记是否达到使用门槛。 */
export function listCouponOptions(itemsTotal: number): CouponOption[] {
  const { owned } = loadWallet()
  return DEMO_COUPONS.filter((coupon) => (owned[coupon.id] || 0) > 0).map((coupon) => ({
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

/** 支付成功后核销一张优惠券，并保留订单与券的关联用于支付成功页展示。 */
export function consumeCoupon(orderId: string, couponId: string): void {
  const state = loadWallet()
  state.owned[couponId] = Math.max(0, (state.owned[couponId] || 0) - 1)
  saveWallet(state)
  rememberAppliedCoupon(orderId, couponId)
}
