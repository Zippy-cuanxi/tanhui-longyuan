import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authApi } from '@/api'
import type { ProfileUpdateInput } from '@/api'
import { tokenStorage } from '@/api/http'
import type { Profile, User } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const profile = ref<Profile | null>(null)
  const loading = ref(false)
  const error = ref('')
  const initialized = ref(false)
  const authenticated = ref(Boolean(tokenStorage.access))

  const isAuthenticated = computed(() => authenticated.value)
  const displayName = computed(
    () => profile.value?.nickname || user.value?.email?.split('@')[0] || '陇原用户'
  )
  const avatarText = computed(() => displayName.value.slice(0, 1).toUpperCase())
  const avatarUrl = computed(() => profile.value?.avatar_url || '')
  const email = computed(() => user.value?.email || '')

  async function login(payload: { email: string; password: string; mfa_code?: string }) {
    loading.value = true
    error.value = ''
    try {
      const pair = await authApi.login(payload)
      tokenStorage.save(pair)
      authenticated.value = true
      await fetchMe()
    } catch (err) {
      error.value = (err as Error).message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(payload: { email: string; password: string; nickname?: string }) {
    loading.value = true
    error.value = ''
    try {
      await authApi.register(payload)
      await login({ email: payload.email, password: payload.password })
    } catch (err) {
      error.value = (err as Error).message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchMe(): Promise<void> {
    if (!tokenStorage.access) {
      authenticated.value = false
      user.value = null
      profile.value = null
      initialized.value = true
      return
    }
    try {
      const data = await authApi.me()
      user.value = data.user
      profile.value = data.profile || null
      authenticated.value = true
    } catch (err) {
      const status = (err as { status?: number }).status
      if (status === 401) {
        clearLocal()
      }
      throw err
    } finally {
      initialized.value = true
    }
  }

  async function updateProfile(payload: ProfileUpdateInput): Promise<Profile> {
    const updated = await authApi.updateMe(payload)
    profile.value = updated
    return updated
  }

  async function uploadAvatar(file: File): Promise<Profile> {
    const updated = await authApi.uploadAvatar(file)
    profile.value = updated
    return updated
  }

  async function logout(): Promise<void> {
    try {
      if (tokenStorage.access) await authApi.logout()
    } finally {
      clearLocal()
    }
  }

  function clearLocal(): void {
    tokenStorage.clear()
    authenticated.value = false
    user.value = null
    profile.value = null
  }

  async function bootstrap(): Promise<void> {
    if (!tokenStorage.access) {
      initialized.value = true
      return
    }
    try {
      await fetchMe()
    } catch {
      // 页面保留未登录态；具体错误由受保护页面处理
    }
  }

  window.addEventListener('auth:expired', clearLocal)

  return {
    user,
    profile,
    loading,
    error,
    initialized,
    isAuthenticated,
    displayName,
    avatarText,
    avatarUrl,
    email,
    login,
    register,
    fetchMe,
    updateProfile,
    uploadAvatar,
    logout,
    clearLocal,
    bootstrap
  }
})
