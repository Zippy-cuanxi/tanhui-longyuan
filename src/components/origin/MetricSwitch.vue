<script setup lang="ts">
import { useHeatData } from '@/composables/useHeatData'

const { data, metric, setMetric } = useHeatData()
</script>

<template>
  <div class="metric-switch" role="group" aria-label="热力指标切换">
    <button
      v-for="item in data?.meta.metrics ?? []"
      :key="item.key"
      type="button"
      :class="{ active: metric === item.key }"
      :aria-pressed="metric === item.key"
      @click="setMetric(item.key)"
    >
      {{ item.label }}
    </button>
  </div>
</template>
