<script setup lang="ts">
// 2D 平面热力地图：纯 SVG，不依赖 WebGL / maplibre / deck。
// 用于非 Chromium 内核（或 WebGL 不可用）环境兜底，交互与 3D 视图一致：
// 市州面悬停/点击、产地定位针悬停/点击、榜单联动。滚轮缩放有上下限，可拖拽平移。
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import type { Geometry } from 'geojson'
import { featureAdcode, loadGeoJson, type GeoCollection } from '@/api/heat'
import { brighten, cssRgb, heatColor } from '@/utils/heatColor'
import { useHeatData } from '@/composables/useHeatData'

const emit = defineEmits<{ ready: []; error: [reason: string] }>()

const heat = useHeatData()

const VIEW_W = 1000
const VIEW_H = 720
const PAD = 40
const MIN_SCALE = 0.9
const MAX_SCALE = 2.6

// 低缩放/窄屏只显示重点市州，避免地名打架
const PRIORITY = new Set(['620100', '620400', '620600', '620700', '620800', '620900', '621100'])

const wrap = ref<HTMLDivElement | null>(null)
const svgRef = ref<SVGSVGElement | null>(null)
const geo = shallowRef<GeoCollection | null>(null)
const paths = shallowRef<{ adcode: string; d: string }[]>([])
const labels = shallowRef<{ adcode: string; name: string; x: number; y: number }[]>([])
const pins = shallowRef<{ id: string; name: string; x: number; y: number }[]>([])

const scale = ref(1)
const tx = ref(0)
const ty = ref(0)
const wide = ref(false)

let project: ((lng: number, lat: number) => [number, number]) | null = null
let observer: ResizeObserver | null = null
let drag: { x: number; y: number; tx: number; ty: number; moved: boolean } | null = null
let disposed = false

const groupTransform = computed(
  () => `translate(${tx.value.toFixed(2)} ${ty.value.toFixed(2)}) scale(${scale.value.toFixed(3)})`
)

function mercator(lng: number, lat: number): [number, number] {
  const clamped = Math.max(-85, Math.min(85, lat))
  const x = (lng * Math.PI) / 180
  const y = Math.log(Math.tan(Math.PI / 4 + (clamped * Math.PI) / 360))
  return [x, y]
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
  if (!project) return [0, 0]
  return project(pt[0], pt[1])
}

function polyPath(poly: number[][][]): string {
  return poly.map((ring) => `M${ring.map((pt) => projectPt(pt).join(' ')).join(' L ')} Z`).join(' ')
}

function geomPath(geometry: Geometry): string {
  if (geometry.type === 'Polygon') return polyPath(geometry.coordinates as number[][][])
  if (geometry.type === 'MultiPolygon') {
    return (geometry.coordinates as number[][][][]).map(polyPath).join(' ')
  }
  return ''
}

function buildProjection(collection: GeoCollection): void {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const feature of collection.features) {
    const points: number[][] = []
    walkCoords((feature.geometry as { coordinates?: unknown } | null)?.coordinates, points)
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
}

function buildShapes(collection: GeoCollection): void {
  paths.value = collection.features.map((feature) => ({
    adcode: featureAdcode(feature),
    d: geomPath(feature.geometry)
  }))
}

function buildPoints(): void {
  if (!project || !heat.data.value) return
  const cities = heat.data.value.cities
  // 简单避让：按当前指标数值优先放置，距离过近的地名跳过，避免小市州地名叠字
  const placed: { x: number; y: number }[] = []
  const visible = cities
    .filter((city) => wide.value || PRIORITY.has(city.adcode))
    .sort((a, b) => b.totals[heat.metric.value] - a.totals[heat.metric.value])
  const picked: { adcode: string; name: string; x: number; y: number }[] = []
  for (const city of visible) {
    const [x, y] = project(city.center[0], city.center[1])
    if (placed.some((p) => Math.hypot(p.x - x, p.y - y) < 34)) continue
    placed.push({ x, y })
    picked.push({ adcode: city.adcode, name: shortName(city.name), x, y })
  }
  labels.value = picked

  pins.value = heat.data.value.origins.map((origin) => {
    const [x, y] = project!(origin.center[0], origin.center[1])
    return { id: origin.id, name: origin.name, x, y }
  })
}

function shortName(name: string): string {
  return name.replace(/(回族自治州|藏族自治州|自治州|市)$/, '')
}

function fillOf(adcode: string): string {
  const base = heatColor(heat.cityT(adcode))
  const active = adcode === heat.activeCityAdcode.value || adcode === heat.selectedCityAdcode.value
  return cssRgb(active ? brighten(base, 0.16) : base)
}

function strokeOf(adcode: string): string {
  const active = adcode === heat.activeCityAdcode.value || adcode === heat.selectedCityAdcode.value
  return active ? '#ffffff' : 'rgba(255,255,255,0.62)'
}

function strokeWidthOf(adcode: string): number {
  const active = adcode === heat.activeCityAdcode.value || adcode === heat.selectedCityAdcode.value
  return active ? 2.4 : 1.4
}

function onCityEnter(adcode: string): void {
  heat.hoverCitySurface(adcode)
}

