<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { cmsApi } from '@/api'
import type { Notice } from '@/api/types'
import { errorText, formatDateTime } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import StateBlock from '@/components/StateBlock.vue'

const notices = ref<Notice[]>([])
const loading = ref(true)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    notices.value = await cmsApi.notices()
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-main notices-page">
    <div class="page-container narrow-container">
      <section class="page-intro">
        <span class="eyebrow">ANNOUNCEMENTS</span>
        <h1>平台公告</h1>
        <p>平台运营、交易与活动公告由 CMS 发布，当前为演示环境。</p>
      </section>

      <StateBlock
        :loading="loading"
        :error="error"
        :empty="!loading && !error && !notices.length"
        empty-text="暂无公告"
        @retry="load"
      >
        <ul class="notice-list">
          <li v-for="notice in notices" :key="notice.id">
            <RouterLink :to="`/notices/${notice.id}`" class="notice-card">
              <span class="notice-icon"><AppIcon name="bell" :size="20" /></span>
              <div>
                <h2>{{ notice.title }}</h2>
                <p>{{ notice.content }}</p>
                <small>{{ formatDateTime(notice.published_at) }}</small>
              </div>
              <AppIcon name="chevron-right" :size="16" />
            </RouterLink>
          </li>
        </ul>
      </StateBlock>
    </div>
  </main>
</template>
