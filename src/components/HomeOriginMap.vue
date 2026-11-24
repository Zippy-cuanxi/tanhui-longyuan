<script setup lang="ts">
// 首页「甘肃产地地图」卡片：标准 2D 平面地图（纯 SVG）。
// 每个市州面支持悬停提示（即时显示，无延迟）与点击跳转该市州商品列表。
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import type { Geometry } from 'geojson'
import { featureAdcode, getHeatData, loadGeoJson, type CityHeat, type HeatData } from '@/api/heat'

const router = useRouter()

const VIEW_W = 1000
const VIEW_H = 600
const PAD = 18
const viewBox = ref(`0 0 ${VIEW_W} ${VIEW_H}`)

// 市州 → 商品列表搜索词：有产地商品的用产地关键词，其余用市州名
const KEYWORD: Record<string, string> = {
  '620800': '静宁',
  '621100': '定西',
  '620600': '民勤',
  '620400': '枸杞',
  '620700': '临泽',
  '620100': '百合'
}

const PRIORITY = new Set(['620100', '620400', '620600', '620700', '620800', '620900', '621100'])

const wrap = ref<HTMLDivElement | null>(null)
const heatData = shallowRef<HeatData | null>(null)
const paths = shallowRef<{ adcode: string; name: string; d: string }[]>([])
const labels = shallowRef<{ adcode: string; name: string; x: number; y: number }[]>([])
const active = ref<CityHeat | null>(null)
const ready = ref(false)
const tipPos = ref({ x: 0, y: 0 })

let project: ((lng: number, lat: number) => [number, number]) | null = null
let disposed = false

const activeInfo = computed(() => {
  const city = active.value
  if (!city) return null
  const origins =
    heatData.value?.origins.filter((origin) => origin.cityAdcode === city.adcode) ?? []
  const sales = city.totals.sales.toLocaleString('zh-CN')
  const names = origins.map((origin) => origin.productName)
  const list = names.length > 2 ? `${names.slice(0, 2).join('、')} 等` : names.join('、')
  return {
    name: city.name,
    sales,
    count: origins.length,
    list,
    hint: origins.length ? '点击查看该产地商品' : '点击查看该地区商品'
  }
})

function shortName(name: string): string {
  return name.replace(/(回族自治州|藏族自治州|自治州|市)$/, '')
}

function keywordOf(adcode: string, name: string): string {
  return KEYWORD[adcode] ?? shortName(name)
}

function hrefOf(adcode: string, name: string): string {
  return `/products?keyword=${encodeURIComponent(keywordOf(adcode, name))}`
}

function mercator(lng: number, lat: number): [number, number] {
  const clamped = Math.max(-85, Math.min(85, lat))
  return [(lng * Math.PI) / 180, Math.log(Math.tan(Math.PI / 4 + (clamped * Math.PI) / 360))]
}

function walkCoords(coords: unknown, out: number[][]): void {
  if (!Array.isArray(coords)) return
  if (typeof coords[0] === 'number') {
    out.push(coords as number[])
    return
  }
  for (const child of coords) walkCoords(child, out)
}

function projectPt(pt: number[]): [number, number] {
  const [x, y] = project ? project(pt[0], pt[1]) : [0, 0]
  // 保留 0.1px 精度：视觉上不可分辨，但能大幅缩短 SVG path 字符串，
  // 减少首屏 HTML/样式布局与解析开销（整页地图含数万个顶点）。
  return [Math.round(x * 10) / 10, Math.round(y * 10) / 10]
}

function polyPath(poly: number[][][]): string {
  return poly.map((ring) => `M${ring.map((p) => projectPt(p).join(' ')).join(' L ')} Z`).join(' ')
}

function geomPath(geometry: Geometry): string {
  if (geometry.type === 'Polygon') return polyPath(geometry.coordinates as number[][][])
  if (geometry.type === 'MultiPolygon') {
    return (geometry.coordinates as number[][][][]).map(polyPath).join(' ')
  }
  return ''
}

function buildProjection(features: { geometry: Geometry }[]): void {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const feature of features) {
    const points: number[][] = []
    walkCoords((feature.geometry as { coordinates?: unknown }).coordinates, points)
    for (const pt of points) {
      const [x, y] = mercator(pt[0], pt[1])
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x)
      maxY = Math.max(maxY, y)
    }
  }
  const spanX = Math.max(1e-6, maxX - minX)
  const spanY = Math.max(1e-6, maxY - minY)
  const s = Math.min((VIEW_W - PAD * 2) / spanX, (VIEW_H - PAD * 2) / spanY)
  const ox = (VIEW_W - spanX * s) / 2 - minX * s
  const oy = (VIEW_H - spanY * s) / 2 + maxY * s
  project = (lng, lat) => {
    const [x, y] = mercator(lng, lat)
    return [x * s + ox, oy - y * s]
  }

  // 用投影后的实际图形范围收紧 viewBox，避免图形在卡片里被大片空白缩小
  let px0 = Infinity
  let py0 = Infinity
  let px1 = -Infinity
  let py1 = -Infinity
  for (const feature of features) {
    const points: number[][] = []
    walkCoords((feature.geometry as { coordinates?: unknown }).coordinates, points)
    for (const pt of points) {
      const [x, y] = project(pt[0], pt[1])
      px0 = Math.min(px0, x)
      py0 = Math.min(py0, y)
      px1 = Math.max(px1, x)
      py1 = Math.max(py1, y)
    }
  }
  const pad = 12
  viewBox.value = `${px0 - pad} ${py0 - pad} ${px1 - px0 + pad * 2} ${py1 - py0 + pad * 2}`
}

