<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogApi } from '@/api'
import type { Product } from '@/api/types'
import { errorText, money, productFallbackImage } from '@/utils/format'
import { productMainImage } from '@/utils/productMedia'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { useToastStore } from '@/stores/toast'
import AppIcon from './AppIcon.vue'

const props = withDefaults(
  defineProps<{ product: Product; compact?: boolean; variant?: 'default' | 'catalog' }>(),
  {
    compact: false,
    variant: 'default'
  }
)
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const cart = useCartStore()
const toast = useToastStore()
const adding = ref(false)
const displayImage = computed(() => productMainImage(props.product))
const imageAlt = computed(() => props.product.title)

function open(): void {
  router.push({ name: 'product-detail', params: { id: props.product.id } })
}

function requireLogin(): boolean {
  if (auth.isAuthenticated) return true
  router.push({ name: 'login', query: { redirect: route.fullPath } })
  return false
}

async function addToCart(): Promise<void> {
  if (!requireLogin()) return
  adding.value = true
  try {
    const detail = await catalogApi.product(props.product.id)
    const sku = detail.skus?.find((item) => item.is_active)
    if (!sku) {
      toast.show('该商品暂无可购买规格', 'warning')
      return
    }
    await cart.add(sku.id, 1)
  } catch (error) {
    toast.show(errorText(error), 'error', (error as { requestId?: string }).requestId)
  } finally {
    adding.value = false
  }
}

function imageFallback(event: Event): void {
  const img = event.target as HTMLImageElement
  const fallback = productFallbackImage(props.product.title)
  if (img.src.endsWith(fallback)) return
  img.src = fallback
}
</script>

<template>
  <article
    class="product-card"
    :class="{ compact, catalog: variant === 'catalog' }"
    tabindex="0"
    @click="open"
    @keydown.enter="open"
  >
    <div class="product-image-wrap">
      <img
        class="product-image"
        :src="displayImage"
        :alt="imageAlt"
        loading="lazy"
        @error="imageFallback"
      />
      <span v-if="product.aid_project_id" class="product-badge">助农好物</span>
      <span class="product-leaf" title="绿色资料可在详情页查看">
        <AppIcon name="leaf" :size="14" />
      </span>
    </div>
    <div class="product-card-body">
      <h3>{{ product.title }}</h3>
      <p>{{ product.subtitle || product.store_name || '甘肃产地好物' }}</p>
      <div class="product-card-bottom">
        <span class="product-price"><small>¥</small>{{ money(product.min_price) }}</span>
        <button
          class="card-cart-button"
          type="button"
          :disabled="adding"
          :aria-label="`将${product.title}加入购物车`"
          @click.stop="addToCart"
        >
          <span v-if="adding" class="mini-spinner" />
          <AppIcon v-else name="cart" :size="18" />
        </button>
      </div>
    </div>
  </article>
</template>
