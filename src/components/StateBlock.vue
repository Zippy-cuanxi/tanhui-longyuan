<script setup lang="ts">
import AppIcon from './AppIcon.vue'

withDefaults(
  defineProps<{
    loading?: boolean
    error?: string
    forbidden?: string
    empty?: boolean
    emptyText?: string
    compact?: boolean
  }>(),
  {
    loading: false,
    error: '',
    forbidden: '',
    empty: false,
    emptyText: '暂无数据',
    compact: false
  }
)

defineEmits<{ retry: [] }>()
</script>

<template>
  <div v-if="loading" class="state-block" :class="{ compact }" aria-live="polite">
    <span class="spinner" />
    <p>正在加载，请稍候…</p>
  </div>
  <div v-else-if="error" class="state-block error-state" :class="{ compact }">
    <span class="state-icon"><AppIcon name="alert" :size="26" /></span>
    <p>{{ error }}</p>
    <button class="outline-button small" type="button" @click="$emit('retry')">
      <AppIcon name="refresh" :size="15" />重新加载
    </button>
  </div>
  <div v-else-if="forbidden" class="state-block forbidden-state" :class="{ compact }">
    <span class="state-icon"><AppIcon name="shield" :size="26" /></span>
    <p>{{ forbidden }}</p>
    <RouterLink to="/" class="outline-button small">返回首页</RouterLink>
  </div>
  <div v-else-if="empty" class="state-block empty-state" :class="{ compact }">
    <span class="state-icon"><AppIcon name="sprout" :size="28" /></span>
    <p>{{ emptyText }}</p>
    <slot name="empty-action" />
  </div>
  <slot v-else />
</template>
