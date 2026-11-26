<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { catalogApi } from '@/api'
import type { Product } from '@/api/types'
import { asString, asStringArray } from '@/utils/cms'
import { errorText } from '@/utils/format'
import ProductCard from '../ProductCard.vue'
import StateBlock from '../StateBlock.vue'
import AppIcon from '../AppIcon.vue'

const props = withDefaults(
  defineProps<{
    config: Record<string, unknown>
    columns?: number
    showHeading?: boolean
  }>(),
  {
    columns: 4,
    showHeading: true
  }
)

const products = ref<Product[]>([])
const loading = ref(true)
const error = ref('')

const title = asString(props.config.title, '精选推荐')
const productIds = asStringArray(props.config.product_ids)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  if (!productIds.length) {
    products.value = []
    loading.value = false
    return
  }
  try {
    const data = await catalogApi.products({ page: 1, page_size: 100 })
    const productMap = new Map(data.items.map((product) => [product.id, product]))
    products.value = productIds
      .map((id) => productMap.get(id))
      .filter((product): product is Product => Boolean(product))
    if (!products.value.length) error.value = '推荐商品暂不可用'
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="section-block cms-product-grid">
    <header v-if="showHeading" class="section-heading">
      <h2>{{ title }}</h2>
      <RouterLink to="/products" class="more-link">
        更多 <AppIcon name="chevron-right" :size="14" />
      </RouterLink>
    </header>
    <StateBlock
      :loading="loading"
      :error="error"
      :empty="!loading && !error && !products.length"
      empty-text="暂无推荐商品"
      @retry="load"
    />
    <div
      v-if="!loading && !error && products.length"
      class="product-grid"
      :style="{ '--columns': columns || 4 }"
    >
      <ProductCard v-for="product in products" :key="product.id" :product="product" />
    </div>
  </section>
</template>
