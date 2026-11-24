<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { aidApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { AidProject } from '@/api/types'
import { errorText, money, percent } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import BannerSection from '@/components/sections/BannerSection.vue'
import StateBlock from '@/components/StateBlock.vue'

const projects = ref<AidProject[]>([])
const loading = ref(true)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const data = await aidApi.list({ page: 1, page_size: 12 })
    projects.value = data.items
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-main aid-page">
    <div class="page-container">
      <BannerSection
        :config="{
          title: '助农项目',
          image_url: '/assets/banners/aid-project.webp',
          link_url: '/aid'
        }"
        variant="page"
        fallback-image="/assets/banners/aid-project.webp"
      />

      <section class="page-intro">
        <span class="eyebrow">RURAL REVITALIZATION</span>
        <h1>每一份订单，都是一份助农力量</h1>
        <p>
          平台连接甘肃合作社与消费者，展示助农项目的目标与进展。当前项目、金额与进度均为演示数据。
        </p>
      </section>

      <StateBlock
        :loading="loading"
        :error="error"
        :empty="!loading && !error && !projects.length"
        empty-text="暂无已发布的助农项目"
        @retry="load"
      >
        <div class="aid-grid">
          <article v-for="project in projects" :key="project.id" class="aid-card">
            <RouterLink :to="`/aid/${project.id}`" class="aid-card-image">
              <img
                :src="assetUrl(project.cover_url, '/assets/banners/aid-project.webp')"
                :alt="project.title"
              />
              <span class="aid-card-badge"><AppIcon name="heart" :size="13" />助农项目</span>
            </RouterLink>
            <div class="aid-card-body">
              <span class="eyebrow">AID PROJECT</span>
              <h2>
                <RouterLink :to="`/aid/${project.id}`">{{ project.title }}</RouterLink>
              </h2>
              <p>{{ project.description || '项目说明待补充。' }}</p>
              <div class="aid-progress">
                <div class="aid-progress-bar">
                  <span
                    :style="{ width: `${percent(project.raised_amount, project.goal_amount)}%` }"
                  />
                </div>
                <div class="aid-progress-meta">
                  <strong>已筹 ¥{{ money(project.raised_amount) }}</strong>
                  <span v-if="project.goal_amount"
                    >目标 ¥{{ money(project.goal_amount) }} ·
                    {{ percent(project.raised_amount, project.goal_amount) }}%</span
                  >
                </div>
              </div>
              <RouterLink :to="`/aid/${project.id}`" class="outline-button small">
                查看项目 <AppIcon name="arrow-right" :size="14" />
              </RouterLink>
            </div>
          </article>
        </div>
      </StateBlock>

      <p class="page-note">
        <AppIcon name="info" :size="15" />
        助农项目与金额为演示数据，不构成真实募捐或资金承诺；真实资金流与公示规则待业务确认。
      </p>
    </div>
  </main>
</template>