function onCityLeave(): void {
  heat.hoverCitySurface('')
}

function onCityClick(adcode: string): void {
  if (drag?.moved) return
  heat.selectCity(adcode)
}

function onPinEnter(id: string): void {
  heat.hoverOrigin(id)
}

function onPinLeave(): void {
  heat.hoverOrigin('')
}

function onPinClick(id: string): void {
  if (drag?.moved) return
  heat.selectOrigin(id)
}

function onPinKey(id: string, event: KeyboardEvent): void {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    heat.selectOrigin(id)
  }
}

// 滚轮缩放：以指针为中心，限制 MIN_SCALE~MAX_SCALE，不能无限放大
function onWheel(event: WheelEvent): void {
  event.preventDefault()
  const el = svgRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const px = ((event.clientX - rect.left) / rect.width) * VIEW_W
  const py = ((event.clientY - rect.top) / rect.height) * VIEW_H
  const next = Math.min(
    MAX_SCALE,
    Math.max(MIN_SCALE, scale.value * Math.exp(-event.deltaY * 0.0012))
  )
  if (next === scale.value) return
  const k = next / scale.value
  tx.value = px - k * (px - tx.value)
  ty.value = py - k * (py - ty.value)
  scale.value = next
}

function onPointerDown(event: PointerEvent): void {
  drag = { x: event.clientX, y: event.clientY, tx: tx.value, ty: ty.value, moved: false }
  svgRef.value?.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent): void {
  if (!drag) return
  const dx = event.clientX - drag.x
  const dy = event.clientY - drag.y
  if (!drag.moved && Math.hypot(dx, dy) > 4) drag.moved = true
  if (!drag.moved) return
  const el = svgRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  tx.value = drag.tx + (dx / rect.width) * VIEW_W
  ty.value = drag.ty + (dy / rect.height) * VIEW_H
}

function onPointerUp(): void {
  window.setTimeout(() => {
    if (drag) drag.moved = false
    drag = null
  }, 0)
}

function resetView(): void {
  scale.value = 1
  tx.value = 0
  ty.value = 0
}

onMounted(async () => {
  observer = new ResizeObserver((entries) => {
    const width = entries[0]?.contentRect.width ?? 0
    const nextWide = width >= 768
    if (nextWide !== wide.value) {
      wide.value = nextWide
      buildPoints()
    }
  })
  if (wrap.value) observer.observe(wrap.value)

  try {
    const collection = await loadGeoJson('620000')
    if (disposed) return
    geo.value = collection
    buildProjection(collection)
    buildShapes(collection)
    buildPoints()
    emit('ready')
  } catch (err) {
    emit('error', err instanceof Error ? err.message : String(err))
  }
})

watch(
  () => [heat.data.value, heat.metric.value],
  () => {
    if (geo.value) buildPoints()
  }
)

onBeforeUnmount(() => {
  disposed = true
  observer?.disconnect()
  observer = null
})
</script>

<template>
  <div ref="wrap" class="heat-map-2d">
    <svg
      ref="svgRef"
      class="heat-map-2d-svg"
      :viewBox="`0 0 ${VIEW_W} ${VIEW_H}`"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="甘肃产地 2D 热力地图，可拖拽、滚轮缩放"
      @wheel="onWheel"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @dblclick="resetView"
    >
      <g :transform="groupTransform">
        <path
          v-for="shape in paths"
          :key="shape.adcode"
          :d="shape.d"
          class="map2d-city"
          :fill="fillOf(shape.adcode)"
          :stroke="strokeOf(shape.adcode)"
          :stroke-width="strokeWidthOf(shape.adcode)"
          @mouseenter="onCityEnter(shape.adcode)"
          @mouseleave="onCityLeave"
          @click="onCityClick(shape.adcode)"
        />

        <text
          v-for="label in labels"
          :key="label.adcode"
          class="map2d-label"
          :x="label.x"
          :y="label.y"
          text-anchor="middle"
          dominant-baseline="middle"
        >
          {{ label.name }}
        </text>

        <g
          v-for="pin in pins"
          :key="pin.id"
          class="map2d-pin"
          :class="{
            'is-hovered': pin.id === heat.hoveredOriginId.value,
            'is-selected': pin.id === heat.selectedOriginId.value
          }"
          :transform="`translate(${(pin.x - 32 * 0.34).toFixed(1)} ${(pin.y - 80 * 0.34).toFixed(1)}) scale(0.34)`"
          role="button"
          tabindex="0"
          :aria-label="`产地：${pin.name}`"
          @mouseenter="onPinEnter(pin.id)"
          @mouseleave="onPinLeave"
          @click="onPinClick(pin.id)"
          @keydown="onPinKey(pin.id, $event)"
        >
          <path
            d="M32 3C17 3 5 15 5 29.5 5 49 32 77 32 77s27-28 27-47.5C59 15 47 3 32 3z"
            fill="#0b7146"
            stroke="#ffffff"
            stroke-width="4"
          />
          <circle cx="32" cy="29" r="9.5" fill="#ffffff" />
        </g>
      </g>
    </svg>
  </div>
</template>
