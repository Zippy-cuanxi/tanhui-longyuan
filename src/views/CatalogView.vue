<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogApi, greenApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { Category, GreenDetail, Pagination, Product } from '@/api/types'
import { errorText, money, productFallbackImage } from '@/utils/format'
import { useToastStore } from '@/stores/toast'
import { useRefreshOnFocus } from '@/composables/useRefreshOnFocus'
import AppIcon from '@/components/AppIcon.vue'
import ProductCard from '@/components/ProductCard.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import StateBlock from '@/components/StateBlock.vue'

interface CategoryDef {
  key: string
  label: string
  categoryName: string
  linear: string
  to?: string
}
interface CategoryItem extends CategoryDef {
  category: Category | null
}
interface ReviewPick {
  product: Product
  score: number
}

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const categoryDefs: CategoryDef[] = [
  {
    key: 'fresh',
    label: '新鲜水果',
    categoryName: '水果生鲜',
    linear: assetUrl('/images/categories/linear/fruit.webp')
  },
  {
    key: 'grains',
    label: '粮油杂粮',
    categoryName: '粮油杂粮',
    linear: assetUrl('/images/categories/linear/grains.webp')
  },
  {
    key: 'food',
    label: '特色食品',
    categoryName: '特色食品',
    linear: assetUrl('/images/categories/linear/food.webp')
  },
  {
    key: 'culture',
    label: '甘味文创',
    categoryName: '文创礼品',
    linear: assetUrl('/images/categories/linear/culture.webp')
  },
  {
    key: 'points',
    label: '绿色积分',
    categoryName: '',
    linear: assetUrl('/images/categories/linear/points.webp'),
    to: '/account/points'
  }
]

const categories = ref<Category[]>([])
const categoryLoading = ref(true)
const categoryError = ref('')
const products = ref<Product[]>([])
const pagination = ref<Pagination>({ page: 1, page_size: 6, total: 0, total_pages: 0 })
const loading = ref(true)
const error = ref('')
const originMap = ref<Record<string, GreenDetail | null>>({})
const originLoading = ref(false)
const reviewPicks = ref<ReviewPick[]>([])
const reviewLoading = ref(true)
const reviewError = ref('')
const filters = reactive({
  keyword: '',
  category_id: '',
  store_id: '',
  sort: 'created_desc' as 'created_desc' | 'price_asc',
  page: 1
})

const displayCategories = computed<CategoryItem[]>(() =>
  categoryDefs.map((definition) => ({
    ...definition,
    category: categories.value.find((item) => item.name === definition.categoryName) || null
  }))
)
const activeDef = computed(
  () =>
    displayCategories.value.find((definition) => definition.category?.id === filters.category_id) ||
    null
)
const activeLabel = computed(() => activeDef.value?.label || '全部商品')
const originProducts = computed(() => products.value.slice(0, 5))

async function loadCategories(): Promise<void> {
  categoryLoading.value = true
  categoryError.value = ''
  try {
    categories.value = await catalogApi.categories()
  } catch (err) {
    categoryError.value = errorText(err)
  } finally {
    categoryLoading.value = false
  }
}

async function loadOrigins(items: Product[]): Promise<void> {
  if (!items.length) {
    originMap.value = {}
    originLoading.value = false
    return
  }
  originLoading.value = true
  const results = await Promise.allSettled(items.map((item) => greenApi.detail(item.id)))
  const map: Record<string, GreenDetail | null> = {}
  items.forEach((item, index) => {
    const result = results[index]
    map[item.id] = result?.status === 'fulfilled' ? result.value : null
  })
  originMap.value = map
  originLoading.value = false
}

/**
 * 【MOCK 数据】后端暂未提供评价接口：用商品 ID 的稳定哈希结合现有资料完整度生成 4.6–5.0 的演示评分，
 * 保证同一商品的评分与排序稳定可复现；页面已明确标注“Mock 演示”。
 * 后续接入评价数据时替换本函数，并移除 Mock 标记。
 */
