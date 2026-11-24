<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = withDefaults(
  defineProps<{
    modelValue: number
    min?: number
    max?: number
    disabled?: boolean
    compact?: boolean
  }>(),
  { min: 1, max: 999, disabled: false, compact: false }
)

const emit = defineEmits<{ 'update:modelValue': [value: number]; change: [value: number] }>()

const safeValue = computed(() => {
  const value = Number(props.modelValue)
  if (!Number.isFinite(value)) return props.min
  return Math.min(props.max, Math.max(props.min, Math.round(value)))
})

function set(value: number): void {
  const next = Math.min(props.max, Math.max(props.min, Math.round(value)))
  emit('update:modelValue', next)
  emit('change', next)
}

function onInput(event: Event): void {
  const value = Number((event.target as HTMLInputElement).value)
  if (!Number.isFinite(value)) return
  emit('update:modelValue', value)
}

function onBlur(): void {
  set(Number(props.modelValue) || props.min)
}
</script>

<template>
  <div class="quantity-control" :class="{ compact, disabled }">
    <button
      type="button"
      aria-label="减少数量"
      :disabled="disabled || safeValue <= min"
      @click="set(safeValue - 1)"
    >
      <AppIcon name="minus" :size="compact ? 13 : 16" />
    </button>
    <input
      :value="modelValue"
      type="number"
      :min="min"
      :max="max"
      :disabled="disabled"
      aria-label="购买数量"
      @input="onInput"
      @blur="onBlur"
    />
    <button
      type="button"
      aria-label="增加数量"
      :disabled="disabled || safeValue >= max"
      @click="set(safeValue + 1)"
    >
      <AppIcon name="plus" :size="compact ? 13 : 16" />
    </button>
  </div>
</template>
