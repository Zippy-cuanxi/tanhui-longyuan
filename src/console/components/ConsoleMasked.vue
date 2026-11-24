<script setup lang="ts">
import { computed } from 'vue'
import { maskAddress, maskEmail, maskPhone } from '@/console/utils/format'

const props = withDefaults(
  defineProps<{
    value?: string | null
    kind?: 'phone' | 'email' | 'address'
    reveal?: boolean
  }>(),
  { kind: 'phone', reveal: false, value: null }
)

const text = computed(() => {
  if (props.reveal) return props.value || '—'
  if (props.kind === 'email') return maskEmail(props.value)
  if (props.kind === 'address') return maskAddress(props.value)
  return maskPhone(props.value)
})
</script>

<template>
  <span>{{ text }}</span>
</template>
