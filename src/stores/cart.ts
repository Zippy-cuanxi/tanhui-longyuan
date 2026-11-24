import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { cartApi } from '@/api'
import type { Cart, CartItem } from '@/api/types'
import { useToastStore } from './toast'

export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const totalQuantity = ref(0)
  const checkedSubtotal = ref('0.00')
  const loading = ref(false)
  const error = ref('')
  const loaded = ref(false)

  const count = computed(() => totalQuantity.value)
  const checkedItems = computed(() => items.value.filter((item) => item.checked))
  const allChecked = computed(
    () => items.value.length > 0 && items.value.every((item) => item.checked)
  )

  function apply(data: Cart): void {
    items.value = data.items || []
    totalQuantity.value = data.total_quantity || 0
    checkedSubtotal.value = data.checked_subtotal || '0.00'
    loaded.value = true
  }

  async function fetchCart(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      apply(await cartApi.get())
    } catch (err) {
      error.value = (err as Error).message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function add(skuId: string, quantity = 1): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      await cartApi.add({ sku_id: skuId, quantity })
      await fetchCart()
      useToastStore().show('已加入购物车', 'success')
    } catch (err) {
      error.value = (err as Error).message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function update(item: CartItem, payload: { quantity?: number; checked?: boolean }) {
    error.value = ''
    try {
      await cartApi.update(item.id, payload)
      await fetchCart()
    } catch (err) {
      error.value = (err as Error).message
      throw err
    }
  }

  async function remove(item: CartItem): Promise<void> {
    error.value = ''
    try {
      await cartApi.remove(item.id)
      await fetchCart()
      useToastStore().show('已从购物车移除', 'success')
    } catch (err) {
      error.value = (err as Error).message
      throw err
    }
  }

  async function setAllChecked(checked: boolean): Promise<void> {
    error.value = ''
    try {
      await Promise.all(
        items.value
          .filter((item) => item.checked !== checked)
          .map((item) => cartApi.update(item.id, { checked }))
      )
      await fetchCart()
    } catch (err) {
      error.value = (err as Error).message
      throw err
    }
  }

  function clear(): void {
    items.value = []
    totalQuantity.value = 0
    checkedSubtotal.value = '0.00'
    loading.value = false
    error.value = ''
    loaded.value = false
  }

  window.addEventListener('auth:expired', clear)

  return {
    items,
    totalQuantity,
    checkedSubtotal,
    loading,
    error,
    loaded,
    count,
    checkedItems,
    allChecked,
    fetchCart,
    add,
    update,
    remove,
    setAllChecked,
    clear
  }
})
