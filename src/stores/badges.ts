import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { notificationApi, orderApi, pointsApi } from '@/api'
import type { Order, PointTransaction } from '@/api/types'
import { useAuthStore } from './auth'

const NOTIFICATIONS_SEEN_KEY = 'tanhui_notifications_seen_at'
const ORDERS_SEEN_KEY = 'tanhui_orders_seen_at'
const POINTS_SEEN_KEY = 'tanhui_points_seen_at'
const PENDING_ORDER_STATUSES = ['pending_payment', 'paid', 'shipped'] as const

function readSeenAt(key: string): number {
  try {
    const raw = window.localStorage.getItem(key)
    if (raw) {
      const value = Number(raw)
      if (Number.isFinite(value) && value > 0) return value
    }
    return 0
  } catch {
    return 0
  }
}

function writeSeenAt(key: string): void {
  try {
    window.localStorage.setItem(key, String(Date.now()))
  } catch {
    // 忽略本地存储失败
  }
}

function timeOf(value?: string | null): number {
  if (!value) return 0
  const time = new Date(value).getTime()
  return Number.isFinite(time) ? time : 0
}

function orderActivityAt(order: Order): number {
  const times = [order.created_at, order.paid_at, order.completed_at, order.cancelled_at]
  order.store_orders?.forEach((storeOrder) => times.push(storeOrder.shipped_at))
  return times.reduce((latest, value) => Math.max(latest, timeOf(value)), 0)
}

function transactionAt(transaction: PointTransaction): number {
  return timeOf(transaction.created_at)
}

export const useBadgeStore = defineStore('badge', () => {
  const unreadNotifications = ref(0)
  const orderUpdates = ref(0)
  const pointUpdates = ref(0)
  const loading = ref(false)
  const total = computed(() => unreadNotifications.value + orderUpdates.value + pointUpdates.value)
  let requestSeq = 0

  function reset(): void {
    requestSeq += 1
    unreadNotifications.value = 0
    orderUpdates.value = 0
    pointUpdates.value = 0
    loading.value = false
  }

  function markNotificationsSeen(): void {
    writeSeenAt(NOTIFICATIONS_SEEN_KEY)
    unreadNotifications.value = 0
  }

  function markOrdersSeen(): void {
    writeSeenAt(ORDERS_SEEN_KEY)
    orderUpdates.value = 0
  }

  function markPointsSeen(): void {
    writeSeenAt(POINTS_SEEN_KEY)
    pointUpdates.value = 0
  }

  async function refresh(): Promise<void> {
    const auth = useAuthStore()
    if (!auth.isAuthenticated) {
      reset()
      return
    }
    const seq = ++requestSeq
    loading.value = true
    const [notificationResult, orderResult, pointsResult] = await Promise.allSettled([
      notificationApi.list(true),
      orderApi.list({ page: 1, page_size: 100 }),
      pointsApi.transactions({ page: 1, page_size: 100 })
    ])
    if (seq !== requestSeq) return

    if (notificationResult.status === 'fulfilled') {
      const since = readSeenAt(NOTIFICATIONS_SEEN_KEY)
      unreadNotifications.value = notificationResult.value.filter(
        (notification) => timeOf(notification.created_at) > since
      ).length
    }
    if (orderResult.status === 'fulfilled') {
      const since = readSeenAt(ORDERS_SEEN_KEY)
      orderUpdates.value = orderResult.value.items.filter(
        (order) =>
          (PENDING_ORDER_STATUSES as readonly string[]).includes(order.status) &&
          orderActivityAt(order) > since
      ).length
    }
    if (pointsResult.status === 'fulfilled') {
      const since = readSeenAt(POINTS_SEEN_KEY)
      pointUpdates.value = pointsResult.value.items.filter(
        (transaction) => transactionAt(transaction) > since
      ).length
    }
    loading.value = false
  }

  return {
    unreadNotifications,
    orderUpdates,
    pointUpdates,
    loading,
    total,
    refresh,
    reset,
    markNotificationsSeen,
    markOrdersSeen,
    markPointsSeen
  }
})
