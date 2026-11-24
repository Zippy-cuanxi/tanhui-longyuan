<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { catalogApi } from '@/api'
import type { Product } from '@/api/types'
import { errorText } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import ProductCard from '@/components/ProductCard.vue'
import StateBlock from '@/components/StateBlock.vue'
import OriginMapStage from '@/components/origin/OriginMapStage.vue'
import { provideHeatData } from '@/composables/useHeatData'

const route = useRoute()
const heat = provideHeatData()
const {
  data: heatData,
  selectedOriginId,
  selectedCityAdcode,
  selectedOrigin,
  selectCity,
  clearSelection
} = heat

// 地图不可用（WebGL 缺失 / 资源加载失败）时显示占位说明；?nomap=1 可强制预览
const fallback = ref(false)
const fallbackReason = ref('')
const forceFallback = computed(() => route.query.nomap === '1')

function onMapFallback(reason: string): void {
  console.warn('[origin] 地图回退：', reason)
  fallbackReason.value = reason
  fallback.value = true
}

function retryMap(): void {
  fallback.value = false
  fallbackReason.value = ''
}

// 旧版产地入口保留作兜底；keyword 同时用于新版商品筛选
const regions = [
  { name: '静宁苹果', keyword: '静宁', region: '平凉市静宁县', cityAdcode: '620800' },
  { name: '定西马铃薯', keyword: '定西', region: '定西市', cityAdcode: '621100' },
  { name: '民勤蜜瓜', keyword: '民勤', region: '武威市民勤县', cityAdcode: '620600' },
  { name: '甘肃枸杞', keyword: '枸杞', region: '白银市景泰县', cityAdcode: '620400' },
  { name: '临泽小枣', keyword: '临泽', region: '张掖市临泽县', cityAdcode: '620700' },
  { name: '兰州百合', keyword: '百合', region: '兰州市七里河区', cityAdcode: '620100' },
  { name: '岷县当归', keyword: '当归', region: '定西市岷县', cityAdcode: '621100' }
]

const cityBar = [
  { code: '', label: '全部' },
  { code: '620800', label: '平凉' },
  { code: '621100', label: '定西' },
  { code: '620600', label: '武威' },
  { code: '620400', label: '白银' },
  { code: '620700', label: '张掖' },
  { code: '620100', label: '兰州' }
]

const products = ref<Product[]>([])
const loading = ref(true)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const data = await catalogApi.products({ page: 1, page_size: 100 })
    products.value = data.items
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

const activeKeywords = computed<string[]>(() => {
  if (selectedOriginId.value) {
    const origin = heatData.value?.origins.find((item) => item.id === selectedOriginId.value)
    if (!origin) return []
    const matched = regions.find((region) => region.name === origin.name)
    return [matched?.keyword ?? origin.productName]
  }
  if (selectedCityAdcode.value) {
    return regions
      .filter((region) => region.cityAdcode === selectedCityAdcode.value)
      .map((region) => region.keyword)
  }
  return []
})

const hasFilter = computed(() => activeKeywords.value.length > 0)

const visibleProducts = computed(() => {
  if (!hasFilter.value) return products.value.slice(0, 12)
  const keywords = activeKeywords.value
  return products.value.filter((product) => {
    const haystack = `${product.title}${product.subtitle ?? ''}${product.store_name ?? ''}`
    return keywords.some((keyword) => haystack.includes(keyword))
  })
})

const filterEmpty = computed(
  () =>
    !loading.value &&
    !error.value &&
    products.value.length > 0 &&
    hasFilter.value &&
    visibleProducts.value.length === 0
)

const filterLabel = computed(() => {
  if (selectedOrigin.value) return selectedOrigin.value.name
  const city = cityBar.find((item) => item.code && item.code === selectedCityAdcode.value)
  return city?.label ?? ''
})

onMounted(() => {
  load()
  heat.load()
})
</script>

<template>
  <main class="page-main origin-page">
    <div class="page-container">
      <template v-if="!fallback && !forceFallback">
        <OriginMapStage @fallback="onMapFallback" />

        <nav class="origin-filter-bar" aria-label="按市州筛选产地">
          <button
            v-for="city in cityBar"
            :key="city.code"
            type="button"
            class="origin-filter-chip"
            :class="{
              active: city.code
                ? selectedCityAdcode === city.code
                : !selectedCityAdcode && !selectedOriginId
            }"
            @click="city.code ? selectCity(city.code) : clearSelection()"
          >
            {{ city.label }}
          </button>
        </nav>
      </template>

      <template v-else>
        <section class="origin-fallback-note" aria-label="地图加载提示">
          <span class="eyebrow">GANSU ORIGIN</span>
          <h1>甘肃产地地图</h1>
          <p v-if="forceFallback">当前为简化预览模式，3D 地图已暂停加载。</p>
          <p v-else>
            3D 地图未能加载{{ fallbackReason ? `（${fallbackReason}）` : '' }}。建议使用最新版
            Chrome / Edge，并确认浏览器已开启硬件加速。
          </p>
          <button
            v-if="!forceFallback"
            class="outline-button small"
            type="button"
            @click="retryMap"
          >
            重新加载 3D 地图
          </button>
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
      </template>

      <section class="section-block">
        <header class="section-heading">
          <h2>
            产地好物
            <span v-if="filterLabel && !fallback && !forceFallback" class="grid-filter-label">
              · {{ filterLabel }}
            </span>
            <button
              v-if="filterLabel && !fallback && !forceFallback"
              type="button"
              class="grid-filter-clear"
              @click="clearSelection()"
            >
              清除筛选
            </button>
          </h2>
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
          <div v-if="filterEmpty" class="origin-filter-empty">
            <p>该产地暂无匹配商品，看看其他产地吧。</p>
            <button class="outline-button small" type="button" @click="clearSelection()">
              查看全部商品
            </button>
          </div>
          <div v-else class="product-grid columns-4">
            <ProductCard v-for="product in visibleProducts" :key="product.id" :product="product" />
          </div>
        </StateBlock>
      </section>

      <section class="origin-story-grid compact">
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
