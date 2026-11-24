<script setup lang="ts">
// 地图舞台：3D/2D 双视图、占位骨架、镜头旋转轮盘、数据兜底、四组浮层。
// 3D 走 maplibre + deck（异步分包）；2D 是纯 SVG，不依赖 WebGL，供非 Chromium 浏览器兜底。
import { defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useHeatData } from '@/composables/useHeatData'
import MetricSwitch from './MetricSwitch.vue'
import OriginRank from './OriginRank.vue'
import MapLegend from './MapLegend.vue'
import ViewSwitch from './ViewSwitch.vue'
import RotateDial from './RotateDial.vue'
import './origin-map.css'

const HeatMap3D = defineAsyncComponent(() => import('./HeatMap3D.vue'))
const HeatMap2D = defineAsyncComponent(() => import('./HeatMap2D.vue'))

const emit = defineEmits<{ fallback: [reason: string] }>()

type MapView = '3d' | '2d'
const DEFAULT_BEARING = -15

const heat = useHeatData()
const ready = ref(false)
const failed = ref(false)
// 3D/2D 地图（maplibre + deck 约 1.7MB）推迟到首屏绘制后的空闲帧再挂载，
// 避免与关键 JS/CSS 抢带宽；期间显示骨架，视觉上仍是"加载中"。
const mapMount = ref(false)
// 3D 初始化失败（瞬时资源/上下文问题）先自动重建一次；仍失败就切 2D，而不是退回旧版式
const attempts = ref(0)
const mountToken = ref(0)
const view = ref<MapView>('3d')
const bearing = ref(DEFAULT_BEARING)
const map3d = ref<{ rotateTo: (deg: number) => void; getBearing: () => number } | null>(null)

function onReady(): void {
  ready.value = true
  stopWatchdog()
  if (view.value === '3d' && map3d.value) {
    bearing.value = map3d.value.getBearing()
  }
}

// 3D 静默卡住（worker/WebGL 不报错也不 ready）时兜底切 2D
let watchdog = 0

function stopWatchdog(): void {
  if (watchdog) {
    window.clearTimeout(watchdog)
    watchdog = 0
  }
}

function startWatchdog(): void {
  stopWatchdog()
  if (view.value !== '3d' || failed.value) return
  watchdog = window.setTimeout(() => {
    watchdog = 0
    if (!ready.value && view.value === '3d' && !failed.value) {
      console.warn('[origin-map] 3D 初始化超时，切换 2D 视图')
      switchView('2d')
    }
  }, 9000)
}

watch(view, startWatchdog, { immediate: true })

onMounted(() => {
  const kick = (): void => {
    mapMount.value = true
  }
  const idle = (
    window as Window & {
      requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number
    }
  ).requestIdleCallback
  if (idle) idle(kick, { timeout: 600 })
  else setTimeout(kick, 200)
})

onBeforeUnmount(() => {
  stopWatchdog()
  stopBearingAnimation()
})

function on3dError(reason: string): void {
  if (failed.value || view.value !== '3d') return
  if (attempts.value < 1) {
    attempts.value += 1
    console.warn('[origin-map] 3D 初始化失败，自动重试：', reason)
    window.setTimeout(() => {
      ready.value = false
      mountToken.value += 1
    }, 700)
    return
  }
  console.warn('[origin-map] 3D 不可用，切换 2D 视图：', reason)
  switchView('2d')
}

function on2dError(reason: string): void {
  if (failed.value) return
  failed.value = true
  console.warn('[origin-map] 回退为静态说明：', reason)
  emit('fallback', reason)
}

function switchView(next: MapView): void {
  if (next === view.value) return
  view.value = next
  ready.value = false
  if (next === '3d') {
    attempts.value = 0
    mountToken.value += 1
  }
}

// 方位角：拖动实时跟随（无缓动）；点按回正走 360ms 缓动，避免视角突然跳
let bearingFrame = 0

function normalizeAngle(deg: number): number {
  return ((((deg + 180) % 360) + 360) % 360) - 180
}

function stopBearingAnimation(): void {
  if (bearingFrame) {
    window.cancelAnimationFrame(bearingFrame)
    bearingFrame = 0
  }
}

function onRotate(deg: number): void {
  stopBearingAnimation()
  const normalized = normalizeAngle(deg)
  bearing.value = normalized
  map3d.value?.rotateTo(normalized)
}

function animateBearingTo(target: number): void {
  stopBearingAnimation()
  const from = bearing.value
  const delta = ((target - from + 540) % 360) - 180
  const startTime = performance.now()
  const duration = 360
  const step = (now: number): void => {
    const progress = Math.min(1, (now - startTime) / duration)
    const eased = 1 - Math.pow(1 - progress, 3)
    const value = normalizeAngle(from + delta * eased)
    bearing.value = value
    map3d.value?.rotateTo(value)
    bearingFrame = progress < 1 ? window.requestAnimationFrame(step) : 0
  }
  bearingFrame = window.requestAnimationFrame(step)
}

function resetBearing(): void {
  animateBearingTo(DEFAULT_BEARING)
}

watch(
  () => heat.error.value,
  (message) => {
    if (message) on3dError(message)
  }
)
</script>

<template>
  <section v-if="!failed" class="origin-map-stage" aria-label="甘肃产地地图">
    <div
      class="stage-placeholder stage-skeleton"
      :class="{ 'is-hidden': ready }"
      aria-hidden="true"
    >
      <span class="skeleton-ring"></span>
      <em>{{ view === '3d' ? '3D 地图加载中…' : '2D 地图加载中…' }}</em>
    </div>

    <HeatMap3D
      v-if="mapMount && view === '3d'"
      ref="map3d"
      :key="`3d-${mountToken}`"
      @ready="onReady"
      @error="on3dError"
    />
    <HeatMap2D v-else-if="mapMount" :key="'2d'" @ready="onReady" @error="on2dError" />

    <div class="stage-overlay stage-title">
      <span class="eyebrow">GANSU ORIGIN</span>
      <h1>甘肃产地地图</h1>
      <p>一县一品一好物 · 溯源直达原产地</p>
    </div>

    <MetricSwitch class="stage-overlay stage-metric" />
    <OriginRank class="stage-overlay stage-rank" />
    <MapLegend class="stage-overlay stage-legend" />

    <div class="stage-controls">
      <RotateDial
        v-if="view === '3d'"
        :bearing="bearing"
        @rotate="onRotate"
        @reset="resetBearing"
      />
      <ViewSwitch :view="view" @change="switchView" />
    </div>
  </section>
</template>
