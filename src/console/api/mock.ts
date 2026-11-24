export const MOCK_FAIL_KEY = 'tanhui_console_mock_fail'

export class MockApiError extends Error {
  code: string
  requestId: string

  constructor(code: string, message: string, requestId = mockRequestId()) {
    super(message)
    this.name = 'MockApiError'
    this.code = code
    this.requestId = requestId
  }
}

export function mockRequestId(): string {
  return `MOCK-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

export function isMockFailureEnabled(): boolean {
  return localStorage.getItem(MOCK_FAIL_KEY) === '1'
}

export function setMockFailureEnabled(value: boolean): void {
  localStorage.setItem(MOCK_FAIL_KEY, value ? '1' : '0')
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

/** 所有 mock api 统一走这里：300–600ms 延迟；开启偶发失败时约 10% 抛错。 */
export async function mockCall<T>(task: () => T): Promise<T> {
  await wait(300 + Math.floor(Math.random() * 300))
  if (isMockFailureEnabled() && Math.random() < 0.1) {
    throw new MockApiError('MOCK_RANDOM_FAILURE', '模拟网络抖动：本次请求失败，请重试')
  }
  return task()
}

export interface MockPageQuery {
  page?: number
  page_size?: number
  status?: string
  keyword?: string
  date_from?: string
  date_to?: string
  [key: string]: string | number | undefined
}

export function mockPaginate<T>(
  items: T[],
  query: MockPageQuery,
  pageSizeDefault = 20
): {
  items: T[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
} {
  const page = Math.max(1, Number(query.page) || 1)
  const pageSize = Math.min(100, Math.max(1, Number(query.page_size) || pageSizeDefault))
  const total = items.length
  const start = (page - 1) * pageSize
  return {
    items: items.slice(start, start + pageSize),
    pagination: {
      page,
      page_size: pageSize,
      total,
      total_pages: Math.ceil(total / pageSize)
    }
  }
}

export function inDateRange(value: string, from?: string, to?: string): boolean {
  if (!from && !to) return true
  const time = new Date(value).getTime()
  if (from && time < new Date(`${from}T00:00:00+08:00`).getTime()) return false
  if (to && time >= new Date(`${to}T00:00:00+08:00`).getTime() + 24 * 60 * 60 * 1000) {
    return false
  }
  return true
}

export function byDateDesc<T extends { createdAt: string }>(a: T, b: T): number {
  return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
}

export function byDateAsc<T extends { createdAt: string }>(a: T, b: T): number {
  return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
}

export function moneyNumber(value: string | number): number {
  return Number(value)
}

export function toMoney(value: number): string {
  return value.toFixed(2)
}
