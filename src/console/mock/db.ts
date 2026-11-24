import type { OperationLog } from '@/console/api/types'
import { assetUrl } from '@/api/http'
import { productFallbackImage } from '@/utils/format'
import { seedDb, SEEDED_DB_VERSION } from './seed'
import type { ConsoleDb } from './seed'

const STORAGE_KEY = 'tanhui_console_db_v1'

let db: ConsoleDb | null = null

/** 历史数据可能是旧版本结构或带旧部署前缀，读取后就地补齐图片字段。 */
function repairDb(target: ConsoleDb): ConsoleDb {
  for (const product of target.products || []) {
    if (!product.cover) product.cover = productFallbackImage(product.title)
    if (!product.images || !product.images.length) product.images = [product.cover]
  }
  for (const merchant of target.merchants || []) {
    if (!merchant.avatar) merchant.avatar = assetUrl('/console-assets/images/avatar-merchant.png')
  }
  for (const admin of target.admins || []) {
    if (!admin.avatar) admin.avatar = assetUrl('/console-assets/images/avatar-admin.png')
  }
  return target
}

function readStorage(): ConsoleDb | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as ConsoleDb
    if (!parsed || parsed.version !== SEEDED_DB_VERSION) return null
    return repairDb(parsed)
  } catch {
    return null
  }
}

export function getDb(): ConsoleDb {
  if (!db) {
    db = readStorage() || seedDb()
    saveDb()
  }
  return db
}

export function saveDb(): void {
  if (!db) return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db))
  } catch {
    // 存储满时忽略，内存态仍可用
  }
}

export function resetDb(): ConsoleDb {
  db = seedDb()
  saveDb()
  return db
}

export function appendLog(
  log: Omit<OperationLog, 'id' | 'createdAt' | 'ip'> & { ip?: string }
): OperationLog {
  const current = getDb()
  const entry: OperationLog = {
    ...log,
    id: `log-${Date.now()}-${Math.random().toString(16).slice(2, 7)}`,
    ip: log.ip || '10.0.0.24',
    createdAt: new Date().toISOString()
  }
  current.logs.unshift(entry)
  saveDb()
  return entry
}

export function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}
