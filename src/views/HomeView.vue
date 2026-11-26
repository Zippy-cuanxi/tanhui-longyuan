<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, onMounted, ref } from 'vue'
import { catalogApi, cmsApi } from '@/api'
import type { Category, CmsConfig, Product } from '@/api/types'
import { errorText } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import HomeCarousel from '@/components/HomeCarousel.vue'
import HomeOriginMap from '@/components/HomeOriginMap.vue'
import ProductGridSection from '@/components/sections/ProductGridSection.vue'
import ProductCard from '@/components/ProductCard.vue'
import StateBlock from '@/components/StateBlock.vue'
import CmsSectionRenderer from '@/components/CmsSectionRenderer.vue'
import { useCatalogLive } from '@/composables/useCatalogLive'

const config = ref<CmsConfig | null>(null)
const categories = ref<Category[]>([])
const fallbackProducts = ref<Product[]>([])
const loading = ref(true)
const error = ref('')
const cmsWarning = ref('')

const quickDefs = [
  { label: '新鲜水果', category: '水果生鲜', icon: assetUrl('/images/categories/flat/fruit.webp') },
  {
    label: '粮油杂粮',
    category: '粮油杂粮',
    icon: assetUrl('/images/categories/flat/grains.webp')
  },
  { label: '特色食品', category: '特色食品', icon: assetUrl('/images/categories/flat/food.webp') },
  {
    label: '甘味文创',
    category: '文创礼品',
    icon: assetUrl('/images/categories/flat/culture.webp')
  },
  {
    label: '绿色积分',
    category: '',
    icon: assetUrl('/images/categories/flat/points.webp'),
    to: '/account/points'
  },
  {
    label: '优惠券商店',
    category: '',
    icon: assetUrl('/images/coupons/coupon-icon.webp'),
    to: '/coupons'
  }
]

