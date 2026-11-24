import { onBeforeUnmount, onMounted } from 'vue'

/**
 * 消费者端页面在窗口重新聚焦时自动刷新数据。
 * 这样管理端（另一标签页）修改商品/发布公告后，切回消费者页面即可看到最新数据。
 */
export function useRefreshOnFocus(refresh: () => void | Promise<void>): void {
  function handler(): void {
    if (document.visibilityState === 'visible') void refresh()
  }
  onMounted(() => {
    window.addEventListener('focus', handler)
    document.addEventListener('visibilitychange', handler)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('focus', handler)
    document.removeEventListener('visibilitychange', handler)
  })
}
