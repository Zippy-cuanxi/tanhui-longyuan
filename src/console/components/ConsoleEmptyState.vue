<script setup lang="ts">
import { assetUrl } from '@/api/http'
withDefaults(
  defineProps<{
    image?: string
    title?: string
    description?: string
  }>(),
  {
    image: assetUrl('/console-assets/images/empty-list.webp'),
    title: '暂无数据',
    description: ''
  }
)
</script>

<template>
  <div class="console-state">
    <img :src="image" :alt="title" loading="lazy" />
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <div class="console-state-actions">
      <slot name="actions" />
    </div>
  </div>
</template>
