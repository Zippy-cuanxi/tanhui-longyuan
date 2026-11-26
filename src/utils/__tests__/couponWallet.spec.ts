import { beforeEach, describe, expect, it } from 'vitest'
import {
  appliedCouponId,
  consumeCoupon,
  couponDiscountAmount,
  findCoupon,
  listCouponOptions,
  rememberAppliedCoupon,
  usedCouponIds
} from '../couponWallet'

describe('couponWallet', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('按订单金额标记优惠券是否达到门槛', () => {
    const options = listCouponOptions(50)
    expect(options).toHaveLength(3)
    expect(options.find((item) => item.coupon.id === 'welcome-5')?.eligible).toBe(true)
    expect(options.find((item) => item.coupon.id === 'full-99-10')?.eligible).toBe(false)
    expect(options.find((item) => item.coupon.id === 'full-199-30')?.eligible).toBe(false)

    const higher = listCouponOptions(120)
    expect(higher.find((item) => item.coupon.id === 'full-99-10')?.eligible).toBe(true)
    expect(higher.find((item) => item.coupon.id === 'full-199-30')?.eligible).toBe(false)
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

  it('支付成功后核销优惠券，后续订单不再可选', () => {
    consumeCoupon('order-1', 'welcome-5')

    expect(usedCouponIds()).toContain('welcome-5')
    expect(appliedCouponId('order-1')).toBe('welcome-5')
    const options = listCouponOptions(500)
    expect(options.some((item) => item.coupon.id === 'welcome-5')).toBe(false)
    expect(options).toHaveLength(2)
  })
})
