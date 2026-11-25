/**
 * 商城目录变更总线。
 *
 * 解决「管理端审核通过 → 消费者端无需刷新即时可见」：
 * - 同一浏览器多标签页：BroadcastChannel + localStorage 版本号；
 * - 静态演示：管理端写入发布区后立即广播；
 * - 真实后端：管理端操作成功后广播，其他浏览器由版本轮询兜底。
 */
export const PUBLISHED_PRODUCTS_KEY = 'tanhui_demo_published_products'
export const CATALOG_REVISION_KEY = 'tanhui_catalog_revision'
const LOCAL_EVENT = 'tanhui:catalog-changed'
const CHANNEL_NAME = 'tanhui-catalog'

let channel: BroadcastChannel | null = null
if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
  try {
    channel = new BroadcastChannel(CHANNEL_NAME)
  } catch {
    channel = null
  }
}

/** 通知所有消费者端页面：商品目录已变化，请立即刷新。 */
export function notifyCatalogChanged(): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(CATALOG_REVISION_KEY, String(Date.now()))
  } catch {
    // 隐私模式下不可写，忽略
  }
  try {
    channel?.postMessage({ at: Date.now() })
  } catch {
    // 通道被关闭时忽略
  }
  window.dispatchEvent(new Event(LOCAL_EVENT))
}

/** 监听目录变化（同标签页、跨标签页、跨窗口）。返回取消监听函数。 */
export function onCatalogChanged(listener: () => void): () => void {
  if (typeof window === 'undefined') return () => {}

  const onLocal = (): void => listener()
  const onMessage = (): void => listener()
  const onStorage = (event: StorageEvent): void => {
    if (event.key === PUBLISHED_PRODUCTS_KEY || event.key === CATALOG_REVISION_KEY) listener()
  }

  window.addEventListener(LOCAL_EVENT, onLocal)
  window.addEventListener('storage', onStorage)
  channel?.addEventListener('message', onMessage)
  return () => {
    window.removeEventListener(LOCAL_EVENT, onLocal)
    window.removeEventListener('storage', onStorage)
    channel?.removeEventListener('message', onMessage)
  }
}
