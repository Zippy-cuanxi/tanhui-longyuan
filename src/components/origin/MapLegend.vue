<script setup lang="ts">
import { useHeatData } from '@/composables/useHeatData'

const { metricMeta, scaleDomain } = useHeatData()

function formatValue(value: number): string {
  return value.toLocaleString('zh-CN')
}
</script>

<template>
  <div class="map-legend" aria-label="热力色阶图例">
    <div class="legend-scale">
      <span>低</span>
      <span class="legend-bar" role="presentation"></span>
      <span>高</span>
      <span class="legend-range">
        {{ formatValue(scaleDomain.min) }} ~ {{ formatValue(scaleDomain.max) }}
        {{ metricMeta?.unit ?? '' }}
      </span>
    </div>
    <p class="legend-hint">拖动旋转 · 滚轮缩放 · 点击产地查看</p>
  </div>
</template>
