import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { hasPermission } from '@/console/constants/permissions'
import type { ConsoleRole, ConsoleSession } from '@/console/api/types'

/**
 * 登录/刷新才用得到完整的管理端 mock 数据层（含 20KB+ 种子数据）。
 * 这里改为按需动态加载，避免这些代码进入消费者商城首屏入口包。
 */
type AuthApiModule = typeof import('@/console/api/auth')
let authApiPromise: Promise<AuthApiModule> | null = null
function loadAuthApi(): Promise<AuthApiModule> {
  if (!authApiPromise) authApiPromise = import('@/console/api/auth')
  return authApiPromise
}

const SESSION_KEY = 'tanhui_console_session'
const REMEMBER_KEY = 'tanhui_console_remember'

function readSession(): ConsoleSession | null {
  const candidates = [localStorage.getItem(SESSION_KEY), sessionStorage.getItem(SESSION_KEY)]
  for (const raw of candidates) {
    if (!raw) continue
    try {
      const parsed = JSON.parse(raw) as ConsoleSession
      if (parsed && (parsed.role === 'merchant' || parsed.role === 'admin') && parsed.token) {
        return parsed
      }
    } catch {
      // 忽略损坏数据
    }
  }
  return null
}

export const useConsoleAuth = defineStore('console-auth', () => {
  const session = ref<ConsoleSession | null>(readSession())
  const remember = ref(localStorage.getItem(REMEMBER_KEY) !== '0')
  const lastSync = ref(0)

  const isAuthenticated = computed(() => Boolean(session.value))
  const role = computed<ConsoleRole | null>(() => session.value?.role || null)
  const isMerchant = computed(() => session.value?.role === 'merchant')
  const isAdmin = computed(() => session.value?.role === 'admin')
  const permissions = computed(() => session.value?.permissions || [])
  const displayName = computed(() => {
    if (!session.value) return ''
    if (session.value.role === 'merchant') return session.value.account.companyName
    return session.value.account.name
  })
  const accountName = computed(() => {
    if (!session.value) return ''
    return session.value.role === 'merchant'
      ? session.value.account.ownerName
      : session.value.account.name
  })
  const avatar = computed(() => {
    if (!session.value) return ''
    return session.value.account.avatar
  })
  const merchantStatus = computed(() =>
    session.value?.role === 'merchant' ? session.value.status : null
  )
  const merchantAccount = computed(() =>
    session.value?.role === 'merchant' ? session.value.account : null
  )
  const adminAccount = computed(() =>
    session.value?.role === 'admin' ? session.value.account : null
  )
  const adminRoleName = computed(() =>
    session.value?.role === 'admin' ? session.value.account.roleName : ''
  )
  const roleHome = computed(() => {
    if (!session.value) return '/console/login'
    if (session.value.role === 'merchant') {
      return session.value.status === 'normal'
        ? '/console/merchant/dashboard'
        : '/console/merchant/status'
    }
    return '/console/admin/dashboard'
  })

  function persist(): void {
    if (!session.value) {
      localStorage.removeItem(SESSION_KEY)
      sessionStorage.removeItem(SESSION_KEY)
      return
    }
    const raw = JSON.stringify(session.value)
    if (remember.value) {
      localStorage.setItem(SESSION_KEY, raw)
      sessionStorage.removeItem(SESSION_KEY)
    } else {
      sessionStorage.setItem(SESSION_KEY, raw)
      localStorage.removeItem(SESSION_KEY)
    }
    localStorage.setItem(REMEMBER_KEY, remember.value ? '1' : '0')
  }

  async function login(
    roleValue: ConsoleRole,
    username: string,
    password: string
  ): Promise<ConsoleSession> {
    const { authApi } = await loadAuthApi()
    const result = await authApi.login({ role: roleValue, username, password })
    session.value = result
    lastSync.value = Date.now()
    persist()
    return result
  }

  async function logout(): Promise<void> {
    try {
      const { authApi } = await loadAuthApi()
      await authApi.logout()
    } finally {
      session.value = null
      lastSync.value = 0
      localStorage.removeItem(SESSION_KEY)
      sessionStorage.removeItem(SESSION_KEY)
    }
  }

  function setRemember(value: boolean): void {
    remember.value = value
    persist()
  }

  async function refresh(): Promise<void> {
    if (!session.value) return
    try {
      const { authApi } = await loadAuthApi()
      session.value = await authApi.me(session.value)
      lastSync.value = Date.now()
      persist()
    } catch {
      session.value = null
      lastSync.value = 0
      localStorage.removeItem(SESSION_KEY)
      sessionStorage.removeItem(SESSION_KEY)
    }
  }

  async function ensureFresh(): Promise<void> {
    if (!session.value) return
    if (Date.now() - lastSync.value < 15000) return
    await refresh()
  }

  function can(code?: string | null): boolean {
    return hasPermission(permissions.value, code)
  }

  return {
    session,
    remember,
    isAuthenticated,
    role,
    isMerchant,
    isAdmin,
    permissions,
    displayName,
    accountName,
    avatar,
    merchantStatus,
    merchantAccount,
    adminAccount,
    adminRoleName,
    roleHome,
    login,
    logout,
    setRemember,
    refresh,
    ensureFresh,
    can
  }
})
