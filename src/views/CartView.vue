<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { assetUrl } from '@/api/http'
import type { CartItem } from '@/api/types'
import { errorText, productFallbackImage } from '@/utils/format'
import { useCartStore } from '@/stores/cart'
import { useCheckoutStore } from '@/stores/checkout'
import { useConfirmStore } from '@/stores/confirm'
import { useToastStore } from '@/stores/toast'
import AppIcon from '@/components/AppIcon.vue'
import QuantityStepper from '@/components/QuantityStepper.vue'
import StateBlock from '@/components/StateBlock.vue'

const cart = useCartStore()
const checkout = useCheckoutStore()
const confirm = useConfirmStore()
const toast = useToastStore()
const router = useRouter()

const groups = computed(() => {
  const map = new Map<string, { store_id: string; store_name: string; items: CartItem[] }>()
  cart.items.forEach((item) => {
    const group = map.get(item.store_id) || {
      store_id: item.store_id,
      store_name: item.store_name,
      items: []
    }
    group.items.push(item)
    map.set(item.store_id, group)
  })
  return [...map.values()]
})

const checkedCount = computed(() => cart.checkedItems.reduce((sum, item) => sum + item.quantity, 0))

async function load(): Promise<void> {
  try {
    await cart.fetchCart()
  } catch {
    // 错误由 StateBlock 展示
  }
}

async function toggle(item: CartItem): Promise<void> {
  try {
    await cart.update(item, { checked: !item.checked })
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  }
}

async function changeQuantity(item: CartItem, quantity: number): Promise<void> {
  try {
    await cart.update(item, { quantity })
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  }
}

async function toggleAll(): Promise<void> {
  try {
    await cart.setAllChecked(!cart.allChecked)
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  }
}

async function remove(item: CartItem): Promise<void> {
  const ok = await confirm.ask({
    title: '移除商品',
    message: `确认将「${item.product_title}」从购物车移除吗？`,
    confirmText: '移除',
    danger: true
  })
  if (!ok) return
  try {
    await cart.remove(item)
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  }
}

function goCheckout(): void {
  if (!cart.checkedItems.length) {
    toast.show('请先勾选要结算的商品', 'warning')
    return
  }
  checkout.clearDirect()
  router.push({ name: 'checkout' })
}

onMounted(load)
</script>

<template>
  <main class="page-main cart-page">
    <div class="page-container">
      <header class="page-heading">
        <div>
          <span class="eyebrow">SHOPPING CART</span>
          <h1>购物车</h1>
          <p>共 {{ cart.count }} 件商品，价格与库存以服务端实时数据为准。</p>
        </div>
        <RouterLink to="/products" class="outline-button small">
          <AppIcon name="arrow-right" :size="15" />继续选购
        </RouterLink>
      </header>

      <StateBlock
        :loading="cart.loading && !cart.loaded"
        :error="cart.error"
        :empty="!cart.loading && !cart.error && !cart.items.length"
        empty-text="购物车还是空的，去挑几件陇原好物吧"
        @retry="load"
      >
        <template #empty-action>
          <RouterLink to="/products" class="primary-button">去逛逛</RouterLink>
        </template>
      </StateBlock>

      <div v-if="cart.items.length" class="cart-layout">
        <section class="cart-main">
          <div class="cart-toolbar">
            <label class="check-row">
              <input type="checkbox" :checked="cart.allChecked" @change="toggleAll" />
              <span>全选</span>
            </label>
            <span class="muted-text"
              >共 {{ groups.length }} 个店铺 · {{ cart.totalQuantity }} 件</span
            >
          </div>

          <article v-for="group in groups" :key="group.store_id" class="cart-store">
            <header class="cart-store-head">
              <span class="store-mark"><AppIcon name="location" :size="15" /></span>
              <strong>{{ group.store_name }}</strong>
              <span class="muted-text">产地直发</span>
            </header>

            <ul class="cart-list">
              <li v-for="item in group.items" :key="item.id" class="cart-item">
                <label class="item-check">
                  <input
                    type="checkbox"
                    :checked="item.checked"
                    :aria-label="`选择${item.product_title}`"
                    @change="toggle(item)"
                  />
                </label>
                <RouterLink :to="`/products/${item.product_id}`" class="cart-item-image">
                  <img
                    :src="assetUrl(item.image_url, productFallbackImage(item.product_title))"
                    :alt="item.product_title"
                  />
                </RouterLink>
                <div class="cart-item-info">
                  <RouterLink :to="`/products/${item.product_id}`" class="cart-item-title">
                    {{ item.product_title }}
                  </RouterLink>
                  <span>{{ item.spec }}</span>
                  <small>库存 {{ item.stock_available }} 件</small>
                  <div class="cart-item-bottom">
                    <span class="cart-item-price"><small>¥</small>{{ item.current_price }}</span>
                    <QuantityStepper
                      compact
                      :model-value="item.quantity"
                      :min="1"
                      :max="Math.min(999, Math.max(1, item.stock_available))"
                      @change="(value) => changeQuantity(item, value)"
                    />
                  </div>
                </div>
                <button
                  type="button"
                  class="remove-item"
                  aria-label="移除商品"
                  @click="remove(item)"
                >
                  <AppIcon name="trash" :size="16" />
                </button>
              </li>
            </ul>
          </article>
        </section>

        <aside class="cart-summary">
          <span class="eyebrow">ORDER SUMMARY</span>
          <h2>结算信息</h2>
          <dl>
            <div>
              <dt>已选商品</dt>
              <dd>{{ checkedCount }} 件</dd>
            </div>
            <div>
              <dt>商品小计</dt>
              <dd>¥{{ cart.checkedSubtotal }}</dd>
            </div>
            <div>
              <dt>运费</dt>
              <dd class="muted-text">结算页计算</dd>
            </div>
          </dl>
          <p class="summary-note">运费、绿色积分抵扣与应付金额由服务端在下单预览时计算。</p>
          <button
            class="primary-button full-button"
            type="button"
            :disabled="!cart.checkedItems.length"
            @click="goCheckout"
          >
            去结算 <AppIcon name="arrow-right" :size="16" />
          </button>
          <RouterLink to="/products" class="ghost-button full-button">继续购物</RouterLink>
        </aside>
      </div>
    </div>
  </main>
</template>
