import { beforeEach, describe, expect, it } from 'vitest'
import {
  COUPON_STORE,
  addCouponToWallet,
  appliedCouponId,
  consumeCoupon,
  couponDiscountAmount,
  findCoupon,
  listCouponOptions,
  ownedCouponCount,
  rememberAppliedCoupon
} from '../couponWallet'

describe('couponWallet', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('初始券包包含三张演示券，并按订单金额标记门槛', () => {
    const options = listCouponOptions(50)
    expect(options).toHaveLength(3)
    expect(options.find((item) => item.coupon.id === 'welcome-5')?.eligible).toBe(true)
    expect(options.find((item) => item.coupon.id === 'full-99-10')?.eligible).toBe(false)
    expect(options.find((item) => item.coupon.id === 'full-199-30')?.eligible).toBe(false)
    expect(options.some((item) => item.coupon.id === 'full-59-6')).toBe(false)

    const higher = listCouponOptions(120)
    expect(higher.find((item) => item.coupon.id === 'full-99-10')?.eligible).toBe(true)
    expect(higher.find((item) => item.coupon.id === 'full-199-30')?.eligible).toBe(false)
  })

  it('兑换商店优惠券后进入券包，可选择使用', () => {
    addCouponToWallet('full-59-6')

    expect(ownedCouponCount('full-59-6')).toBe(1)
    const options = listCouponOptions(80)
    expect(options).toHaveLength(4)
    expect(options.find((item) => item.coupon.id === 'full-59-6')?.eligible).toBe(true)
  })

  it('减金不会超过应付金额', () => {
    const coupon = findCoupon('full-199-30')
    expect(couponDiscountAmount(coupon, 20)).toBe(20)
    expect(couponDiscountAmount(coupon, 199)).toBe(30)
    expect(couponDiscountAmount(null, 199)).toBe(0)
  })

  it('按订单记录并清除已选优惠券', () => {
    rememberAppliedCoupon('order-1', 'full-99-10')
    expect(appliedCouponId('order-1')).toBe('full-99-10')
    expect(appliedCouponId('order-2')).toBe('')

    rememberAppliedCoupon('order-1', null)
    expect(appliedCouponId('order-1')).toBe('')
  })

  it('支付成功后核销一张，券包耗尽后不再可选', () => {
    consumeCoupon('order-1', 'welcome-5')

    expect(ownedCouponCount('welcome-5')).toBe(0)
    expect(appliedCouponId('order-1')).toBe('welcome-5')
    expect(listCouponOptions(500).some((item) => item.coupon.id === 'welcome-5')).toBe(false)

    consumeCoupon('order-2', 'welcome-5')
    expect(ownedCouponCount('welcome-5')).toBe(0)

    addCouponToWallet('welcome-5')
    expect(ownedCouponCount('welcome-5')).toBe(1)
  })

  it('商店目录与支付券使用同一套券信息', () => {
    expect(COUPON_STORE).toHaveLength(5)
    COUPON_STORE.forEach((item) => {
      expect(item.points).toBeGreaterThan(0)
      expect(findCoupon(item.coupon.id)).not.toBeNull()
    })
    expect(new Set(COUPON_STORE.map((item) => item.reward_code)).size).toBe(COUPON_STORE.length)
  })
})
