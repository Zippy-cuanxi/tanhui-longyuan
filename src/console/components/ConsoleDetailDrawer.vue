<script setup lang="ts">
import ConsoleErrorState from './ConsoleErrorState.vue'

withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    size?: string
    loading?: boolean
    error?: string
    errorRequestId?: string
  }>(),
  { size: '720px', loading: false, error: '', errorRequestId: '' }
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  retry: []
}>()
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    :size="size"
    class="console-drawer"
    :with-header="true"
    destroy-on-close
    @update:model-value="(value: boolean) => emit('update:modelValue', value)"
  >
    <template #header>
      <div class="console-drawer-title">{{ title }}</div>
    </template>
    <el-skeleton v-if="loading" :rows="8" animated />
    <ConsoleErrorState
      v-else-if="error"
      :message="error"
      :request-id="errorRequestId"
      @retry="emit('retry')"
    />
    <div v-else>
      <slot />
    </div>
    <template v-if="$slots.footer" #footer>
      <div class="console-inline-actions" style="justify-content: flex-end">
        <slot name="footer" />
      </div>
    </template>
  </el-drawer>
</template>
