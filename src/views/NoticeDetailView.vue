<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { cmsApi } from '@/api'
import type { Notice } from '@/api/types'
import { errorText, formatDateTime } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const noticeId = computed(() => String(route.params.id))
const notice = ref<Notice | null>(null)
const loading = ref(true)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const list = await cmsApi.notices()
    notice.value = list.find((item) => item.id === noticeId.value) || null
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-main notice-detail-page">
    <div class="page-container narrow-container">
      <RouterLink to="/notices" class="back-link">
        <AppIcon name="chevron-left" :size="15" />返回公告列表
      </RouterLink>

      <StateBlock v-if="loading" :loading="true" />
      <StateBlock v-else-if="error" :error="error" @retry="load" />
      <StateBlock v-else-if="!notice" :empty="true" empty-text="公告不存在或已下线">
        <template #empty-action>
          <RouterLink to="/notices" class="outline-button small">查看全部公告</RouterLink>
        </template>
      </StateBlock>

      <article v-else class="notice-detail">
        <span class="eyebrow">ANNOUNCEMENT</span>
        <h1>{{ notice.title }}</h1>
        <p class="notice-date">发布于 {{ formatDateTime(notice.published_at) }}</p>
        <div class="notice-body">{{ notice.content }}</div>
        <RouterLink to="/notices" class="outline-button small">返回公告列表</RouterLink>
      </article>
    </div>
  </main>
</template>
