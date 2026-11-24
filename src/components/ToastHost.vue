<script setup lang="ts">
import { ref } from 'vue'
import { useToastStore } from '@/stores/toast'
import AppIcon from './AppIcon.vue'

const toast = useToastStore()
const copied = ref(false)

async function copyRequestId(): Promise<void> {
  if (!toast.requestId) return
  try {
    await navigator.clipboard.writeText(toast.requestId)
    copied.value = true
    window.setTimeout(() => {
      copied.value = false
    }, 1600)
  } catch {
    copied.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="toast">
      <div
        v-if="toast.visible"
        class="toast"
        :class="`toast-${toast.type}`"
        role="status"
        aria-live="polite"
      >
        <span class="toast-icon"><AppIcon :name="toast.icon" :size="18" /></span>
        <div class="toast-content">
          <p>{{ toast.message }}</p>
          <button
            v-if="toast.requestId"
            type="button"
            class="toast-request"
            title="复制 request_id 便于排查"
            @click="copyRequestId"
          >
            request_id: {{ toast.requestId.slice(0, 12) }}…
            <span>{{ copied ? '已复制' : '复制' }}</span>
          </button>
        </div>
        <button type="button" class="toast-close" aria-label="关闭提示" @click="toast.hide">
          <AppIcon name="close" :size="15" />
        </button>
      </div>
    </Transition>
  </Teleport>
</template>
