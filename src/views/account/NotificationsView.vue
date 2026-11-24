<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { notificationApi } from '@/api'
import type { AppNotification } from '@/api/types'
import { errorText, formatDateTime, notificationTypeLabel } from '@/utils/format'
import { useToastStore } from '@/stores/toast'
import AppIcon from '@/components/AppIcon.vue'
import StateBlock from '@/components/StateBlock.vue'

const toast = useToastStore()
const notifications = ref<AppNotification[]>([])
const loading = ref(true)
const error = ref('')
const unreadOnly = ref(false)
const marking = ref(false)

const unreadCount = computed(() => notifications.value.filter((item) => !item.read_at).length)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    notifications.value = await notificationApi.list(unreadOnly.value)
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

async function markRead(notification: AppNotification): Promise<void> {
  if (notification.read_at) return
  try {
    await notificationApi.markRead(notification.id)
    notification.read_at = new Date().toISOString()
    if (unreadOnly.value) {
      notifications.value = notifications.value.filter((item) => item.id !== notification.id)
    }
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  }
}

async function markAll(): Promise<void> {
  if (!unreadCount.value) return
  marking.value = true
  try {
    await notificationApi.markAllRead()
    await load()
    toast.show('已全部标记为已读', 'success')
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  } finally {
    marking.value = false
  }
}

function toggleFilter(): void {
  unreadOnly.value = !unreadOnly.value
  load()
}

onMounted(load)
</script>

<template>
  <div class="notifications-view">
    <header class="account-page-head">
      <div>
        <span class="eyebrow">NOTIFICATIONS</span>
        <h2>消息通知</h2>
        <p>订单、支付与售后的站内通知。</p>
      </div>
      <div class="head-actions">
        <button
          type="button"
          class="ghost-button small"
          :class="{ active: unreadOnly }"
          @click="toggleFilter"
        >
          <AppIcon name="filter" :size="14" />{{ unreadOnly ? '只看未读' : '全部消息' }}
        </button>
        <button
          type="button"
          class="outline-button small"
          :disabled="marking || !unreadCount"
          @click="markAll"
        >
          <AppIcon name="check" :size="14" />全部已读
        </button>
      </div>
    </header>

    <StateBlock
      :loading="loading"
      :error="error"
      :empty="!loading && !error && !notifications.length"
      empty-text="暂无消息通知"
      @retry="load"
    >
      <ul class="notification-list">
        <li
          v-for="item in notifications"
          :key="item.id"
          :class="{ unread: !item.read_at }"
          @click="markRead(item)"
        >
          <span class="notification-icon"><AppIcon name="bell" :size="18" /></span>
          <div>
            <div class="notification-title">
              <strong>{{ item.title }}</strong>
              <em>{{ notificationTypeLabel(item.type) }}</em>
              <span v-if="!item.read_at" class="unread-dot" />
            </div>
            <p>{{ item.content }}</p>
            <small>{{ formatDateTime(item.created_at) }}</small>
          </div>
        </li>
      </ul>
    </StateBlock>
  </div>
</template>
