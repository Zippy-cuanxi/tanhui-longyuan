<script setup lang="ts">
import { useRouter } from 'vue-router'

const props = withDefaults(
  defineProps<{
    label: string
    value: string
    hint?: string
    tone?: 'default' | 'green' | 'gold'
    to?: string
  }>(),
  { hint: '', tone: 'default', to: '' }
)
const router = useRouter()

function open(): void {
  if (props.to) router.push(props.to)
}
</script>

<template>
  <div class="console-kpi" :class="tone" @click="open">
    <div class="console-kpi-label">{{ label }}</div>
    <div class="console-kpi-value">{{ value }}</div>
    <div v-if="hint" class="console-kpi-hint">{{ hint }}</div>
  </div>
</template>
