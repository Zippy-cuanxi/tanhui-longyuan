/**
 * 后端 UUID ↔ 管理端 mock ID 的映射表（持久化到 localStorage）。
 * 管理端页面沿用 p001/o001 这类短 ID，桥接层负责与后端 UUID 互转。
 */

const MAP_KEY = 'tanhui_console_id_map_v1'

interface IdMap {
  uuidToMock: Record<string, string>
  mockToUuid: Record<string, string>
  counters: Record<string, number>
}

let cache: IdMap | null = null

function load(): IdMap {
  if (cache) return cache
  try {
    const raw = localStorage.getItem(MAP_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as IdMap
      if (parsed && parsed.uuidToMock && parsed.mockToUuid) {
        cache = parsed
        return cache
      }
    }
  } catch {
    // ignore
  }
  cache = { uuidToMock: {}, mockToUuid: {}, counters: {} }
  return cache
}

function persist(): void {
  if (!cache) return
  try {
    localStorage.setItem(MAP_KEY, JSON.stringify(cache))
  } catch {
    // ignore
  }
}

/** 为后端 UUID 分配/读取稳定的 mock ID，如 prefix + 三位序号。 */
export type IdPrefix = 'p' | 'o' | 'as' | 'm' | 's' | 'u' | 'cat' | 'ann' | 'g' | 'r' | 'z' | 'n' | 'k'

export function mockIdFor(uuid: string, prefix: IdPrefix): string {
  const map = load()
  const existing = map.uuidToMock[uuid]
  if (existing) return existing
  const next = (map.counters[prefix] || 0) + 1
  map.counters[prefix] = next
  const mockId = `${prefix}${String(next).padStart(3, '0')}`
  map.uuidToMock[uuid] = mockId
  map.mockToUuid[mockId] = uuid
  persist()
  return mockId
}

/** 显式绑定一个已存在的 mock ID 到后端 UUID（用于新建实体后建立关联）。 */
export function bindId(mockId: string, uuid: string): void {
  const map = load()
  map.uuidToMock[uuid] = mockId
  map.mockToUuid[mockId] = uuid
  persist()
}

/** mock ID → 后端 UUID；无映射返回原值（便于后端 ID 直接传入时透传）。 */
export function uuidFor(mockId: string): string {
  const map = load()
  return map.mockToUuid[mockId] || mockId
}

/** 后端 UUID → mock ID；无映射返回原值。 */
export function mockFor(uuid: string): string {
  const map = load()
  return map.uuidToMock[uuid] || uuid
}
