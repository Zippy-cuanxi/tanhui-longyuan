import { ref } from 'vue'
import { defineStore } from 'pinia'
import { isMockFailureEnabled, setMockFailureEnabled } from '@/console/api/mock'
import { resetDb } from '@/console/mock/db'

export const useConsoleApp = defineStore('console-app', () => {
  const collapsed = ref(false)
  const mockFail = ref(isMockFailureEnabled())

  function toggleCollapsed(): void {
    collapsed.value = !collapsed.value
  }

  function setMockFail(value: boolean): void {
    mockFail.value = value
    setMockFailureEnabled(value)
  }

  function resetMock(): void {
    resetDb()
    window.location.reload()
  }

  return { collapsed, mockFail, toggleCollapsed, setMockFail, resetMock }
})
