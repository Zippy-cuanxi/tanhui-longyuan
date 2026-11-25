/**
 * 消费者端商城实时刷新。
 *
 * 触发来源：
 * 1. 同浏览器管理端审核/下架成功 → catalogBus 立即广播；
 * 2. 其他浏览器/设备的管理端操作 → 每 5 秒轮询 /catalog/version 指纹；
 * 3. 窗口重新聚焦/从后台恢复 → 主动校验一次。
 *
 * 静态演示（GitHub Pages）没有后端，使用管理端写入 localStorage 后的广播。
 */
import { onBeforeUnmount, onMounted } from 'vue'
import { catalogApi } from '@/api'
import { onCatalogChanged } from '@/utils/catalogBus'

type RefreshHandler = () => void | Promise<void>

const isStaticDemo = import.meta.env.VITE_STATIC_DEMO === '1'
const POLL_MS = 5000
const subscribers = new Set<RefreshHandler>()

let flushTimer = 0
let pollTimer = 0
let lastVersion = ''
let checking = false

function flush(): void {
  if (flushTimer) return
  flushTimer = window.setTimeout(() => {
    flushTimer = 0
    const jobs = [...subscribers].map((handler) =>
      Promise.resolve()
        .then(handler)
        .catch(() => undefined)
    )
    void Promise.allSettled(jobs)
  }, 120)
}

async function checkVersion(force = false): Promise<void> {
  if (isStaticDemo || checking) return
  checking = true
  try {
    const next = await catalogApi.version()
    if (!lastVersion) {
      lastVersion = next
      if (force) flush()
      return
    }
    if (next !== lastVersion) {
      lastVersion = next
      flush()
    } else if (force) {
      flush()
    }
  } catch {
    // 后端暂不可用时静默，避免影响页面本身
  } finally {
    checking = false
  }
}

function startPolling(): void {
  if (isStaticDemo || pollTimer) return
  void checkVersion()
  pollTimer = window.setInterval(() => void checkVersion(), POLL_MS)
}

function stopPolling(): void {
  if (!pollTimer) return
  window.clearInterval(pollTimer)
  pollTimer = 0
}

/** 在当前页面注册目录变更回调；组件卸载时自动清理。 */
export function useCatalogLive(refresh: RefreshHandler): void {
  let unsubscribe = (): void => {}

  const onFocus = (): void => {
    if (document.visibilityState !== 'visible') return
    if (isStaticDemo) flush()
    else void checkVersion(true)
  }

  onMounted(() => {
    subscribers.add(refresh)
    unsubscribe = onCatalogChanged(flush)
    window.addEventListener('focus', onFocus)
    document.addEventListener('visibilitychange', onFocus)
    startPolling()
  })

  onBeforeUnmount(() => {
    subscribers.delete(refresh)
    unsubscribe()
    window.removeEventListener('focus', onFocus)
    document.removeEventListener('visibilitychange', onFocus)
    if (!subscribers.size) {
      stopPolling()
      if (flushTimer) {
        window.clearTimeout(flushTimer)
        flushTimer = 0
      }
    }
  })
}
