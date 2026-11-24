<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { commonApi, type NoticeFeedItem } from '@/console/api/common'
import { useConsoleAuth } from '@/console/stores/auth'
import { relativeTime } from '@/console/utils/format'

const auth = useConsoleAuth()
const router = useRouter()
const items = ref<NoticeFeedItem[]>([])
const unread = ref(0)
const loading = ref(false)

async function load(): Promise<void> {
  if (!auth.session || loading.value) return
  loading.value = true
  try {
    const result = await commonApi.noticeFeed(auth.session)
    items.value = result.items
    unread.value = result.unread
  } finally {
    loading.value = false
  }
}

function openAll(): void {
  if (auth.isMerchant) router.push('/console/merchant/notifications')
  else router.push('/console/admin/settings?tab=logs')
}
</script>

<template>
  <el-popover placement="bottom-end" :width="320" trigger="click" @show="load">
    <template #reference>
      <button type="button" class="console-icon-button" title="消息通知">
        <el-badge :is-dot="unread > 0" :hidden="unread === 0">
          <el-icon><Bell /></el-icon>
        </el-badge>
      </button>
    </template>
    <div>
      <div class="console-switch-row" style="padding-top: 0">
        <strong style="font-size: 13px">消息通知</strong>
        <button type="button" class="console-link" @click="openAll">查看全部</button>
      </div>
      <div v-if="loading" class="console-muted">加载中…</div>
      <div v-else-if="!items.length" class="console-muted">暂无通知</div>
      <div v-else class="console-notice-list">
        <div v-for="item in items" :key="item.id" class="console-notice-item">
          <strong>{{ item.title }}</strong>
          <span>{{ item.content }}</span>
          <span>{{ relativeTime(item.createdAt) }}</span>
        </div>
      </div>
    </div>
  </el-popover>
</template>
