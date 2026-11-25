/**
 * 管理端后端桥接客户端。
 *
 * 管理端沿用自身的 mock 会话与页面类型，但通过本模块与真实 FastAPI 后端通信，
 * 使消费者端与管理端共享同一份权威数据（订单、商品、退款、公告、商家、店铺）。
 *
 * 设计要点：
 * - 使用独立的 token key，不干扰消费者端的 localStorage token。
 * - 管理端演示账号（admin_super / merchant01 等）在首次桥接时，用对应的后端
 *   演示账号换取真实 JWT；若后端不可达，所有桥接方法安全失败，页面回退到 mock。
 * - 所有方法不抛异常到页面：返回 null / false，由调用方决定是否降级。
 */

const API_BASE = '/api/v1'
const TOKEN_KEY = 'tanhui_console_backend_token'
const TOKEN_KEY_ADMIN = 'tanhui_console_backend_token_admin'
const TOKEN_KEY_MERCHANT = 'tanhui_console_backend_token_merchant'
const AUTH_KEY = 'tanhui_console_backend_account'

function tokenKeyFor(role: 'admin' | 'merchant'): string {
  return role === 'admin' ? TOKEN_KEY_ADMIN : TOKEN_KEY_MERCHANT
}

/** 演示账号 → 后端真实账号映射（后端 seed 中的固定演示账号）。 */
const BACKEND_ACCOUNTS: Record<string, { email: string; password: string }> = {
  admin: { email: 'admin@tanhui.example.com', password: 'Demo@123456' },
  merchant: { email: 'merchant1@tanhui.example.com', password: 'Passw0rd!123' }
}

export interface BridgeAuthInfo {
  email: string
  role: 'admin' | 'merchant'
  linkedAt: string
}

export function getBackendToken(role?: 'admin' | 'merchant'): string {
  try {
    if (role) return localStorage.getItem(tokenKeyFor(role)) || ''
    // 兼容旧调用：优先返回当前 auth 角色的 token
    const current = getBackendAuth()?.role
    return (
      (current && localStorage.getItem(tokenKeyFor(current))) ||
      localStorage.getItem(TOKEN_KEY) ||
      ''
    )
  } catch {
    return ''
  }
}

export function getBackendAuth(): BridgeAuthInfo | null {
  try {
    const raw = localStorage.getItem(AUTH_KEY)
    return raw ? (JSON.parse(raw) as BridgeAuthInfo) : null
  } catch {
    return null
  }
}

/** 用演示账号换取后端 JWT；成功返回 token，失败返回 null（不抛错）。 */
export async function linkBackend(role: 'admin' | 'merchant'): Promise<string | null> {
  if (import.meta.env.VITE_STATIC_DEMO === '1') return 'demo.static.token'
  const account = BACKEND_ACCOUNTS[role]
  if (!account) return null
  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(account)
    })
    if (!response.ok) return null
    const payload = (await response.json()) as {
      code?: string
      data?: { access_token?: string }
    }
    const token = payload?.data?.access_token
    if (!token) return null
    localStorage.setItem(tokenKeyFor(role), token)
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(
      AUTH_KEY,
      JSON.stringify({ email: account.email, role, linkedAt: new Date().toISOString() })
    )
    return token
  } catch {
    return null
  }
}

export function clearBackendAuth(): void {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(AUTH_KEY)
  } catch {
    // ignore
  }
}

export interface BridgeResult<T> {
  ok: boolean
  data: T | null
  status: number
  /** 后端失败时的可读错误信息（用于审核/同步等需要明确原因的页面）。 */
  message?: string
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as {
      message?: string
      data?: { message?: string }
    }
    return payload?.message || payload?.data?.message || ''
  } catch {
    return ''
  }
}

/**
 * 统一请求入口：自动带 token，失败返回结构化结果，绝不抛异常到调用方。
 */
export async function bridgeRequest<T>(
  path: string,
  options: { method?: string; body?: unknown; role?: 'admin' | 'merchant' } = {}
): Promise<BridgeResult<T>> {
  // 静态演示模式（GitHub Pages 无后端）：写穿透视为成功，读返回空，让管理端走纯 mock 演示
  if (import.meta.env.VITE_STATIC_DEMO === '1') {
    const method = options.method || 'GET'
    return { ok: true, data: (method === 'GET' ? [] : null) as T, status: 200 }
  }
  const role = options.role || getBackendAuth()?.role || 'admin'
  let token = getBackendToken(role)
  if (!token) token = (await linkBackend(role)) || ''
  if (!token) return { ok: false, data: null, status: 401 }

  const headers: Record<string, string> = {
    Accept: 'application/json',
    Authorization: `Bearer ${token}`
  }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: options.method || 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined
    })
    if (response.status === 401) {
      // 令牌过期：重新登录一次并重试
      const fresh = await linkBackend(role)
      if (!fresh) return { ok: false, data: null, status: 401 }
      headers.Authorization = `Bearer ${fresh}`
      const retry = await fetch(`${API_BASE}${path}`, {
        method: options.method || 'GET',
        headers,
        body: options.body !== undefined ? JSON.stringify(options.body) : undefined
      })
      if (!retry.ok) {
        return {
          ok: false,
          data: null,
          status: retry.status,
          message: await readErrorMessage(retry)
        }
      }
      const text = await retry.text()
      return { ok: true, data: text ? (JSON.parse(text) as T) : null, status: retry.status }
    }
    if (!response.ok) {
      return {
        ok: false,
        data: null,
        status: response.status,
        message: await readErrorMessage(response)
      }
    }
    const text = await response.text()
    return { ok: true, data: text ? (JSON.parse(text) as T) : null, status: response.status }
  } catch {
    return { ok: false, data: null, status: 0 }
  }
}

/** 解包统一响应 {code,message,data,request_id}。 */
export function unwrap<T>(result: BridgeResult<{ data?: T; code?: string }>): T | null {
  if (!result.ok || !result.data) return null
  if (result.data.code && result.data.code !== 'OK') return null
  return result.data.data ?? null
}
