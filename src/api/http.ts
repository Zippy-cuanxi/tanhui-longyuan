import type { ApiResponse, CmsConfig } from './types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
const FILE_BASE = (import.meta.env.VITE_FILE_BASE_URL || '').replace(/\/$/, '')
const ACCESS_KEY = 'tanhui_access_token'
const REFRESH_KEY = 'tanhui_refresh_token'
const REQUEST_TIMEOUT = 15000

let refreshPromise: Promise<string> | null = null

export class ApiError extends Error {
  code: string
  status: number
  data: unknown
  requestId: string

  constructor(
    message: string,
    options: { code?: string; status?: number; data?: unknown; requestId?: string } = {}
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = options.code || 'REQUEST_FAILED'
    this.status = options.status || 0
    this.data = options.data ?? null
    this.requestId = options.requestId || ''
  }
}

export const tokenStorage = {
  get access(): string {
    return localStorage.getItem(ACCESS_KEY) || ''
  },
  get refresh(): string {
    return localStorage.getItem(REFRESH_KEY) || ''
  },
  save(pair: { access_token: string; refresh_token: string }): void {
    localStorage.setItem(ACCESS_KEY, pair.access_token)
    localStorage.setItem(REFRESH_KEY, pair.refresh_token)
  },
  clear(): void {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }
}

export function queryString(params: Record<string, unknown> = {}): string {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  const text = query.toString()
  return text ? `?${text}` : ''
}

function requestIdOf(payload: unknown, response: Response): string {
  const body = payload as Partial<ApiResponse<unknown>> | null
  return body?.request_id || response.headers.get('X-Request-ID') || ''
}

function errorMessageOf(payload: unknown, fallback: string): string {
  const body = payload as {
    message?: string
    data?: { errors?: Array<{ message?: string }> }
  } | null
  if (body?.data?.errors?.length) {
    return body.data.errors[0]?.message || body.message || fallback
  }
  return body?.message || fallback
}

function httpMessage(status: number): string {
  const messages: Record<number, string> = {
    400: '请求参数不合法',
    401: '登录状态已失效，请重新登录',
    403: '当前账号无权执行该操作',
    404: '请求的资源不存在',
    409: '操作冲突，请刷新后重试',
    422: '提交的信息不合法，请检查后重试',
    429: '请求过于频繁，请稍后重试',
    500: '服务器开小差了，请稍后重试'
  }
  return messages[status] || `请求失败（${status}）`
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    throw new ApiError('服务返回了无法解析的数据', {
      code: 'INVALID_RESPONSE',
      status: response.status,
      requestId: response.headers.get('X-Request-ID') || ''
    })
  }
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = tokenStorage.refresh
  if (!refreshToken) {
    throw new ApiError('登录状态已失效，请重新登录', { code: 'UNAUTHENTICATED', status: 401 })
  }
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  })
  const payload = await parseJson(response)
  if (!response.ok) {
    throw new ApiError(errorMessageOf(payload, httpMessage(response.status)), {
      code: (payload as { code?: string } | null)?.code || `HTTP_${response.status}`,
      status: response.status,
      data: (payload as { data?: unknown } | null)?.data,
      requestId: requestIdOf(payload, response)
    })
  }
  const envelope = payload as ApiResponse<{ access_token: string; refresh_token: string }>
  if (!envelope?.data?.access_token || !envelope?.data?.refresh_token) {
    throw new ApiError('刷新登录状态失败', { code: 'REFRESH_FAILED', status: 401 })
  }
  tokenStorage.save(envelope.data)
  return envelope.data.access_token
}

function clearSession(): void {
  tokenStorage.clear()
  window.dispatchEvent(new CustomEvent('auth:expired'))
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  timeout?: number
  skipAuthRefresh?: boolean
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    body,
    timeout = REQUEST_TIMEOUT,
    skipAuthRefresh = false,
    headers: initHeaders,
    ...rest
  } = options
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeout)
  const headers = new Headers(initHeaders || {})
  headers.set('Accept', 'application/json')
  if (tokenStorage.access) headers.set('Authorization', `Bearer ${tokenStorage.access}`)

  let payloadBody: BodyInit | undefined
  if (body !== undefined) {
    if (body instanceof FormData || body instanceof Blob || typeof body === 'string') {
      payloadBody = body
    } else {
      headers.set('Content-Type', 'application/json')
      payloadBody = JSON.stringify(body)
    }
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers,
      body: payloadBody,
      signal: controller.signal
    })

    if (response.status === 401 && !skipAuthRefresh && tokenStorage.refresh) {
      try {
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken().finally(() => {
            refreshPromise = null
          })
        }
        await refreshPromise
        return await request<T>(path, { ...options, skipAuthRefresh: true })
      } catch (refreshError) {
        clearSession()
        throw refreshError
      }
    }

    if (response.status === 401) {
      clearSession()
    }

    const payload = await parseJson(response)
    if (!response.ok) {
      throw new ApiError(errorMessageOf(payload, httpMessage(response.status)), {
        code: (payload as { code?: string } | null)?.code || `HTTP_${response.status}`,
        status: response.status,
        data: (payload as { data?: unknown } | null)?.data,
        requestId: requestIdOf(payload, response)
      })
    }

    if (payload && typeof payload === 'object' && 'code' in payload && 'data' in payload) {
      const envelope = payload as ApiResponse<T>
      if (envelope.code !== 'OK') {
        throw new ApiError(errorMessageOf(envelope, '操作未完成'), {
          code: envelope.code,
          status: response.status,
          data: envelope.data,
          requestId: envelope.request_id || ''
        })
      }
      return envelope.data
    }

    return payload as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('请求超时，请稍后重试', { code: 'TIMEOUT' })
    }
    throw new ApiError('无法连接后端服务，请确认服务已启动', {
      code: 'NETWORK_ERROR',
      data: error instanceof Error ? error.message : String(error)
    })
  } finally {
    window.clearTimeout(timer)
  }
}

