<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { aidApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { AidProject } from '@/api/types'
import { asString } from '@/utils/cms'
import { errorText, money, percent } from '@/utils/format'
import AppIcon from '../AppIcon.vue'

const props = defineProps<{ config: Record<string, unknown> }>()
const projectId = asString(props.config.project_id, '')
const project = ref<AidProject | null>(null)
const loading = ref(true)
const error = ref('')

async function load(): Promise<void> {
  if (!projectId) {
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    project.value = await aidApi.detail(projectId)
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-if="loading || project" class="cms-aid-card">
    <img
      :src="assetUrl(project?.cover_url, '/assets/banners/aid-project.webp')"
      :alt="project?.title || '助农项目'"
    />
    <div class="cms-aid-copy">
      <span class="eyebrow">RURAL REVITALIZATION</span>
      <h2>{{ project?.title || '助农项目' }}</h2>
      <p>{{ project?.description || '正在加载助农项目…' }}</p>
      <div v-if="project" class="aid-progress">
        <div class="aid-progress-bar">
          <span :style="{ width: `${percent(project.raised_amount, project.goal_amount)}%` }" />
        </div>
        <p>
          已筹 ¥{{ money(project.raised_amount) }}
          <span v-if="project.goal_amount">/ 目标 ¥{{ money(project.goal_amount) }}</span>
        </p>
      </div>
      <RouterLink v-if="project" :to="`/aid/${project.id}`" class="outline-button">
        了解项目 <AppIcon name="arrow-right" :size="15" />
      </RouterLink>
    </div>
  </section>
</template>
