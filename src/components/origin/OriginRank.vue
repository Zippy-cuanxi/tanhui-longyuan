<script setup lang="ts">
import { ref } from 'vue'
import { useHeatData } from '@/composables/useHeatData'

const { rankedOrigins, metricMeta, hoveredOriginId, hoverOrigin, selectedOriginId, selectOrigin } =
  useHeatData()
const collapsed = ref(false)

function formatValue(value: number): string {
  return value.toLocaleString('zh-CN')
}
</script>

<template>
  <aside class="origin-rank" :class="{ collapsed }" aria-label="产地榜">
    <header class="rank-header">
      <h2>产地榜</h2>
      <button
        type="button"
        class="rank-toggle"
        :aria-expanded="!collapsed"
        @click="collapsed = !collapsed"
      >
        {{ collapsed ? '展开' : '收起' }}
      </button>
    </header>
    <ol v-show="!collapsed" class="rank-list">
      <li v-for="(origin, index) in rankedOrigins" :key="origin.id">
        <button
          type="button"
          class="rank-item"
          :class="{
            'is-hovered': hoveredOriginId === origin.id,
            'is-selected': selectedOriginId === origin.id
          }"
          :aria-pressed="selectedOriginId === origin.id"
          @mouseenter="hoverOrigin(origin.id)"
          @mouseleave="hoverOrigin('')"
          @focus="hoverOrigin(origin.id)"
          @blur="hoverOrigin('')"
          @click="selectOrigin(origin.id)"
        >
          <span class="rank-index">{{ index + 1 }}</span>
          <span class="rank-info">
            <strong>{{ origin.name }}</strong>
            <small>{{ origin.location }}</small>
          </span>
          <span class="rank-value">
            {{ formatValue(origin.totals[metricMeta?.key ?? 'sales']) }}
            <small>{{ metricMeta?.unit ?? '' }}</small>
          </span>
        </button>
      </li>
    </ol>
  </aside>
</template>
