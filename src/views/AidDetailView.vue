<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { aidApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { AidProject } from '@/api/types'
import { errorText, formatDate, money, percent } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const projectId = computed(() => String(route.params.id))
const project = ref<AidProject | null>(null)
const loading = ref(true)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    project.value = await aidApi.detail(projectId.value)
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-main aid-detail-page">
    <div class="page-container narrow-container">
      <StateBlock v-if="loading" :loading="true" />
      <StateBlock v-else-if="error" :error="error" @retry="load" />

      <template v-else-if="project">
        <RouterLink to="/aid" class="back-link">
          <AppIcon name="chevron-left" :size="15" />返回助农项目
        </RouterLink>

        <section class="aid-detail-hero">
          <img
            :src="assetUrl(project.cover_url, '/assets/banners/aid-project.webp')"
            :alt="project.title"
          />
          <div class="aid-detail-copy">
            <span class="eyebrow">AID PROJECT</span>
            <h1>{{ project.title }}</h1>
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
            <dl class="aid-detail-meta">
              <div>
                <dt>项目状态</dt>
                <dd>{{ project.status === 'published' ? '已发布' : project.status }}</dd>
              </div>
              <div>
                <dt>发布时间</dt>
                <dd>{{ formatDate(project.published_at) }}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section class="aid-detail-body">
          <h2>项目说明</h2>
          <p>{{ project.description || '项目说明待补充。' }}</p>
          <h2>参与方式</h2>
          <p>
            当前版本仅展示助农项目信息，未开放真实捐赠或资金募集。消费者可通过购买助农商品支持产地合作社。
          </p>
          <div class="aid-detail-actions">
            <RouterLink to="/products" class="primary-button">选购助农商品</RouterLink>
            <RouterLink to="/aid" class="outline-button">查看其他项目</RouterLink>
          </div>
          <p class="page-note">
            <AppIcon name="info" :size="15" />
            项目与金额为演示数据，不构成真实募捐或资金承诺。
          </p>
        </section>
      </template>
    </div>
  </main>
</template>
