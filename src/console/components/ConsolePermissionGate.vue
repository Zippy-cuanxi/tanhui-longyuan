<script setup lang="ts">
import { computed } from 'vue'
import { useConsoleAuth } from '@/console/stores/auth'
import { hasPermission } from '@/console/constants/permissions'

const props = defineProps<{
  code?: string
  any?: string[]
}>()
const auth = useConsoleAuth()
const allowed = computed(() => {
  if (props.any?.length) return props.any.some((item) => hasPermission(auth.permissions, item))
  return hasPermission(auth.permissions, props.code)
})
</script>

<template>
  <slot v-if="allowed" />
  <slot v-else name="fallback" />
</template>
