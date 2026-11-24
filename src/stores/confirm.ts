import { reactive } from 'vue'
import { defineStore } from 'pinia'

interface ConfirmOptions {
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
}

export const useConfirmStore = defineStore('confirm', () => {
  const state = reactive({
    visible: false,
    title: '请确认',
    message: '',
    confirmText: '确认',
    cancelText: '取消',
    danger: false
  })
  let resolver: ((value: boolean) => void) | null = null

  function ask(options: ConfirmOptions): Promise<boolean> {
    if (resolver) resolver(false)
    state.title = options.title || '请确认'
    state.message = options.message
    state.confirmText = options.confirmText || '确认'
    state.cancelText = options.cancelText || '取消'
    state.danger = Boolean(options.danger)
    state.visible = true
    return new Promise<boolean>((resolve) => {
      resolver = resolve
    })
  }

  function settle(value: boolean): void {
    state.visible = false
    if (resolver) {
      resolver(value)
      resolver = null
    }
  }

  return { state, ask, settle }
})
