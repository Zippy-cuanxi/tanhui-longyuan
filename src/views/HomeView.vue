<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { catalogApi, cmsApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { Category, CmsConfig, Product } from '@/api/types'
import { errorText } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import BannerSection from '@/components/sections/BannerSection.vue'
import ProductGridSection from '@/components/sections/ProductGridSection.vue'
import ProductCard from '@/components/ProductCard.vue'
import StateBlock from '@/components/StateBlock.vue'
import CmsSectionRenderer from '@/components/CmsSectionRenderer.vue'

const config = ref<CmsConfig | null>(null)
const categories = ref<Category[]>([])
const fallbackProducts = ref<Product[]>([])
const loading = ref(true)
const error = ref('')
const cmsWarning = ref('')

const quickDefs = [
  { label: '新鲜水果', category: '水果生鲜', icon: 'fruit' },
  { label: '粮油杂粮', category: '粮油杂粮', icon: 'grains' },
  { label: '特色食品', category: '特色食品', icon: 'food' },
  { label: '甘肃文创', category: '文创礼品', icon: 'culture' },
  { label: '绿色积分', category: '', icon: 'points', to: '/account/points' }
]

const sections = computed(() =>
  (config.value?.sections || [])
    .filter((section) => section.enabled)
    .slice()
    .sort((a, b) => a.sort - b.sort)
)
const heroSection = computed(() =>
  sections.value.find((section) => section.section_type === 'banner')
)
const gridSection = computed(() =>
  sections.value.find((section) => section.section_type === 'product_grid')
)
const otherSections = computed(() =>
  sections.value.filter((section) => !['banner', 'product_grid'].includes(section.section_type))
)

const quickCategories = computed(() =>
  quickDefs.map((definition) => {
    const category = categories.value.find((item) => item.name === definition.category)
    return {
      ...definition,
      iconUrl: category?.icon_url
        ? assetUrl(category.icon_url, `/assets/categories/${definition.icon}.webp`)
        : `/assets/categories/${definition.icon}.webp`,
      to:
        definition.to ||
        (category
          ? `/products?category_id=${category.id}`
          : `/products?keyword=${encodeURIComponent(definition.category)}`)
    }
  })
)

const featured = computed(() => fallbackProducts.value.slice(0, 4))

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  cmsWarning.value = ''
  const [cmsResult, categoryResult, productResult] = await Promise.allSettled([
    cmsApi.config('home'),
    catalogApi.categories(),
    catalogApi.products({ page: 1, page_size: 8 })
  ])
  if (cmsResult.status === 'fulfilled') config.value = cmsResult.value
  else cmsWarning.value = errorText(cmsResult.reason)
  if (categoryResult.status === 'fulfilled') categories.value = categoryResult.value
  if (productResult.status === 'fulfilled') fallbackProducts.value = productResult.value.items
  else error.value = errorText(productResult.reason)
  loading.value = false
}

onMounted(load)
</script>

<template>
  <main class="page-main home-page">
    <div class="page-container">
      <div v-if="cmsWarning" class="soft-notice">
        <AppIcon name="info" :size="15" />
        首页动态配置暂不可用，已使用设计稿静态内容展示。
      </div>

      <BannerSection
        v-if="heroSection"
        :config="heroSection.config"
        variant="home"
        fallback-image="/assets/banners/home-hero.webp"
      />
      <BannerSection
        v-else
        :config="{
          title: '来自陇原的自然好物',
          image_url: '/assets/banners/home-hero.webp',
          link_url: '/products'
        }"
        variant="home"
      />

      <section class="quick-categories" aria-label="快捷分类">
        <RouterLink
          v-for="category in quickCategories"
          :key="category.label"
          :to="category.to"
          class="quick-category"
        >
          <span class="category-icon"><img :src="category.iconUrl" :alt="category.label" /></span>
          <strong>{{ category.label }}</strong>
        </RouterLink>
      </section>

      <div class="home-content-grid">
        <section class="featured-section">
          <ProductGridSection v-if="gridSection" :config="gridSection.config" :columns="4" />
          <template v-else>
            <header class="section-heading">
              <h2>精选推荐</h2>
              <RouterLink to="/products" class="more-link">
                更多 <AppIcon name="chevron-right" :size="14" />
              </RouterLink>
            </header>
            <StateBlock
              :loading="loading"
              :error="error"
              :empty="!loading && !error && !featured.length"
              empty-text="暂无推荐商品"
              @retry="load"
            />
            <div v-if="!loading && !error && featured.length" class="product-grid columns-4">
              <ProductCard v-for="product in featured" :key="product.id" :product="product" />
            </div>
          </template>
        </section>

        <aside class="origin-card">
          <header class="section-heading">
            <h2>甘肃产地地图</h2>
            <RouterLink to="/origin" class="more-link">
              探索更多 <AppIcon name="chevron-right" :size="14" />
            </RouterLink>
          </header>
          <RouterLink to="/origin" class="origin-image-link">
            <img
              src="/assets/banners/origin-map-card.webp"
              alt="甘肃产地地图——一县一品一好物，溯源直达原产地"
            />
            <span class="origin-image-copy">
              <strong>一县一品一好物</strong>
              <small>溯源直达原产地</small>
            </span>
          </RouterLink>
        </aside>
      </div>

      <RouterLink to="/green" class="green-banner" aria-label="绿色消费专区">
        <img src="/assets/banners/green-zone.webp" alt="绿色消费专区——每一次购物，都在为地球减负" />
      </RouterLink>

      <CmsSectionRenderer
        v-for="(section, index) in otherSections"
        :key="`${section.section_type}-${index}`"
        :section="section"
      />
    </div>
  </main>
</template>
