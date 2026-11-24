<script setup lang="ts">
export interface StatusTab {
  label: string
  value: string
  count?: number
}

defineProps<{
  tabs: StatusTab[]
  modelValue: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <nav class="console-status-tabs" aria-label="状态筛选">
    <button
      v-for="tab in tabs"
      :key="tab.value"
      type="button"
      class="console-status-tab"
      :class="{ active: modelValue === tab.value }"
      @click="emit('update:modelValue', tab.value)"
    >
      {{ tab.label }}
      <b v-if="tab.count !== undefined">{{ tab.count }}</b>
    </button>
  </nav>
</template>
