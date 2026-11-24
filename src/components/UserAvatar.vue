<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { assetUrl } from '@/api/http'

const props = withDefaults(
  defineProps<{
    url?: string | null
    text?: string
    size?: number
  }>(),
  { url: '', text: '陇', size: 40 }
)

const broken = ref(false)
const src = computed(() => assetUrl(props.url))
const fontSize = computed(() => `${Math.max(11, Math.round(props.size * 0.42))}px`)

watch(src, () => {
  broken.value = false
})
</script>

<template>
  <span class="user-avatar" :style="{ width: `${size}px`, height: `${size}px`, fontSize }">
    <img v-if="src && !broken" :src="src" alt="用户头像" @error="broken = true" />
    <template v-else>{{ text }}</template>
  </span>
</template>
