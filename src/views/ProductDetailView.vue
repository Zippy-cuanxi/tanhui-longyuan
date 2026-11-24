<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { aidApi, catalogApi, greenApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { AidProject, GreenDetail, Product, ProductDetail, Sku } from '@/api/types'
import { errorText, money, productFallbackGallery, productFallbackImage } from '@/utils/format'
import { dishInfoForProduct } from '@/utils/productMedia'
import { productExtraInfoFor } from '@/utils/productInfo'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { useCheckoutStore } from '@/stores/checkout'
import AppIcon from '@/components/AppIcon.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import QuantityStepper from '@/components/QuantityStepper.vue'
import SkuSelector from '@/components/SkuSelector.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const cart = useCartStore()
const checkout = useCheckoutStore()

const product = ref<ProductDetail | null>(null)
const recipe = computed(() => dishInfoForProduct(product.value?.title))
const extraInfo = computed(() => productExtraInfoFor(product.value?.title))
const green = ref<GreenDetail | null>(null)
const aidProject = ref<AidProject | null>(null)
const related = ref<Product[]>([])
const selectedSku = ref<Sku | null>(null)
const quantity = ref(1)
const activeImage = ref(0)
const tab = ref<'detail' | 'specs' | 'green'>('detail')
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const adding = ref(false)

const fallbackGallery = computed(() => productFallbackGallery(product.value?.title))
const images = computed(() => {
  const list = (product.value?.images || [])
    .slice()
    .sort((a, b) => a.sort - b.sort)
    .map((image) => assetUrl(image.url))
  return list.length ? list : fallbackGallery.value
})
const price = computed(() => selectedSku.value?.price || product.value?.min_price || null)
const greenOrigin = computed(() => green.value?.profile?.origin || '甘肃')
const carbon = computed(() => green.value?.carbon_assessment || null)
const hasGreen = computed(() => green.value?.profile?.status === 'approved')

function requireLogin(): boolean {
  if (auth.isAuthenticated) return true
  router.push({ name: 'login', query: { redirect: route.fullPath } })
  return false
}

function imageFallback(event: Event): void {
  const img = event.target as HTMLImageElement
  const fallback = fallbackGallery.value[activeImage.value] || fallbackGallery.value[0]
  if (img.src.endsWith(fallback)) return
  img.src = fallback
}

function selectSku(sku: Sku): void {
  selectedSku.value = sku
  quantity.value = 1
}

async function addToCart(): Promise<void> {
  if (!selectedSku.value || !requireLogin()) return
  adding.value = true
  actionError.value = ''
  try {
    await cart.add(selectedSku.value.id, quantity.value)
  } catch (err) {
    actionError.value = errorText(err)
  } finally {
    adding.value = false
  }
}

function buyNow(): void {
  if (!selectedSku.value || !requireLogin()) return
  checkout.setDirect([
    {
      sku_id: selectedSku.value.id,
      quantity: quantity.value,
      expected_unit_price: selectedSku.value.price,
      title: product.value?.title,
      image_url: images.value[0],
      spec: selectedSku.value.spec,
      price: selectedSku.value.price
    }
  ])
  router.push({ name: 'checkout' })
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  actionError.value = ''
  product.value = null
  green.value = null
  aidProject.value = null
  related.value = []
  try {
    const detail = await catalogApi.product(String(route.params.id))
    product.value = detail
    selectedSku.value = detail.skus?.find((sku) => sku.is_active) || null
    activeImage.value = 0
    tab.value = 'detail'

    const [greenResult, relatedResult] = await Promise.allSettled([
      greenApi.detail(detail.id),
      catalogApi.products({ store_id: detail.store_id, page: 1, page_size: 8 })
    ])
    if (greenResult.status === 'fulfilled') green.value = greenResult.value
    if (relatedResult.status === 'fulfilled') {
      related.value = relatedResult.value.items.filter((item) => item.id !== detail.id).slice(0, 6)
    }
    if (detail.aid_project_id) {
      aidApi
        .detail(detail.aid_project_id)
        .then((project) => {
          aidProject.value = project
        })
        .catch(() => {
          aidProject.value = null
        })
    }
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, load, { immediate: true })
</script>

<template>
  <main class="page-main detail-page">
    <div class="page-container">
      <Breadcrumbs
        :items="[
          { label: '首页', to: '/' },
          { label: '全部商品', to: '/products' },
          { label: product?.title || '商品详情' }
        ]"
      />

      <StateBlock v-if="loading" :loading="true" />
      <StateBlock v-else-if="error" :error="error" @retry="load" />

      <template v-else-if="product">
        <div class="detail-layout">
          <section class="gallery-panel">
            <div class="main-product-image">
              <img
                :src="images[activeImage]"
                :alt="product.title"
                loading="eager"
                decoding="async"
                @error="imageFallback"
              />
              <span class="gallery-corner"><AppIcon name="leaf" :size="13" /> 产地直供</span>
            </div>
            <div v-if="images.length > 1" class="thumbnail-list">
              <button
                v-for="(image, index) in images"
                :key="image"
                type="button"
                :class="{ active: activeImage === index }"
                :aria-label="`查看${product.title}图片${index + 1}`"
                @click="activeImage = index"
              >
                <img
                  :src="image"
                  :alt="`${product.title}图片${index + 1}`"
                  loading="lazy"
                  decoding="async"
                />
              </button>
            </div>
          </section>

          <section class="product-info-panel">
            <div class="detail-title-row">
              <div>
                <span class="eyebrow">GANSU ORIGINAL</span>
                <h1>{{ product.title }}</h1>
              </div>
              <span class="verified-mark" title="商品已通过平台审核">
                <AppIcon name="check" :size="17" />
              </span>
            </div>
            <p class="detail-subtitle">
              {{ product.subtitle || product.store_name || '甘肃产地好物' }}
            </p>

            <div class="detail-price-row">
              <span class="detail-price"
                ><small>¥</small><strong>{{ money(price) }}</strong></span
              >
              <span v-if="hasGreen" class="green-pill"
                ><AppIcon name="leaf" :size="13" /> 绿色资料已审核</span
              >
              <span v-if="product.aid_project_id" class="aid-pill">助农好物</span>
            </div>

            <div class="detail-tag-row">
              <span>产地直供</span>
              <span>平台审核通过</span>
              <span v-if="hasGreen">{{ greenOrigin }}</span>
              <span>售后以平台规则为准</span>
            </div>

            <dl class="product-meta">
              <div>
                <dt>店铺</dt>
                <dd>{{ product.store_name || '—' }}</dd>
              </div>
              <div>
                <dt>产地</dt>
                <dd>{{ greenOrigin }}</dd>
              </div>
              <div>
                <dt>规格</dt>
                <dd>
                  {{
                    selectedSku?.spec ||
                    `${product.skus.filter((sku) => sku.is_active).length} 种可选规格`
                  }}
                </dd>
              </div>
              <div v-if="aidProject">
                <dt>助农项目</dt>
                <dd>
                  <RouterLink :to="`/aid/${aidProject.id}`" class="text-link"
                    >{{ aidProject.title }} <AppIcon name="chevron-right" :size="12"
                  /></RouterLink>
                </dd>
              </div>
            </dl>

            <div class="detail-rule" />

            <div class="sku-section">
              <h2>选择规格</h2>
              <SkuSelector
                :skus="product.skus"
                :model-value="selectedSku"
                @update:model-value="selectSku"
              />
            </div>

            <div class="quantity-section">
              <h2>购买数量</h2>
              <QuantityStepper v-model="quantity" :max="999" />
              <span>价格、库存与运费以下单时服务端校验为准</span>
            </div>

            <p v-if="actionError" class="inline-error">{{ actionError }}</p>

            <div class="detail-actions">
              <button
                class="outline-button"
                type="button"
                :disabled="!selectedSku || adding"
                @click="addToCart"
              >
                <span v-if="adding" class="mini-spinner dark" />
                <AppIcon v-else name="cart" :size="18" />
                {{ adding ? '加入中…' : '加入购物车' }}
              </button>
              <button class="primary-button" type="button" :disabled="!selectedSku" @click="buyNow">
                <AppIcon name="sparkle" :size="18" />
                立即购买
              </button>
            </div>

            <div class="detail-assurance">
              <span><AppIcon name="shield" :size="15" /> 平台审核商品</span>
              <span><AppIcon name="truck" :size="15" /> 产地仓发货</span>
              <span><AppIcon name="leaf" :size="15" /> 绿色资料可查</span>
            </div>
          </section>

          <aside class="origin-related-panel">
            <header class="section-heading">
              <h2><AppIcon name="map" :size="18" /> 甘肃产地地图</h2>
              <RouterLink
                :to="{ name: 'products', query: { store_id: product.store_id } }"
                class="more-link"
              >
                更多 <AppIcon name="chevron-right" :size="13" />
              </RouterLink>
            </header>
            <div v-if="related.length" class="related-list">
              <RouterLink
                v-for="item in related"
                :key="item.id"
                :to="`/products/${item.id}`"
                class="related-item"
              >
                <img
                  :src="assetUrl(item.cover_url, productFallbackImage(item.title))"
                  :alt="item.title"
                  loading="lazy"
                  decoding="async"
                />
                <div>
                  <span>{{ item.store_name }}</span>
                  <strong>{{ item.title }}</strong>
                  <small>¥{{ money(item.min_price) }}</small>
                </div>
                <span class="related-link"
                  >查看商品 <AppIcon name="chevron-right" :size="11"
                /></span>
              </RouterLink>
            </div>
            <div v-else class="store-card">
              <img
                :src="images[0]"
                :alt="product.store_name || product.title"
                loading="lazy"
                decoding="async"
              />
              <span>{{ product.store_name }}</span>
              <strong>甘肃产地直供</strong>
              <RouterLink
                :to="{ name: 'products', query: { store_id: product.store_id } }"
                class="outline-button small"
              >
                进入店铺
              </RouterLink>
            </div>
          </aside>
        </div>

        <section class="detail-content">
          <div class="detail-tabs" role="tablist" aria-label="商品信息">
            <button
              type="button"
              role="tab"
              :aria-selected="tab === 'detail'"
              :class="{ active: tab === 'detail' }"
              @click="tab = 'detail'"
            >
              商品详情
            </button>
            <button
              type="button"
              role="tab"
              :aria-selected="tab === 'specs'"
              :class="{ active: tab === 'specs' }"
              @click="tab = 'specs'"
            >
              规格参数
            </button>
            <button
              v-if="hasGreen"
              type="button"
              role="tab"
              :aria-selected="tab === 'green'"
              :class="{ active: tab === 'green' }"
              @click="tab = 'green'"
            >
              绿色资料
            </button>
          </div>

          <div v-if="tab === 'detail'" class="detail-tab-body">
            <p class="detail-description">{{ product.description || '商家暂未提供商品描述。' }}</p>
            <div v-if="extraInfo" class="product-info-grid">
              <section class="product-info-card">
                <h3>规格参数</h3>
                <dl class="product-info-list">
                  <div v-for="spec in extraInfo.specs" :key="spec.label">
                    <dt>{{ spec.label }}</dt>
                    <dd>{{ spec.value }}</dd>
                  </div>
                  <div>
                    <dt>可选规格</dt>
                    <dd>{{ product.skus.map((sku) => sku.spec).join('、') }}</dd>
                  </div>
                </dl>
              </section>
              <section class="product-info-card">
                <h3>产品特点</h3>
                <ul>
                  <li v-for="item in extraInfo.features" :key="item">{{ item }}</li>
                </ul>
              </section>
              <section class="product-info-card">
                <h3>使用说明</h3>
                <ul>
                  <li v-for="item in extraInfo.usage" :key="item">{{ item }}</li>
                </ul>
              </section>
              <section class="product-info-card">
                <h3>注意事项</h3>
                <ul>
                  <li v-for="item in extraInfo.precautions" :key="item">{{ item }}</li>
                </ul>
              </section>
            </div>
            <div class="detail-visual-row">
              <img
                v-for="(image, index) in images.slice(0, 3)"
                :key="image"
                :src="image"
                :alt="`${product.title}详情图${index + 1}`"
                loading="lazy"
                decoding="async"
              />
            </div>
          </div>

          <div v-else-if="tab === 'specs'" class="detail-tab-body">
            <table class="spec-table">
              <tbody>
                <tr>
                  <th>商品名称</th>
                  <td>{{ product.title }}</td>
                </tr>
                <tr>
                  <th>店铺</th>
                  <td>{{ product.store_name || '—' }}</td>
                </tr>
                <tr>
                  <th>产地</th>
                  <td>{{ greenOrigin }}</td>
                </tr>
                <tr
                  v-for="spec in (extraInfo?.specs || []).filter((item) => item.label !== '产地')"
                  :key="spec.label"
                >
                  <th>{{ spec.label }}</th>
                  <td>{{ spec.value }}</td>
                </tr>
                <tr>
                  <th>币种</th>
                  <td>CNY</td>
                </tr>
                <tr>
                  <th>商品状态</th>
                  <td>{{ product.status === 'approved' ? '平台审核通过' : product.status }}</td>
                </tr>
              </tbody>
            </table>
            <table class="spec-table">
              <thead>
                <tr>
                  <th>规格</th>
                  <th>价格</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="sku in product.skus" :key="sku.id">
                  <td>{{ sku.spec }}</td>
                  <td>¥{{ money(sku.price) }}</td>
                  <td>{{ sku.is_active ? '可售' : '已停用' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else class="detail-tab-body green-profile-card">
            <div class="green-profile-head">
              <span class="cms-points-icon"><AppIcon name="leaf" :size="22" /></span>
              <div>
                <h3>绿色资料</h3>
                <p>资料由商家提交、平台审核；未核验的碳数据不会展示为已核验。</p>
              </div>
            </div>
            <dl class="product-meta">
              <div>
                <dt>产地</dt>
                <dd>{{ green?.profile?.origin || '—' }}</dd>
              </div>
              <div>
                <dt>种植方式</dt>
                <dd>{{ green?.profile?.planting_mode || '—' }}</dd>
              </div>
              <div>
                <dt>资料状态</dt>
                <dd>
                  {{
                    green?.profile?.status === 'approved' ? '已审核' : green?.profile?.status || '—'
                  }}
                </dd>
              </div>
            </dl>
            <p class="detail-description">
              {{ green?.profile?.description || '暂无绿色资料说明。' }}
            </p>
            <div v-if="carbon" class="carbon-box">
              <div>
                <span class="eyebrow">CARBON ASSESSMENT</span>
                <strong>{{ carbon.co2e_per_unit }} kg CO₂e / {{ carbon.unit }}</strong>
                <p>{{ carbon.methodology || '碳评估方法以平台记录为准。' }}</p>
              </div>
              <span class="status-tag" :class="carbon.verified ? 'tone-success' : 'tone-warning'">
                {{ carbon.verified ? '已核验' : '未核验' }}
              </span>
            </div>
            <p v-else class="muted-text">该商品暂无碳评估数据。</p>
          </div>
        </section>

        <section v-if="recipe" class="recipe-section">
          <div class="recipe-copy">
            <span class="eyebrow">SERVING IDEA</span>
            <h2>推荐吃法</h2>
            <h3>{{ recipe.name }}</h3>
            <p>{{ recipe.description }}</p>
            <span class="recipe-note">菜品示意图 · 实际烹饪以个人口味为准</span>
          </div>
          <div class="recipe-image">
            <img :src="recipe.image" :alt="`${recipe.name}菜品示意图`" loading="lazy" />
          </div>
        </section>
      </template>
    </div>
  </main>
</template>
