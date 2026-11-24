<script setup lang="ts">
withDefaults(
  defineProps<{
    image?: string
    title?: string
    description?: string
  }>(),
  {
    image: '/console-assets/images/empty-list.png',
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