const heroSlides = [
  {
    key: 'catalog',
    label: '全部商品',
    image: assetUrl('/images/banners/home-main-visual.webp'),
    to: '/products',
    alt: '全部商品——来自陇原的自然好物，绿色生态、品质优选、助力乡村振兴'
  },
  {
    key: 'origin',
    label: '甘肃产地',
    image: assetUrl('/images/banners/origin-map.webp'),
    to: '/origin',
    alt: '甘肃产地地图——一县一品一好物，溯源直达原产地'
  },
  {
    key: 'green',
    label: '绿色消费区',
    image: assetUrl('/images/banners/green.webp'),
    to: '/green',
    alt: '绿色消费专区——每一次购物，都在为地球减负'
  },
  {
    key: 'aid',
    label: '助农公益',
    image: assetUrl('/images/banners/aid.webp'),
    to: '/aid',
    alt: '助农公益——每一份订单，都是一份助农力量'
  },
  {
    key: 'join',
    label: '商家入驻',
    image: assetUrl('/images/banners/join.webp'),
    to: '/join',
    alt: '商家入驻——产地直供、平台赋能、共赢陇原'
  }
]
const sections = computed(() =>
  (config.value?.sections || [])
    .filter((section) => section.enabled)
    .slice()
    .sort((a, b) => a.sort - b.sort)
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
      iconUrl: definition.icon,
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
useCatalogLive(load)
</script>

<template>
  <main class="page-main home-page">
    <div class="page-container">
      <div v-if="cmsWarning" class="soft-notice">
        <AppIcon name="info" :size="15" />
        首页动态配置暂不可用，已使用设计稿静态内容展示。
      </div>

      <div class="home-announcement">
        <span>甘肃产地直供 · 让陇原好物走进日常</span>
        <RouterLink to="/green">绿色消费可累计绿色积分</RouterLink>
        <RouterLink to="/aid">公益助农进度 <AppIcon name="chevron-right" :size="12" /></RouterLink>
      </div>

      <HomeCarousel :slides="heroSlides" />

      <div class="home-hero-actions">
        <RouterLink to="/products" class="primary-button">
          逛精选好物 <AppIcon name="arrow-right" :size="15" />
        </RouterLink>
        <RouterLink to="/origin" class="outline-button">
          探索甘肃产地 <AppIcon name="map" :size="15" />
        </RouterLink>
        <span class="home-hero-note">好产地 · 好味道 · 看得见的绿色价值</span>
      </div>

      <section class="home-category-block" aria-label="按品类逛陇原">
        <header class="home-section-head">
          <div>
            <span class="eyebrow">按品类逛陇原</span>
            <h2>找到你的家乡味</h2>
          </div>
          <RouterLink to="/products" class="home-section-link">
            全部商品 <AppIcon name="chevron-right" :size="14" />
          </RouterLink>
        </header>
        <div class="quick-categories">
          <RouterLink
            v-for="category in quickCategories"
            :key="category.label"
            :to="category.to"
            class="quick-category"
          >
            <span class="category-icon">
              <img :src="category.iconUrl" :alt="category.label" loading="lazy" decoding="async" />
            </span>
            <strong>{{ category.label }}</strong>
          </RouterLink>
        </div>
      </section>

      <section class="featured-section home-featured">
        <header class="home-section-head">
          <div>
            <span class="eyebrow">陇原人气好物</span>
            <h2>从产地到餐桌，把当季鲜味带回家</h2>
          </div>
          <RouterLink to="/products" class="home-section-link">
            查看全部商品 <AppIcon name="chevron-right" :size="14" />
          </RouterLink>
        </header>
        <ProductGridSection
          v-if="gridSection"
          :config="gridSection.config"
          :columns="4"
          :show-heading="false"
        />
        <template v-else>
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

      <section class="home-map-section" aria-labelledby="home-map-title">
        <header class="home-section-head">
          <div>
            <span class="eyebrow">甘肃特产 · 一县一品</span>
            <h2 id="home-map-title">沿着地图，去看甘肃好产地</h2>
            <p>从河西走廊到陇东高原，悬停查看市州产地信息，点击进入对应商品列表。</p>
          </div>
          <RouterLink to="/origin" class="outline-button small">
            探索产地 <AppIcon name="arrow-right" :size="14" />
          </RouterLink>
        </header>
        <div class="home-map-layout">
          <div class="home-map-panel">
            <HomeOriginMap />
          </div>
          <aside class="home-map-aside">
            <span class="eyebrow">从一方水土，发现更多陇原好物</span>
            <h3>点一点地图，找到家乡味</h3>
            <ul class="home-map-points">
              <li><AppIcon name="location" :size="16" />悬停市州可查看年销与产地好物</li>
              <li><AppIcon name="arrow-right" :size="16" />点击市州直达对应产地商品列表</li>
              <li><AppIcon name="leaf" :size="16" />产地信息来自平台商品数据</li>
            </ul>
            <p class="home-map-note">地图支持鼠标与键盘操作，Tab 聚焦后按回车即可跳转。</p>
            <RouterLink to="/origin" class="primary-button">
              探索甘肃产地 <AppIcon name="map" :size="15" />
            </RouterLink>
          </aside>
        </div>
      </section>

      <section class="home-topic-grid" aria-label="绿色消费与助农公益">
        <RouterLink to="/green" class="home-topic-card">
          <img
            :src="assetUrl('/images/banners/green.webp')"
            alt="绿色消费专区——每一次购物，都在为地球减负"
            loading="lazy"
            decoding="async"
          />
        </RouterLink>
        <RouterLink to="/aid" class="home-topic-card">
          <img
            :src="assetUrl('/images/banners/aid.webp')"
            alt="助农项目——每一份订单，都是一份助农力量"
            loading="lazy"
            decoding="async"
          />
        </RouterLink>
      </section>

      <CmsSectionRenderer
        v-for="(section, index) in otherSections"
        :key="`${section.section_type}-${index}`"
        :section="section"
      />
    </div>
  </main>
</template>
