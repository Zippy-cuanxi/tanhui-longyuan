<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { catalogApi, greenApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { GreenDetail, Product } from '@/api/types'
import { errorText, money, productFallbackImage } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import BannerSection from '@/components/sections/BannerSection.vue'
import StateBlock from '@/components/StateBlock.vue'

const products = ref<Product[]>([])
const greenMap = ref<Record<string, GreenDetail | null>>({})
const loading = ref(true)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const data = await catalogApi.products({ page: 1, page_size: 20 })
    products.value = data.items
    const results = await Promise.allSettled(
      data.items.map((product) => greenApi.detail(product.id))
    )
    const map: Record<string, GreenDetail | null> = {}
    data.items.forEach((product, index) => {
      const result = results[index]
      map[product.id] = result?.status === 'fulfilled' ? result.value : null
    })
    greenMap.value = map
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-main green-page">
    <div class="page-container">
      <BannerSection
        :config="{
          title: '绿色消费专区',
          image_url: '/assets/banners/green-zone.webp',
          link_url: '/green'
        }"
        variant="page"
        fallback-image="/assets/banners/green-zone.webp"
      />

      <section class="page-intro">
        <span class="eyebrow">GREEN CONSUMPTION</span>
        <h1>每一次购物，都在为地球减负</h1>
        <p>
          绿色消费专区汇集已提交绿色资料的商品。资料由商家提交、平台审核；未核验的碳评估数据会明确标记，不冒充已核验结论。
        </p>
      </section>

      <StateBlock
        :loading="loading"
        :error="error"
        :empty="!loading && !error && !products.length"
        empty-text="暂无绿色资料商品"
        @retry="load"
      >
        <div class="green-product-grid">
          <article v-for="product in products" :key="product.id" class="green-product-card">
            <RouterLink :to="`/products/${product.id}`" class="green-product-image">
              <img
                :src="assetUrl(product.cover_url, productFallbackImage(product.title))"
                :alt="product.title"
              />
              <span class="green-product-badge"><AppIcon name="leaf" :size="13" />绿色资料</span>
            </RouterLink>
            <div class="green-product-body">
              <h2>
                <RouterLink :to="`/products/${product.id}`">{{ product.title }}</RouterLink>
              </h2>
              <p>{{ greenMap[product.id]?.profile?.origin || '产地信息待补充' }}</p>
              <span v-if="greenMap[product.id]?.profile" class="green-status">
                <AppIcon name="check" :size="13" />绿色资料已审核
              </span>
              <span v-else class="green-status muted">绿色资料待补充</span>
              <div class="green-product-foot">
                <span class="product-price"><small>¥</small>{{ money(product.min_price) }}</span>
                <RouterLink
                  :to="`/products/${product.id}`"
                  class="card-cart-button"
                  aria-label="查看商品"
                >
                  <AppIcon name="arrow-right" :size="16" />
                </RouterLink>
              </div>
            </div>
          </article>
        </div>
      </StateBlock>

      <p class="page-note">
        <AppIcon name="info" :size="15" />
        绿色资料与碳数据以平台审核记录为准；未核验数据不会展示为已核验。
      </p>
    </div>
  </main>
</template>