function stableHash(text: string): number {
  let hash = 2166136261
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

function reviewScore(product: Product): number {
  let score = 4.6 + (stableHash(product.id || product.title) % 4) * 0.1
  if (product.aid_project_id) score += 0.04
  if (product.subtitle) score += 0.02
  if (product.cover_url) score += 0.02
  return Math.min(5, Math.round(score * 10) / 10)
}

function filledStars(score: number): number {
  return Math.round(score)
}

async function loadReviewPicks(): Promise<void> {
  reviewLoading.value = true
  reviewError.value = ''
  try {
    const data = await catalogApi.products({ sort: 'created_desc', page: 1, page_size: 12 })
    reviewPicks.value = data.items
      .map((product) => ({ product, score: reviewScore(product) }))
      .sort(
        (a, b) => b.score - a.score || a.product.title.localeCompare(b.product.title, 'zh-Hans-CN')
      )
      .slice(0, 4)
  } catch (err) {
    reviewError.value = errorText(err)
    reviewPicks.value = []
  } finally {
    reviewLoading.value = false
  }
}

async function loadProducts(): Promise<void> {
  loading.value = true
  error.value = ''
  originMap.value = {}
  try {
    const data = await catalogApi.products({
      category_id: filters.category_id || undefined,
      store_id: filters.store_id || undefined,
      keyword: filters.keyword || undefined,
      sort: filters.sort,
      page: filters.page,
      page_size: 6
    })
    products.value = data.items
    pagination.value = data.pagination
    void loadOrigins(data.items.slice(0, 5))
  } catch (err) {
    error.value = errorText(err)
    products.value = []
  } finally {
    loading.value = false
  }
}

function applyRoute(): void {
  filters.keyword = String(route.query.keyword || '')
  filters.category_id = String(route.query.category_id || '')
  filters.store_id = String(route.query.store_id || '')
  filters.sort = route.query.sort === 'price_asc' ? 'price_asc' : 'created_desc'
  filters.page = Math.max(1, Number(route.query.page) || 1)
  loadProducts()
}

function updateQuery(patch: Record<string, string | number | undefined>): void {
  const query: Record<string, string | number> = {}
  const current = { ...route.query, ...patch }
  Object.entries(current).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query[key] = value as string | number
  })
  router.push({ name: 'products', query })
}

function selectCategory(definition: CategoryItem): void {
  if (definition.to) {
    router.push(definition.to)
    return
  }
  if (categoryLoading.value) {
    toast.show('分类正在加载，请稍候', 'info')
    return
  }
  if (!definition.category) {
    toast.show('该分类暂未接入商品', 'warning')
    return
  }
  if (filters.category_id === definition.category.id) {
    updateQuery({ category_id: undefined, page: 1 })
    return
  }
  updateQuery({ category_id: definition.category.id, page: 1 })
}

function clearAll(): void {
  updateQuery({
    keyword: undefined,
    store_id: undefined,
    category_id: undefined,
    sort: undefined,
    page: 1
  })
}

function setSort(sort: 'created_desc' | 'price_asc'): void {
  updateQuery({ sort, page: 1 })
}

function pageTo(page: number): void {
  updateQuery({ page })
}

function originFor(product: Product): string {
  return originMap.value[product.id]?.profile?.origin || product.store_name || '甘肃产地'
}

function originImage(product: Product): string {
  return assetUrl(product.cover_url, productFallbackImage(product.title))
}

function originImageError(event: Event, product: Product): void {
  const img = event.target as HTMLImageElement
  const fallback = productFallbackImage(product.title)
  if (img.src.endsWith(fallback)) return
  img.src = fallback
}

watch(() => route.query, applyRoute, { immediate: true })
onMounted(() => {
  loadCategories()
  loadReviewPicks()
})
useRefreshOnFocus(() => {
  loadProducts()
})
</script>

