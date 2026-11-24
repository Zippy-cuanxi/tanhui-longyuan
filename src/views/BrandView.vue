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

async function loadProducts(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const data = await catalogApi.products({ page: 1, page_size: 4 })
    products.value = data.items
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(loadProducts)
</script>

<template>
  <main class="page-main brand-page">
    <div class="page-container">
      <BannerSection
        :config="{
          title: '品牌故事',
          image_url: '/assets/banners/brand-story.webp',
          link_url: '/brand'
        }"
        variant="page"
        fallback-image="/assets/banners/brand-story.webp"
      />

      <section class="page-intro centered">
        <span class="eyebrow">OUR STORY</span>
        <h1>从陇原大地，到万家餐桌</h1>
        <p>碳惠陇原连接甘肃产地与消费者，让绿色生态、品质优选与助农增收在同一份订单里相遇。</p>
      </section>

      <section class="brand-story-grid">
        <article>
          <img src="/assets/banners/aid-card-farm.webp" alt="甘肃产地合作社" />
          <div>
            <span class="eyebrow">ORIGIN</span>
            <h2>一方水土，孕育自然好物</h2>
            <p>
              甘肃的梯田、河谷与绿洲，孕育了苹果、马铃薯、蜜瓜、枸杞、百合等各具风味的农特产品。平台以产地为线索组织商品，让消费者看见好物从哪里来。
            </p>
          </div>
        </article>
        <article>
          <img src="/assets/banners/green-card.webp" alt="绿色消费专区" />
          <div>
            <span class="eyebrow">GREEN</span>
            <h2>绿色资料，让选择更透明</h2>
            <p>
              商家可提交产地、种植方式与绿色资料，经平台审核后展示。未核验的碳评估数据会明确标记“未核验”，不冒充已核验结论。
            </p>
          </div>
        </article>
        <article>
          <img src="/assets/banners/aid-card-farmer.webp" alt="助农项目" />
          <div>
            <span class="eyebrow">RURAL REVITALIZATION</span>
            <h2>每一份订单，都是一份助农力量</h2>
            <p>
              平台通过助农项目连接合作社与消费者。当前项目与金额均为演示数据，真实资金流与公示口径待业务确认。
            </p>
          </div>
        </article>
      </section>

      <section class="brand-values">
        <div>
          <span><AppIcon name="leaf" :size="22" /></span>
          <h3>绿色生态</h3>
          <p>关注产地环境与种植方式，绿色资料可查。</p>
        </div>
        <div>
          <span><AppIcon name="shield" :size="22" /></span>
          <h3>品质优选</h3>
          <p>商品经平台审核后上架，交易价格与库存由服务端校验。</p>
        </div>
        <div>
          <span><AppIcon name="heart" :size="22" /></span>
          <h3>助农增收</h3>
          <p>连接产地合作社，让好物被更多人看见。</p>
        </div>
      </section>

      <section class="section-block">
        <header class="section-heading">
          <h2>陇原好物</h2>
          <RouterLink to="/products" class="more-link"
            >全部商品 <AppIcon name="chevron-right" :size="14"
          /></RouterLink>
        </header>
        <StateBlock
          :loading="loading"
          :error="error"
          :empty="!loading && !error && !products.length"
          empty-text="暂无品牌好物"
          @retry="loadProducts"
        >
          <div class="product-grid columns-4">
            <ProductCard v-for="product in products" :key="product.id" :product="product" />
          </div>
        </StateBlock>
      </section>

      <section class="brand-cta">
        <div>
          <span class="eyebrow">EXPLORE</span>
          <h2>去看看陇原好物</h2>
          <p>从产地地图出发，挑选一件来自甘肃的自然好物。</p>
        </div>
        <div class="brand-cta-actions">
          <RouterLink to="/products" class="primary-button">全部商品</RouterLink>
          <RouterLink to="/origin" class="outline-button">甘肃产地</RouterLink>
        </div>
      </section>
    </div>
  </main>
</template>
