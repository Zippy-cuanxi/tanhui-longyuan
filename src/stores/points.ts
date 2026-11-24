import { ref } from 'vue'
import { defineStore } from 'pinia'
import { pointsApi } from '@/api'
import { useAuthStore } from './auth'

export const usePointsStore = defineStore('points', () => {
  const balance = ref<number | null>(null)
  const loading = ref(false)
  const error = ref('')

  async function fetchBalance(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const account = await pointsApi.account()
      balance.value = account.balance
    } catch (err) {
      error.value = (err as Error).message
    } finally {
      loading.value = false
    }
  }

  function setBalance(value: number): void {
    balance.value = value
  }

  function clear(): void {
    balance.value = null
    error.value = ''
  }

  let refreshTimer = 0

  function refreshIfAuthenticated(): void {
    if (!useAuthStore().isAuthenticated) return
    window.clearTimeout(refreshTimer)
    refreshTimer = window.setTimeout(() => {
      void fetchBalance()
    }, 120)
  }

  window.addEventListener('points:changed', refreshIfAuthenticated)
  window.addEventListener('focus', refreshIfAuthenticated)
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refreshIfAuthenticated()
  })

  return { balance, loading, error, fetchBalance, setBalance, clear }
})
