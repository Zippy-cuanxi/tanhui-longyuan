<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { catalogApi } from '@/api'
import type { Product } from '@/api/types'
import { errorText } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import BannerSection from '@/components/sections/BannerSection.vue'
import ProductCard from '@/components/ProductCard.vue'
import StateBlock from '@/components/StateBlock.vue'

const products = ref<Product[]>([])
const loading = ref(true)
const error = ref('')

const regions = [
  { name: '静宁苹果', keyword: '静宁', region: '平凉市静宁县' },
  { name: '定西马铃薯', keyword: '定西', region: '定西市' },
  { name: '民勤蜜瓜', keyword: '民勤', region: '武威市民勤县' },
  { name: '甘肃枸杞', keyword: '枸杞', region: '白银市景泰县' },
  { name: '临泽小枣', keyword: '临泽', region: '张掖市临泽县' },
  { name: '兰州百合', keyword: '百合', region: '兰州市七里河区' },
  { name: '岷县当归', keyword: '当归', region: '定西市岷县' }
]

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const data = await catalogApi.products({ page: 1, page_size: 12 })
    products.value = data.items
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-main origin-page">
    <div class="page-container">
      <BannerSection
        :config="{
          title: '甘肃产地地图',
          image_url: '/assets/banners/origin-map.webp',
          link_url: '/origin'
        }"
        variant="page"
        fallback-image="/assets/banners/origin-map.webp"
      />

      <section class="page-intro">
        <span class="eyebrow">GANSU ORIGIN</span>
        <h1>一县一品一好物，溯源直达原产地</h1>
        <p>
          从河西走廊到陇中高原，甘肃不同产区孕育了各具风味的农特产品。平台按产地组织商品，绿色资料可在商品详情页查看。
        </p>
      </section>

      <section class="region-chips" aria-label="甘肃产地">
        <RouterLink
          v-for="region in regions"
          :key="region.name"
          :to="{ name: 'products', query: { keyword: region.keyword } }"
          class="region-chip"
        >
          <span class="region-pin"><AppIcon name="location" :size="16" /></span>
          <div>
            <strong>{{ region.name }}</strong>
            <small>{{ region.region }}</small>
          </div>
          <AppIcon name="chevron-right" :size="14" />
        </RouterLink>
      </section>

      <section class="section-block">
        <header class="section-heading">
          <h2>产地好物</h2>
          <RouterLink to="/products" class="more-link"
            >全部商品 <AppIcon name="chevron-right" :size="14"
          /></RouterLink>
        </header>
        <StateBlock
          :loading="loading"
          :error="error"
          :empty="!loading && !error && !products.length"
          empty-text="暂无产地商品"
          @retry="load"
        >
          <div class="product-grid columns-4">
            <ProductCard v-for="product in products" :key="product.id" :product="product" />
          </div>
        </StateBlock>
      </section>

      <section class="origin-story-grid">
        <article>
          <span><AppIcon name="mountain" :size="22" /></span>
          <h3>高原与绿洲</h3>
          <p>甘肃跨越高原、河谷与绿洲，日照充足、昼夜温差大，形成了多样的农产品风味。</p>
        </article>
        <article>
          <span><AppIcon name="sprout" :size="22" /></span>
          <h3>产地直发</h3>
          <p>平台商品由产地店铺发货，商品详情页展示店铺与产地信息，便于溯源。</p>
        </article>
        <article>
          <span><AppIcon name="shield" :size="22" /></span>
          <h3>平台审核</h3>
          <p>商品需经平台审核后上架；绿色资料由商家提交并经平台审核后展示。</p>
        </article>
      </section>
    </div>
  </main>
</template>
