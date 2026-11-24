<script setup lang="ts">
import AppIcon from './AppIcon.vue'

defineProps<{
  items: Array<{ label: string; to?: string | Record<string, unknown> }>
}>()
</script>

<template>
  <nav class="breadcrumbs" aria-label="面包屑">
    <template v-for="(item, index) in items" :key="`${item.label}-${index}`">
      <AppIcon v-if="index > 0" name="chevron-right" :size="12" class="crumb-sep" />
      <RouterLink v-if="item.to" :to="item.to">{{ item.label }}</RouterLink>
      <span v-else aria-current="page">{{ item.label }}</span>
    </template>
  </nav>
</template>
