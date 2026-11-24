<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { ElMessage } from 'element-plus'
import { copyText } from '@/console/utils/format'

const props = withDefaults(
  defineProps<{
    message?: string
    requestId?: string
  }>(),
  { message: '加载失败，请稍后重试', requestId: '' }
)
const emit = defineEmits<{ retry: [] }>()

async function copyId(): Promise<void> {
  if (!props.requestId) return
  const ok = await copyText(props.requestId)
  ElMessage[ok ? 'success' : 'warning'](ok ? 'request_id 已复制' : '复制失败，请手动选择')
}
</script>

<template>
  <div class="console-state">
    <img :src="assetUrl('/console-assets/images/error-404.webp')" alt="加载失败" loading="lazy" />
    <h3>加载失败</h3>
    <p>{{ message }}</p>
    <p v-if="requestId" class="console-mono">request_id: {{ requestId }}</p>
    <div class="console-state-actions">
      <el-button type="primary" @click="emit('retry')">重试</el-button>
      <el-button v-if="requestId" @click="copyId">复制 request_id</el-button>
    </div>
  </div>
</template>