function buildLabels(data: HeatData): void {
  if (!project) return
  labels.value = data.cities
    .filter((city) => PRIORITY.has(city.adcode))
    .map((city) => {
      const [x, y] = project!(city.center[0], city.center[1])
      return { adcode: city.adcode, name: shortName(city.name), x, y }
    })
}

function placeTip(clientX: number, clientY: number): void {
  if (!wrap.value) return
  const rect = wrap.value.getBoundingClientRect()
  const tipW = 208
  const tipH = 96
  const x = Math.min(Math.max(clientX - rect.left + 14, 8), rect.width - tipW - 8)
  const y = Math.min(Math.max(clientY - rect.top + 14, 8), rect.height - tipH - 8)
  tipPos.value = { x, y }
}

function onEnter(adcode: string, event?: MouseEvent): void {
  const city = heatData.value?.cities.find((item) => item.adcode === adcode) ?? null
  active.value = city
  if (city && event && event.clientX && event.clientY) {
    placeTip(event.clientX, event.clientY)
  }
}

function onLeave(): void {
  active.value = null
}

// 提示框跟随指针，限制在卡片内，避免溢出
function onMove(event: PointerEvent): void {
  if (!active.value) return
  placeTip(event.clientX, event.clientY)
}

function go(adcode: string, name: string): void {
  router.push({ name: 'products', query: { keyword: keywordOf(adcode, name) } })
}

function onKey(adcode: string, name: string, event: KeyboardEvent): void {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    go(adcode, name)
  }
}

async function loadMap(): Promise<void> {
  try {
    const [collection, data] = await Promise.all([loadGeoJson('620000'), getHeatData()])
    if (disposed) return
    heatData.value = data
    buildProjection(collection.features)
    paths.value = collection.features.map((feature) => ({
      adcode: featureAdcode(feature),
      name: String(feature.properties.name ?? ''),
      d: geomPath(feature.geometry)
    }))
    buildLabels(data)
    ready.value = true
  } catch (err) {
    console.error('[home-origin-map] 2D 地图加载失败', err)
  }
}

let mapRaf = 0
let mapTimer = 0

onMounted(() => {
  // 地图在首屏下方，晚一帧构建即可；先让轮播/商品完成首次绘制，
  // 避免数万个 SVG 顶点的解析与布局占用 LCP 的关键帧。
  mapRaf = window.requestAnimationFrame(() => {
    mapTimer = window.setTimeout(() => void loadMap(), 0)
  })
})

onBeforeUnmount(() => {
  disposed = true
  window.cancelAnimationFrame(mapRaf)
  window.clearTimeout(mapTimer)
})
</script>

<template>
  <div ref="wrap" class="home-origin-map" :class="{ 'is-ready': ready }" @pointermove="onMove">
    <svg
      class="home-origin-map-svg"
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
      role="group"
      aria-label="甘肃产地 2D 地图，悬停查看详情，点击进入对应商品列表"
    >
      <path
        v-for="region in paths"
        :key="region.adcode"
        class="home-map-region"
        :class="{ 'is-active': active?.adcode === region.adcode }"
        :d="region.d"
        :data-adcode="region.adcode"
        :data-href="hrefOf(region.adcode, region.name)"
        role="link"
        tabindex="0"
        :aria-label="`${region.name}，点击查看商品`"
        @mouseenter="onEnter(region.adcode, $event)"
        @mouseleave="onLeave"
        @click="go(region.adcode, region.name)"
        @keydown="onKey(region.adcode, region.name, $event)"
      />
      <text
        v-for="label in labels"
        :key="label.adcode"
        class="home-map-label"
        :x="label.x"
        :y="label.y"
        text-anchor="middle"
        dominant-baseline="middle"
      >
        {{ label.name }}
      </text>
    </svg>

    <div
      v-if="activeInfo"
      class="home-map-tip"
      :style="{ left: `${tipPos.x}px`, top: `${tipPos.y}px` }"
      aria-live="polite"
    >
      <strong>{{ activeInfo.name }}</strong>
      <span class="home-map-tip-meta">
        年销 {{ activeInfo.sales }} 件 · 产地 {{ activeInfo.count }} 个
      </span>
      <span v-if="activeInfo.list" class="home-map-tip-list">{{ activeInfo.list }}</span>
      <em>{{ activeInfo.hint }}</em>
    </div>
  </div>
</template>
