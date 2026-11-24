<script setup lang="ts">
import { orderStatusLabel, orderStatusTone } from '@/utils/format'

defineProps<{ status?: string | null }>()
</script>

<template>
  <span class="status-tag" :class="`tone-${orderStatusTone(status)}`">{{
    orderStatusLabel(status)
  }}</span>
</template>
