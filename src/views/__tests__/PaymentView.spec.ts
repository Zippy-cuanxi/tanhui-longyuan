import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import PaymentView from '../PaymentView.vue'
import { orderApi, paymentApi } from '@/api'
import { ownedCouponCount } from '@/utils/couponWallet'
import { useToastStore } from '@/stores/toast'
import type { Order, Payment } from '@/api/types'

vi.mock('@/api', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@/api')>()
  return {
    ...mod,
    orderApi: {
      ...mod.orderApi,
      detail: vi.fn()
    },
    paymentApi: {
      ...mod.paymentApi,
      init: vi.fn(),
      mockPay: vi.fn()
    }
  }
})

const pendingOrder = {
  id: 'o1',
  order_no: 'TH20261126001',
  status: 'pending_payment',
  receiver_name: '张三',
  receiver_phone: '13800000000',
  address: '甘肃省兰州市城关区',
  items_total: '150.00',
  shipping_fee: '0.00',
  points_deduct: '0.00',
  points_used: 0,
  pay_amount: '150.00',
  currency: 'CNY',
  created_at: '2026-11-26T00:00:00Z',
  store_orders: []
} as unknown as Order

const paidOrder = {
  ...pendingOrder,
  status: 'paid',
  paid_at: '2026-11-26T00:10:00Z'
} as unknown as Order

const payment = {
  id: 'pay1',
  pay_no: 'PAY20261126001',
  order_id: 'o1',
  amount: '0.00',
  currency: 'CNY',
  status: 'pending',
  provider: 'mock_sandbox',
  expires_at: '2026-11-26T01:00:00Z'
} as unknown as Payment

async function mountPaymentPage() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/pay/:orderId', name: 'payment', component: PaymentView },
      { path: '/account/orders/:id', component: { template: '<div />' } },
      { path: '/products', component: { template: '<div />' } }
    ]
  })
  await router.push('/pay/o1')
  await router.isReady()

  const wrapper = mount(PaymentView, {
    global: { plugins: [router] }
  })
  await flushPromises()
  return wrapper
}

describe('PaymentView 优惠券减金', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.mocked(orderApi.detail)
      .mockReset()
      .mockResolvedValueOnce(pendingOrder)
      .mockResolvedValueOnce(paidOrder)
    vi.mocked(paymentApi.init).mockReset().mockResolvedValue(payment)
    vi.mocked(paymentApi.mockPay).mockReset().mockResolvedValue({ return_code: 'SUCCESS' })
  })

  it('展示可用/不可用优惠券，并按订单金额计算应付', async () => {
    const wrapper = await mountPaymentPage()

    const tickets = wrapper.findAll('.coupon-ticket')
    expect(tickets).toHaveLength(3)
    expect(tickets[2].attributes('disabled')).toBeDefined()

    expect(wrapper.find('.payment-amount strong').text()).toContain('150.00')

    await tickets[1].trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.payment-amount strong').text()).toContain('140.00')
    expect(wrapper.find('.total-row dd').text()).toContain('140.00')
    expect(wrapper.find('.pay-button').text()).toContain('140.00')
    expect(wrapper.find('.payment-coupon-title span').text()).toContain('2 张')

    wrapper.unmount()
  })

  it('支付成功后核销优惠券，成功页展示优惠后金额', async () => {
    const wrapper = await mountPaymentPage()
    const toast = useToastStore()

    await wrapper.findAll('.coupon-ticket')[1].trigger('click')
    await wrapper.find('.pay-button').trigger('click')
    await flushPromises()

    expect(wrapper.find('.payment-result-amount').text()).toContain('140.00')
    expect(wrapper.find('.payment-result-meta').text()).toContain('优惠券减金')
    expect(toast.message).toContain('优惠券减 ¥10.00')
    expect(ownedCouponCount('full-99-10')).toBe(0)

    wrapper.unmount()
  })

  it('刷新后恢复该订单已选优惠券', async () => {
    localStorage.setItem('tanhui_order_coupons', JSON.stringify({ o1: 'full-199-30' }))
    const wrapper = await mountPaymentPage()

    // 满 199 券在本单不满足门槛，数据恢复后仍不应错误抵扣
    expect(wrapper.find('.payment-amount strong').text()).toContain('150.00')

    wrapper.unmount()
  })
})
