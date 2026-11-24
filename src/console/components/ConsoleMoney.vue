<script setup lang="ts">
import { computed } from 'vue'
import { formatMoney } from '@/console/utils/format'

const props = withDefaults(
  defineProps<{
    value?: string | number | null
    signed?: boolean
    symbol?: boolean
  }>(),
  { signed: false, symbol: false, value: null }
)

const text = computed(() => {
  const value = formatMoney(props.value)
  if (value === '—') return value
  if (props.signed && !value.startsWith('-') && Number(value) > 0) return `+${value}`
  return value
})
const negative = computed(() => String(props.value ?? '').startsWith('-'))
</script>

<template>
  <span class="console-mono" :class="{ 'console-amount': negative, positive: signed && !negative }">
    <template v-if="symbol">¥</template>{{ text }}
  </span>
</template>
