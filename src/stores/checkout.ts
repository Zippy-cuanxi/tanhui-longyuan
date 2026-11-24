import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { OrderItemInput } from '@/api/types'

const KEY = 'tanhui_checkout_direct'

export interface CheckoutDirectItem extends OrderItemInput {
  title?: string
  image_url?: string
  spec?: string
  price?: string
}

function readDirect(): CheckoutDirectItem[] | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as CheckoutDirectItem[]
    return Array.isArray(parsed) && parsed.length ? parsed : null
  } catch {
    return null
  }
}

export const useCheckoutStore = defineStore('checkout', () => {
  const directItems = ref<CheckoutDirectItem[] | null>(readDirect())

  function setDirect(items: CheckoutDirectItem[]): void {
    directItems.value = items
    try {
      sessionStorage.setItem(KEY, JSON.stringify(items))
    } catch {
      // 忽略存储失败
    }
  }

  function clearDirect(): void {
    directItems.value = null
    try {
      sessionStorage.removeItem(KEY)
    } catch {
      // 忽略存储失败
    }
  }

  return { directItems, setDirect, clearDirect }
})
