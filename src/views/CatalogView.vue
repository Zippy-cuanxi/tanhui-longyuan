<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogApi } from '@/api'
import type { Category, Pagination, Product } from '@/api/types'
import { DESIGN_CATEGORY_ORDER, categoryIcon, errorText } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import BannerSection from '@/components/sections/BannerSection.vue'
import ProductCard from '@/components/ProductCard.vue'
import StateBlock from '@/components/StateBlock.vue'
import PaginationBar from '@/components/PaginationBar.vue'

const route = useRoute()
const router = useRouter()
const categories = ref<Category[]>([])
const products = ref<Product[]>([])
const pagination = ref<Pagination>({ page: 1, page_size: 6, total: 0, total_pages: 0 })
const loading = ref(true)
const error = ref('')
const categoryLoading = ref(true)
const filters = reactive({
  keyword: '',
  category_id: '',
  store_id: '',
  sort: 'created_desc' as 'created_desc' | 'price_asc',
  page: 1
})

const designCategories = computed(() =>
  DESIGN_CATEGORY_ORDER.map((name) => categories.value.find((category) => category.name === name))
    .filter((category): category is Category => Boolean(category))
    .map((category) => ({ ...category, icon: categoryIcon(category.name) }))
)
const activeCategoryName = computed(
  () => categories.value.find((category) => category.id === filters.category_id)?.name || ''
)

async function loadCategories(): Promise<void> {
  categoryLoading.value = true
  try {
    categories.value = await catalogApi.categories()
  } catch {
    categories.value = []
  } finally {
    categoryLoading.value = false
  }
}

async function loadProducts(): Promise<void> {
  loading.value = true
  error.value = ''
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

function clearKeyword(): void {
  updateQuery({ keyword: undefined, page: 1 })
}

function pageTo(page: number): void {
  updateQuery({ page })
}

watch(() => route.query, applyRoute, { immediate: true })
loadCategories()
</script>

<template>
  <main class="page-main catalog-page">
    <div class="page-container">
      <BannerSection
        :config="{
          title: '甘肃好物 绿色优选',
          image_url: '/assets/banners/catalog-hero.webp',
          link_url: '/products'
        }"
        variant="page"
        fallback-image="/assets/banners/catalog-hero.webp"
      />

      <div class="catalog-toolbar">
        <div class="catalog-toolbar-left">
          <button
            type="button"
            class="all-category-button"
            :class="{ active: !filters.category_id }"
            @click="updateQuery({ category_id: undefined, page: 1 })"
          >
            <AppIcon name="grid" :size="17" />
            全部分类
          </button>
          <span v-if="activeCategoryName" class="current-filter">{{ activeCategoryName }}</span>
        </div>
        <div class="sort-tabs" aria-label="商品排序">
          <button
            type="button"
            :class="{ active: filters.sort === 'created_desc' }"
            @click="updateQuery({ sort: 'created_desc', page: 1 })"
          >
            综合排序
          </button>
          <button type="button" disabled title="后端暂未提供销量排序字段">销量优先</button>
          <button
            type="button"
            :class="{ active: filters.sort === 'price_asc' }"
            @click="updateQuery({ sort: 'price_asc', page: 1 })"
          >
            价格优先
          </button>
        </div>
      </div>

      <div class="catalog-layout">
        <aside class="category-sidebar" aria-label="商品分类">
          <button
            type="button"
            :class="{ active: !filters.category_id }"
            @click="updateQuery({ category_id: undefined, page: 1 })"
          >
            <span class="sidebar-icon"><AppIcon name="grid" :size="17" /></span>
            <span>全部品类</span>
            <AppIcon name="chevron-right" :size="13" class="sidebar-chevron" />
          </button>
          <button
            v-for="category in designCategories"
            :key="category.id"
            type="button"
            :class="{ active: filters.category_id === category.id }"
            @click="updateQuery({ category_id: category.id, page: 1 })"
          >
            <span class="sidebar-icon"><img :src="category.icon" :alt="category.name" /></span>
            <span>{{ category.name }}</span>
            <AppIcon name="chevron-right" :size="13" class="sidebar-chevron" />
          </button>
          <p v-if="categoryLoading" class="category-loading">分类读取中…</p>
        </aside>

        <section class="catalog-results" aria-label="商品列表">
          <div v-if="filters.keyword || filters.store_id" class="result-keyword">
            <span v-if="filters.keyword">“{{ filters.keyword }}” 的搜索结果</span>
            <span v-else>指定店铺商品</span>
            <button v-if="filters.keyword" type="button" @click="clearKeyword">清除搜索</button>
            <button v-else type="button" @click="updateQuery({ store_id: undefined, page: 1 })">
              查看全部
            </button>
          </div>

          <StateBlock
            :loading="loading"
            :error="error"
            :empty="!loading && !error && !products.length"
            empty-text="没有找到符合条件的商品"
            @retry="loadProducts"
          >
            <template #empty-action>
              <RouterLink to="/products" class="outline-button small">查看全部商品</RouterLink>
            </template>
          </StateBlock>

          <div v-if="!loading && !error && products.length" class="product-grid columns-3">
            <ProductCard v-for="product in products" :key="product.id" :product="product" />
          </div>

          <PaginationBar v-if="!loading && !error" :pagination="pagination" @change="pageTo" />
        </section>
      </div>
    </div>
  </main>
</template>
