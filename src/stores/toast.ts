import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export const useToastStore = defineStore('toast', () => {
  const visible = ref(false)
  const message = ref('')
  const type = ref<ToastType>('success')
  const requestId = ref('')
  let timer: number | undefined

  const icon = computed(() => {
    if (type.value === 'success') return 'check'
    if (type.value === 'error') return 'alert'
    if (type.value === 'warning') return 'alert'
    return 'info'
  })

  function show(text: string, kind: ToastType = 'success', reqId = ''): void {
    message.value = text
    type.value = kind
    requestId.value = reqId
    visible.value = true
    if (timer) window.clearTimeout(timer)
    timer = window.setTimeout(
      () => {
        visible.value = false
      },
      kind === 'error' ? 5200 : 2600
    )
  }

  function hide(): void {
    visible.value = false
    if (timer) window.clearTimeout(timer)
  }

  return { visible, message, type, requestId, icon, show, hide }
})