export interface RawResult<T> {
  data: T | null
  notModified: boolean
  etag: string
}

export async function requestRaw<T>(
  path: string,
  options: RequestOptions = {}
): Promise<RawResult<T>> {
  const { body, timeout = REQUEST_TIMEOUT, headers: initHeaders, ...rest } = options
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeout)
  const headers = new Headers(initHeaders || {})
  headers.set('Accept', 'application/json')
  if (tokenStorage.access) headers.set('Authorization', `Bearer ${tokenStorage.access}`)
  let payloadBody: BodyInit | undefined
  if (body !== undefined) {
    if (body instanceof FormData || body instanceof Blob || typeof body === 'string') {
      payloadBody = body
    } else {
      headers.set('Content-Type', 'application/json')
      payloadBody = JSON.stringify(body)
    }
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers,
      body: payloadBody,
      signal: controller.signal
    })
    if (response.status === 304) {
      return { data: null, notModified: true, etag: response.headers.get('ETag') || '' }
    }
    const payload = await parseJson(response)
    if (!response.ok) {
      throw new ApiError(errorMessageOf(payload, httpMessage(response.status)), {
        code: (payload as { code?: string } | null)?.code || `HTTP_${response.status}`,
        status: response.status,
        data: (payload as { data?: unknown } | null)?.data,
        requestId: requestIdOf(payload, response)
      })
    }
    return {
      data: payload as T,
      notModified: false,
      etag: response.headers.get('ETag') || ''
    }
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('请求超时，请稍后重试', { code: 'TIMEOUT' })
    }
    throw new ApiError('无法连接后端服务，请确认服务已启动', {
      code: 'NETWORK_ERROR',
      data: error instanceof Error ? error.message : String(error)
    })
  } finally {
    window.clearTimeout(timer)
  }
}

export function assetUrl(path?: string | null, fallback = ''): string {
  if (!path) return fallback
  if (/^(https?:)?\/\//.test(path) || path.startsWith('data:') || path.startsWith('blob:')) {
    return path
  }
  if (path.startsWith('/uploads')) return `${FILE_BASE}${path}`
  if (path.startsWith('/assets')) return path
  if (path.startsWith('/')) return path
  return `${FILE_BASE}/${path}`
}

const CMS_CACHE_PREFIX = 'tanhui_cms_'

export async function getCmsConfig(pageKey: string): Promise<CmsConfig> {
  const cacheKey = `${CMS_CACHE_PREFIX}${pageKey}`
  let cached: CmsConfig | null = null
  let cachedEtag = ''
  try {
    const raw = localStorage.getItem(cacheKey)
    if (raw) {
      const parsed = JSON.parse(raw) as { etag?: string; data?: CmsConfig }
      cached = parsed.data || null
      cachedEtag = parsed.etag || ''
    }
  } catch {
    cached = null
  }

  const headers: Record<string, string> = {}
  if (cachedEtag) headers['If-None-Match'] = cachedEtag

  try {
    const result = await requestRaw<CmsConfig>(`/client/config/${encodeURIComponent(pageKey)}`, {
      headers
    })
    if (result.notModified) {
      if (cached) return cached
      throw new ApiError('页面配置缓存失效，请刷新重试', { code: 'CMS_CACHE_MISS' })
    }
    if (result.data) {
      try {
        localStorage.setItem(
          cacheKey,
          JSON.stringify({ etag: result.etag, data: result.data, saved_at: Date.now() })
        )
      } catch {
        // 忽略本地存储失败
      }
      return result.data
    }
  } catch (error) {
    if (cached) return cached
    throw error
  }
  if (cached) return cached
  throw new ApiError('页面配置暂不可用', { code: 'CMS_UNAVAILABLE' })
}
