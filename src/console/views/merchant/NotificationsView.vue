<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleStatusTabs from '@/console/components/ConsoleStatusTabs.vue'
import ConsoleEmptyState from '@/console/components/ConsoleEmptyState.vue'
import ConsoleErrorState from '@/console/components/ConsoleErrorState.vue'
import { merchantApi, type Announcement, type Notification } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { formatDateTime, relativeTime } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const merchantId = computed(() => auth.merchantAccount?.id || '')
const tab = ref('messages')
const notifications = ref<Notification[]>([])
const notices = ref<Announcement[]>([])
const loading = ref(true)
const error = ref('')
const requestId = ref('')
const acting = ref(false)

const unread = computed(() => notifications.value.filter((item) => !item.read).length)
const tabs = computed(() => [
  { label: '消息通知', value: 'messages', count: notifications.value.length },
  { label: '未读消息', value: 'unread', count: unread.value },
  { label: '平台公告', value: 'notices', count: notices.value.length }
])

const typeLabel: Record<Notification['type'], string> = {
  order: '订单',
  system: '系统',
  notice: '公告',
  aftersale: '售后',
  finance: '结算'
}

const visibleNotifications = computed(() =>
  tab.value === 'unread' ? notifications.value.filter((item) => !item.read) : notifications.value
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const [notificationResult, noticeResult] = await Promise.all([
      merchantApi.notifications(merchantId.value),
      merchantApi.notices()
    ])
    notifications.value = notificationResult
    notices.value = noticeResult
  } catch (err) {
    const state = toErrorState(err)
    error.value = state.message
    requestId.value = state.requestId
  } finally {
    loading.value = false
  }
}

async function markRead(item: Notification): Promise<void> {
  if (item.read) return
  try {
    await merchantApi.markNotificationRead(merchantId.value, item.id)
    item.read = true
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  }
}

async function markAll(): Promise<void> {
  if (!unread.value) {
    ElMessage.info('当前没有未读消息')
    return
  }
  acting.value = true
  try {
    await merchantApi.markAllNotificationsRead(merchantId.value)
    notifications.value = notifications.value.map((item) => ({ ...item, read: true }))
    ElMessage.success('已全部标记为已读')
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="消息通知"
      description="订单、售后、结算等业务消息与平台公告；平台公告只读。"
    >
      <template #actions>
        <el-button :loading="acting" :disabled="!unread" @click="markAll"> 全部标为已读 </el-button>
        <el-button @click="load">刷新</el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleErrorState v-if="error" :message="error" :request-id="requestId" @retry="load" />
    <template v-else>
      <ConsoleStatusTabs :tabs="tabs" :model-value="tab" @update:model-value="tab = $event" />

      <div v-if="loading" class="console-card">
        <el-skeleton :rows="6" animated />
      </div>
      <template v-else-if="tab === 'notices'">
        <div v-if="!notices.length" class="console-card">
          <ConsoleEmptyState
            :image="assetUrl('/console-assets/images/empty-list.png')"
            title="暂无平台公告"
            description="平台发布公告后会出现在这里。"
          />
        </div>
        <div v-else class="console-notice-page-list">
          <article v-for="notice in notices" :key="notice.id" class="console-notice-page-item">
            <div class="console-notice-page-meta">
              <span class="console-tag-soft">平台公告</span>
              <span>{{ formatDateTime(notice.publishedAt || notice.createdAt) }}</span>
            </div>
            <h3>{{ notice.title }}</h3>
            <p>{{ notice.content }}</p>
            <span class="console-muted">发布人：{{ notice.author }}</span>
          </article>
        </div>
      </template>
      <template v-else>
        <div v-if="!visibleNotifications.length" class="console-card">
          <ConsoleEmptyState
            :image="assetUrl('/console-assets/images/empty-list.png')"
            :title="tab === 'unread' ? '没有未读消息' : '暂无消息'"
            description="订单、售后和结算消息会实时出现在这里。"
          />
        </div>
        <div v-else class="console-message-list">
          <article
            v-for="item in visibleNotifications"
            :key="item.id"
            class="console-message-item"
            :class="{ unread: !item.read }"
            @click="markRead(item)"
          >
            <span class="console-message-type">{{ typeLabel[item.type] }}</span>
            <div class="console-message-body">
              <h3>
                {{ item.title }}
                <span v-if="!item.read" class="console-message-dot" />
              </h3>
              <p>{{ item.content }}</p>
              <span>{{ relativeTime(item.createdAt) }} · {{ formatDateTime(item.createdAt) }}</span>
            </div>
            <el-button
              v-if="!item.read"
              link
              type="primary"
              size="small"
              @click.stop="markRead(item)"
            >
              标为已读
            </el-button>
            <span v-else class="console-muted" style="font-size: 11px">已读</span>
          </article>
        </div>
      </template>
    </template>
  </div>
</template>
