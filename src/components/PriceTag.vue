<script setup lang="ts">
import { money } from '@/utils/format'

withDefaults(
  defineProps<{
    amount?: string | number | null
    size?: 'sm' | 'md' | 'lg' | 'xl'
    color?: 'price' | 'ink'
  }>(),
  { amount: null, size: 'md', color: 'price' }
)
</script>

<template>
  <span class="price-tag" :class="[`size-${size}`, `color-${color}`]">
    <small>¥</small><strong>{{ money(amount) }}</strong>
  </span>
</template>
