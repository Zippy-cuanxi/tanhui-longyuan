import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ensureBackendLinked, isBackendLinked, syncNow } from '@/console/api/bridge'
import { useConsoleAuth } from '@/console/stores/auth'

/**
 * 在管理端页面挂载时，把真实后端数据投影到本地数据源。
 * 同时监听窗口重新聚焦，保证消费者端在另一标签页下单后切回来即可看到。
 */
export function useDataSync(options: { merchantRole?: boolean } = {}) {
  const auth = useConsoleAuth()
  const syncing = ref(false)
  const lastResult = ref<string>('')

  async function run(force = true): Promise<void> {
    syncing.value = true
    try {
      const role = options.merchantRole || auth.isMerchant ? 'merchant' : 'admin'
      if (!isBackendLinked()) await ensureBackendLinked(role)
      const result = await syncNow(force)
      if (result) {
        lastResult.value = result.ok
          ? `已同步 ${result.orders} 订单 / ${result.products} 商品`
          : result.error || '后端不可用，使用演示数据'
      }
    } finally {
      syncing.value = false
    }
  }

  function onVisible(): void {
    if (document.visibilityState === 'visible') void run()
  }

  onMounted(() => {
    void run()
    window.addEventListener('focus', onVisible)
    document.addEventListener('visibilitychange', onVisible)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('focus', onVisible)
    document.removeEventListener('visibilitychange', onVisible)
  })

  return { syncing, lastResult, refresh: run }
}
