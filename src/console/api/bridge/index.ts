/**
 * 管理端 ↔ 真实后端桥接层统一出口。
 * 页面/API 层只依赖本模块，不直接触碰 fetch 细节。
 */
import { syncFromBackend, writeThrough, type SyncReport } from './sync'
import { clearBackendAuth, getBackendAuth, linkBackend } from './client'

const LAST_SYNC_KEY = 'tanhui_console_last_sync'
const AUTO_SYNC_INTERVAL = 30_000

let lastAttempt = 0
let inFlight: Promise<SyncReport> | null = null

/** 供页面调用的增量同步（带节流 + 去重）。 */
export function syncNow(force = false): Promise<SyncReport> | null {
  const now = Date.now()
  if (!force && now - lastAttempt < AUTO_SYNC_INTERVAL) return null
  if (inFlight) return inFlight
  lastAttempt = now
  inFlight = syncFromBackend()
    .then((report) => {
      if (report.ok) localStorage.setItem(LAST_SYNC_KEY, report.at)
      return report
    })
    .finally(() => {
      inFlight = null
    })
  return inFlight
}

export function lastSyncAt(): string {
  try {
    return localStorage.getItem(LAST_SYNC_KEY) || ''
  } catch {
    return ''
  }
}

export function isBackendLinked(): boolean {
  return Boolean(getBackendAuth())
}

export async function ensureBackendLinked(role: 'admin' | 'merchant'): Promise<boolean> {
  return Boolean((await linkBackend(role)) || getBackendAuth())
}

/**
 * 读取前的轻量同步：确保已链接后端，并在超过间隔时拉取一次权威数据。
 * 供管理端各 API 读取方法在开头 await，保证页面看到消费者端真实数据。
 */
export async function ensureSynced(role: 'admin' | 'merchant' = 'admin'): Promise<void> {
  if (!isBackendLinked()) await ensureBackendLinked(role)
  await syncNow(false)
}

export { syncFromBackend, writeThrough, clearBackendAuth, linkBackend, getBackendAuth }
export type { SyncReport }
