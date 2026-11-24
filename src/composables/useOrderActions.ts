import { useRouter } from 'vue-router'
import { orderApi } from '@/api'
import type { Order } from '@/api/types'
import { useConfirmStore } from '@/stores/confirm'
import { useToastStore } from '@/stores/toast'
import { errorText } from '@/utils/format'

export function useOrderActions(refresh: () => void | Promise<void>) {
  const router = useRouter()
  const confirm = useConfirmStore()
  const toast = useToastStore()

  function fail(error: unknown): void {
    toast.show(errorText(error), 'error', (error as { requestId?: string }).requestId)
  }

  function pay(order: Order): void {
    router.push({ name: 'payment', params: { orderId: order.id } })
  }

  async function cancel(order: Order): Promise<void> {
    const ok = await confirm.ask({
      title: '取消订单',
      message: `确认取消订单 ${order.order_no} 吗？取消后库存将释放。`,
      confirmText: '取消订单',
      cancelText: '再想想',
      danger: true
    })
    if (!ok) return
    try {
      await orderApi.cancel(order.id, '买家取消')
      toast.show('订单已取消', 'success')
      await refresh()
    } catch (error) {
      fail(error)
    }
  }

  async function confirmReceipt(order: Order): Promise<void> {
    const ok = await confirm.ask({
      title: '确认收货',
      message: '确认已收到商品吗？确认后订单将完成并发放绿色积分。',
      confirmText: '确认收货'
    })
    if (!ok) return
    try {
      await orderApi.confirmReceipt(order.id)
      toast.show('已确认收货，订单完成', 'success')
      await refresh()
    } catch (error) {
      fail(error)
    }
  }

  function refund(order: Order): void {
    router.push({ name: 'order-refund', params: { id: order.id } })
  }

  function logistics(order: Order): void {
    router.push({ name: 'order-logistics', params: { id: order.id } })
  }

  function detail(order: Order): void {
    router.push({ name: 'order-detail', params: { id: order.id } })
  }

  async function handle(action: string, order: Order): Promise<void> {
    if (action === 'pay') return pay(order)
    if (action === 'cancel') return cancel(order)
    if (action === 'confirm') return confirmReceipt(order)
    if (action === 'refund') return refund(order)
    if (action === 'logistics') return logistics(order)
    if (action === 'detail') return detail(order)
  }

  return { pay, cancel, confirmReceipt, refund, logistics, detail, handle }
}
