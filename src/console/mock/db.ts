import type { OperationLog } from '@/console/api/types'
import { seedDb, SEEDED_DB_VERSION } from './seed'
import type { ConsoleDb } from './seed'

const STORAGE_KEY = 'tanhui_console_db_v1'

let db: ConsoleDb | null = null

function readStorage(): ConsoleDb | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as ConsoleDb
    if (!parsed || parsed.version !== SEEDED_DB_VERSION) return null
    return parsed
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
