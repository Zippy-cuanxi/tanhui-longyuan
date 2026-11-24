<script setup lang="ts">
import type { Sku } from '@/api/types'
import { money } from '@/utils/format'

defineProps<{
  skus: Sku[]
  modelValue: Sku | null
}>()

const emit = defineEmits<{ 'update:modelValue': [sku: Sku] }>()
</script>

<template>
  <div class="sku-options" role="radiogroup" aria-label="选择规格">
    <button
      v-for="sku in skus"
      :key="sku.id"
      type="button"
      role="radio"
      :aria-checked="modelValue?.id === sku.id"
      :class="{ active: modelValue?.id === sku.id }"
      :disabled="!sku.is_active"
      @click="emit('update:modelValue', sku)"
    >
      <span>{{ sku.spec }}</span>
      <small>¥{{ money(sku.price) }}</small>
    </button>
  </div>
</template>