<template>
  <main class="page-main catalog-page catalog-page-v2">
    <div class="page-container">
      <header class="catalog-title-row">
        <div>
          <span class="eyebrow">ALL PRODUCTS</span>
          <h1>全部商品</h1>
          <p>甘肃产地直供 · 绿色优选 · 按分类浏览</p>
        </div>
        <div class="catalog-title-meta">
          <span>共 {{ pagination.total }} 件商品</span>
          <span v-if="activeDef" class="active-filter-badge">{{ activeDef.label }}</span>
        </div>
      </header>

      <section class="catalog-category-panel" aria-label="商品分类导航">
        <div class="catalog-category-main">
          <div class="catalog-category-pills">
            <button
              v-for="category in displayCategories"
              :key="category.key"
              type="button"
              class="catalog-category-pill"
              :class="{
                active: activeDef?.key === category.key,
                disabled: !category.to && !category.category
              }"
              :disabled="!category.to && !category.category"
              :aria-pressed="activeDef?.key === category.key"
              @click="selectCategory(category)"
            >
              <span class="catalog-category-icon">
                <img :src="category.linear" :alt="category.label" loading="lazy" />
              </span>
              <span>{{ category.label }}</span>
              <AppIcon v-if="activeDef?.key === category.key" name="check" :size="13" />
            </button>
          </div>
          <p v-if="categoryLoading" class="category-panel-note">分类加载中…</p>
          <p v-else-if="categoryError" class="category-panel-note error">
            分类暂不可用，仍可浏览全部商品。
          </p>
        </div>

        <RouterLink to="/origin" class="catalog-category-card">
          <img
            :src="assetUrl('/images/banners/category-card.webp')"
            alt="甘肃梯田与产地风光"
            loading="lazy"
            decoding="async"
          />
          <span class="catalog-category-card-copy">
            <strong>甘肃产地</strong>
            <small>一县一品 · 溯源直达</small>
          </span>
          <span class="catalog-category-card-arrow">
            <AppIcon name="arrow-right" :size="16" />
          </span>
        </RouterLink>
      </section>

      <section
        v-if="!filters.keyword"
        class="featured-reviews"
        aria-labelledby="featured-reviews-title"
      >
        <header class="featured-reviews-head">
          <div>
            <span class="eyebrow">TOP RATED · MOCK</span>
            <h2 id="featured-reviews-title">精选好评推荐 <em class="mock-badge">Mock 演示</em></h2>
            <p>评价接口尚未接入；以下评分与排序为本地演示数据，不代表真实评价。</p>
          </div>
          <RouterLink to="/products" class="more-link">
            查看更多 <AppIcon name="chevron-right" :size="13" />
          </RouterLink>
        </header>

        <p v-if="reviewLoading" class="featured-review-state">
          <span class="mini-spinner dark" />正在挑选好评商品…
        </p>
        <p v-else-if="reviewError" class="featured-review-state">
          好评推荐暂不可用，不影响浏览全部商品。
        </p>
        <div v-else class="featured-review-grid">
          <RouterLink
            v-for="pick in reviewPicks"
            :key="pick.product.id"
            :to="`/products/${pick.product.id}`"
            class="featured-review-card"
          >
            <div class="featured-review-image">
              <img
                :src="originImage(pick.product)"
                :alt="pick.product.title"
                loading="lazy"
                decoding="async"
                @error="originImageError($event, pick.product)"
              />
              <span class="featured-review-badge">演示好评</span>
            </div>
            <div class="featured-review-body">
              <h3>{{ pick.product.title }}</h3>
              <div class="featured-review-rating" :aria-label="`评分 ${pick.score.toFixed(1)} 分`">
                <span class="rating-stars" aria-hidden="true">
                  <AppIcon
                    v-for="star in 5"
                    :key="star"
                    name="star"
                    :size="12"
                    :class="{ on: star <= filledStars(pick.score) }"
                  />
                </span>
                <strong>{{ pick.score.toFixed(1) }}</strong>
                <small>分</small>
              </div>
              <div class="featured-review-bottom">
                <span class="product-price"
                  ><small>¥</small>{{ money(pick.product.min_price) }}</span
                >
                <span class="featured-review-link">
                  查看详情 <AppIcon name="chevron-right" :size="12" />
                </span>
              </div>
            </div>
          </RouterLink>
        </div>
      </section>

      <div class="catalog-body">
        <aside class="origin-panel">
          <header class="origin-panel-head">
            <div>
              <span class="eyebrow">GANSU ORIGIN</span>
              <h2>甘肃产地</h2>
            </div>
            <RouterLink to="/origin" class="more-link">
              更多 <AppIcon name="chevron-right" :size="13" />
            </RouterLink>
          </header>

          <p v-if="originLoading && !loading" class="origin-loading">
            <span class="mini-spinner dark" />产地信息读取中…
          </p>

          <StateBlock
            :loading="loading && !originProducts.length"
            :error="error"
            :empty="!loading && !error && !originProducts.length"
            empty-text="暂无产地商品"
            compact
            @retry="loadProducts"
          >
            <template #empty-action>
              <button type="button" class="outline-button small" @click="clearAll">
                查看全部商品
              </button>
            </template>
            <ul class="origin-list">
              <li v-for="product in originProducts" :key="product.id" class="origin-item">
                <RouterLink :to="`/products/${product.id}`" class="origin-thumb">
                  <img
                    :src="originImage(product)"
                    :alt="product.title"
                    loading="lazy"
                    decoding="async"
                    @error="originImageError($event, product)"
                  />
                </RouterLink>
                <div class="origin-item-copy">
                  <span class="origin-name">
                    <AppIcon name="location" :size="12" />{{ originFor(product) }}
                  </span>
                  <h3>
                    <RouterLink :to="`/products/${product.id}`">{{ product.title }}</RouterLink>
                  </h3>
                  <p>{{ product.subtitle || '甘肃产地好物' }}</p>
                </div>
                <RouterLink :to="`/products/${product.id}`" class="origin-detail-button">
                  查看详情 <AppIcon name="chevron-right" :size="12" />
                </RouterLink>
              </li>
            </ul>
          </StateBlock>
        </aside>

        <section class="catalog-results">
          <header class="catalog-results-head">
            <div>
              <span class="eyebrow">PRODUCTS</span>
              <h2>{{ activeLabel }}</h2>
            </div>
            <div class="catalog-result-tools">
              <span class="result-count">共 {{ pagination.total }} 件</span>
              <div class="sort-tabs" aria-label="商品排序">
                <button
                  type="button"
                  :class="{ active: filters.sort === 'created_desc' }"
                  @click="setSort('created_desc')"
                >
                  综合排序
                </button>
                <button type="button" disabled title="后端暂未提供销量排序字段">销量优先</button>
                <button
                  type="button"
                  :class="{ active: filters.sort === 'price_asc' }"
                  @click="setSort('price_asc')"
                >
                  价格优先
                </button>
              </div>
            </div>
          </header>

          <div
            v-if="filters.keyword || filters.store_id || filters.category_id"
            class="result-keyword"
          >
            <span v-if="filters.keyword">“{{ filters.keyword }}” 的搜索结果</span>
            <span v-else-if="filters.store_id">指定店铺商品</span>
            <span v-else>已筛选：{{ activeLabel }}</span>
            <button type="button" @click="clearAll">清除筛选</button>
          </div>

          <StateBlock
            :loading="loading"
            :error="error"
            :empty="!loading && !error && !products.length"
            empty-text="没有找到符合条件的商品"
            @retry="loadProducts"
          >
            <template #empty-action>
              <button type="button" class="outline-button small" @click="clearAll">
                查看全部商品
              </button>
            </template>
            <div class="product-grid catalog-product-grid-v2">
              <ProductCard
                v-for="product in products"
                :key="product.id"
                :product="product"
                variant="catalog"
              />
            </div>
          </StateBlock>

          <PaginationBar v-if="!loading && !error" :pagination="pagination" @change="pageTo" />
        </section>
      </div>
    </div>
  </main>
</template>
