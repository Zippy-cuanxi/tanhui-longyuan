<script setup lang="ts">
// 3D 热力地图本体：maplibre-gl（纯色背景，无瓦片无 token）+ deck.gl MapLibreOverlay。
// maplibre / deck 全部动态 import，本组件由 OriginMapStage 异步加载，单独分包。
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Map as MapLibreMap, Marker } from 'maplibre-gl'
import type { MapLibreOverlay } from '@deck.gl/maplibre'
import type { LayersList } from '@deck.gl/core'
import { featureAdcode, loadGeoJson, type GeoCollection, type GeoFeature } from '@/api/heat'
import { useHeatData } from '@/composables/useHeatData'
import { brighten, heatColor } from '@/utils/heatColor'
import 'maplibre-gl/dist/maplibre-gl.css'

const emit = defineEmits<{ ready: []; error: [reason: string] }>()

const heat = useHeatData()
const container = ref<HTMLDivElement | null>(null)

type DeckMaplibreModule = typeof import('@deck.gl/maplibre')
type DeckLayersModule = typeof import('@deck.gl/layers')

let map: MapLibreMap | null = null
let overlay: MapLibreOverlay | null = null
let deckLayers: DeckLayersModule | null = null
let maplibreModule: typeof import('maplibre-gl') | null = null
let geo: GeoCollection | null = null
let disposed = false
let readyEmitted = false
let mapLoaded = false
const markers: Marker[] = []
const markerEls = new Map<string, HTMLDivElement>()
const markerObjs = new Map<string, Marker>()
const cityLabels = new Map<string, Marker>()
let offsetFrame = 0

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

// 最高柱约省宽（约 1400km）的 6.5%
const MAX_ELEVATION = 90000
const GANSU_BOUNDS: [[number, number], [number, number]] = [
  [92.9, 32.5],
  [108.8, 42.9]
]

// 低缩放层级只显示重点市州，避免文字互相遮挡
const LABEL_ALL_ZOOM = 6.4
const PRIORITY_CITIES = new Set([
  '620100',
  '620400',
  '620600',
  '620700',
  '620800',
  '620900',
  '621100'
])
const zoom = ref(5.4)

const labelCities = computed(() => {
  const cities = heat.data.value?.cities ?? []
  if (zoom.value >= LABEL_ALL_ZOOM) return cities
  return cities.filter((city) => PRIORITY_CITIES.has(city.adcode))
})
const labelKey = computed(() => labelCities.value.map((city) => city.adcode).join(','))

function cityShortName(name: string): string {
  return name.replace(/(回族自治州|藏族自治州|自治州|市)$/, '')
}

// 站点绿色水滴定位针（白色描边）。
// 用 maplibre DOM Marker 而非 deck IconLayer：本机 WebGL 实现下 IconLayer 实例化
// 渲染损坏（拉丝，v5/v6 均复现），DOM Marker 视觉与交互等价且稳定。
const PIN_SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 80" aria-hidden="true">' +
  '<path d="M32 3C17 3 5 15 5 29.5 5 49 32 77 32 77s27-28 27-47.5C59 15 47 3 32 3z" ' +
  'fill="#0b7146" stroke="#ffffff" stroke-width="4"/>' +
  '<circle cx="32" cy="29" r="9.5" fill="#ffffff"/></svg>'

function webglAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  } catch {
    return false
  }
}

function buildLayers(): LayersList {
  if (!deckLayers || !geo || !heat.data.value) return []
  const { GeoJsonLayer } = deckLayers
  const metric = heat.metric.value
  const activeCity = heat.activeCityAdcode.value
  const selectedCity = heat.selectedCityAdcode.value
  const transitions = reducedMotion ? undefined : { getElevation: 600, getFillColor: 600 }

  const highlighted = (adcode: string) => adcode === activeCity || adcode === selectedCity

  const cityLayer = new GeoJsonLayer({
    id: 'city-extrusion',
    data: geo,
    extruded: true,
    filled: true,
    stroked: true,
    pickable: true,
    getElevation: (feature: GeoFeature) =>
      Math.max(2500, heat.cityT(featureAdcode(feature)) * MAX_ELEVATION),
    getFillColor: (feature: GeoFeature) => {
      const adcode = featureAdcode(feature)
      const base = heatColor(heat.cityT(adcode))
      const lit = highlighted(adcode) ? brighten(base, 0.16) : base
      return [lit[0], lit[1], lit[2], 255]
    },
    getLineColor: (feature: GeoFeature) =>
      highlighted(featureAdcode(feature)) ? [255, 255, 255, 255] : [255, 255, 255, 150],
    getLineWidth: (feature: GeoFeature) => (highlighted(featureAdcode(feature)) ? 2.5 : 1),
    lineWidthUnits: 'pixels',
    lineWidthMinPixels: 1,
    lineWidthMaxPixels: 4,
    // 默认光照下侧面自然比顶面略深
    material: { ambient: 0.62, diffuse: 0.5, shininess: 16, specularColor: [255, 255, 255] },
    transitions,
    updateTriggers: {
      getElevation: [metric],
      getFillColor: [metric, activeCity, selectedCity],
      getLineColor: [activeCity, selectedCity],
      getLineWidth: [activeCity, selectedCity]
    },
    onHover: (info: { object?: GeoFeature | null }) => {
      heat.hoverCitySurface(info.object ? featureAdcode(info.object) : '')
    }
  })

  return [cityLayer]
}

function syncLayers(): void {
  if (overlay && !disposed) overlay.setProps({ layers: buildLayers() })
}

// 7 个产地定位针：DOM Marker，悬停放大 / 点击选中 / 与榜单双向联动
function ensureMarkers(): void {
  if (!map || !maplibreModule || !heat.data.value || markers.length) return
  for (const origin of heat.data.value.origins) {
    const el = document.createElement('div')
    el.className = 'origin-pin-marker'
    el.innerHTML = `<div class="pin-inner">${PIN_SVG}</div>`
    el.setAttribute('role', 'button')
    el.setAttribute('aria-label', `产地：${origin.name}`)
    el.tabIndex = 0
    el.addEventListener('mouseenter', () => heat.hoverOrigin(origin.id))
    el.addEventListener('mouseleave', () => heat.hoverOrigin(''))
    el.addEventListener('click', () => heat.selectOrigin(origin.id))
    el.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        heat.selectOrigin(origin.id)
      }
    })
    const marker = new maplibreModule.Marker({ element: el, anchor: 'bottom' })
      .setLngLat(origin.center)
      .addTo(map)
    markers.push(marker)
    markerObjs.set(origin.id, marker)
    markerEls.set(origin.id, el)
  }
  updateMarkerOffsets()
  syncMarkerHover()
}

function syncMarkerHover(): void {
  for (const [id, el] of markerEls) {
    el.classList.toggle('is-hovered', id === heat.hoveredOriginId.value)
  }
}

// 柱高换算成屏幕像素：屏幕抬升 ≈ 高度(米) ÷ 每像素米数 × cos(俯角)
function liftPx(elevation: number): number {
  if (!map) return 0
  const centerLat = map.getCenter().lat
  const metersPerPx =
    (40075016.686 * Math.cos((centerLat * Math.PI) / 180)) / (512 * Math.pow(2, map.getZoom()))
  return (elevation / metersPerPx) * Math.cos((map.getPitch() * Math.PI) / 180)
}

// 市州地名：用 DOM Marker 绘制，随视角实时抬到柱顶。
// deck TextLayer 的 getPosition 只吃 2D 坐标，z 高度会被丢弃，文字因此贴地
// 沉到柱体下方；改 DOM 后悬停/缩放都无偏移。
function syncCityLabels(): void {
  if (!map || !maplibreModule || !heat.data.value) return
  const wanted = new Map(labelCities.value.map((city) => [city.adcode, city]))
  for (const [adcode, marker] of cityLabels) {
    if (!wanted.has(adcode)) {
      marker.remove()
      cityLabels.delete(adcode)
    }
  }
  for (const city of labelCities.value) {
    if (cityLabels.has(city.adcode)) continue
    const el = document.createElement('div')
    el.className = 'origin-city-label'
    el.textContent = cityShortName(city.name)
    const marker = new maplibreModule.Marker({ element: el, anchor: 'center' })
      .setLngLat(city.center)
      .addTo(map)
    cityLabels.set(city.adcode, marker)
  }
  updateLabelOffsets()
}

function updateLabelOffsets(): void {
  if (!map || !heat.data.value) return
  for (const city of heat.data.value.cities) {
    const marker = cityLabels.get(city.adcode)
    if (!marker) continue
    const elevation = Math.max(2500, heat.cityT(city.adcode) * MAX_ELEVATION)
    marker.setOffset([0, -liftPx(elevation) - 6])
  }
}

// 定位针也抬到对应市州柱顶，避免针尖陷在柱体底部。
function updateMarkerOffsets(): void {
  if (!map || !heat.data.value) return
  for (const origin of heat.data.value.origins) {
    const marker = markerObjs.get(origin.id)
    if (!marker) continue
    const elevation = Math.max(2500, heat.cityT(origin.cityAdcode) * MAX_ELEVATION)
    marker.setOffset([0, -liftPx(elevation)])
  }
}

function scheduleMarkerOffsets(): void {
  if (offsetFrame) return
  offsetFrame = window.requestAnimationFrame(() => {
    offsetFrame = 0
    updateMarkerOffsets()
    updateLabelOffsets()
  })
}

function tryReady(): void {
  if (readyEmitted || disposed) return
  if (mapLoaded && geo && heat.data.value) {
    syncLayers()
    ensureMarkers()
    syncCityLabels()
    readyEmitted = true
    emit('ready')
  }
}

function fail(reason: string): void {
  if (disposed || readyEmitted) return
  console.error('[origin-map]', reason)
  emit('error', reason)
}

const onZoom = () => {
  if (map) zoom.value = map.getZoom()
}

// 供舞台的旋转轮盘调用
function rotateTo(deg: number): void {
  map?.setBearing(deg)
}

function getBearing(): number {
  return map ? map.getBearing() : -15
}

defineExpose({ rotateTo, getBearing })

onMounted(async () => {
  if (!webglAvailable()) {
    fail('当前环境不支持 WebGL')
    return
  }
  try {
    const [maplibre, deckMaplibre, layersModule, geoData] = await Promise.all([
      import('maplibre-gl'),
      import('@deck.gl/maplibre'),
      import('@deck.gl/layers'),
      loadGeoJson('620000')
    ])
    if (disposed || !container.value) return
    deckLayers = layersModule
    maplibreModule = maplibre
    geo = geoData

    const stageWidth = container.value.clientWidth
    // 窄屏（手机/窄窗）降低俯角、收紧留白，否则省域被压小、标注与柱体错位更明显
    const narrow = stageWidth < 600
    const panelPadding = stageWidth >= 900 ? 372 : narrow ? 12 : 24
    map = new maplibre.Map({
      container: container.value,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#eaf3ec' } }]
      },
      center: [100.8, 37.6],
      zoom: 5,
      pitch: narrow ? 32 : 45,
      bearing: -15,
      maxPitch: 65,
      // 缩放上下限：滚轮不能无限放大
      minZoom: 4.8,
      maxZoom: 8.5,
      canvasContextAttributes: { antialias: true },
      attributionControl: false,
      doubleClickZoom: false,
      renderWorldCopies: false
    })
    map.fitBounds(GANSU_BOUNDS, {
      padding: narrow
        ? { top: 46, bottom: 54, left: 10, right: 10 }
        : { top: 70, bottom: 100, left: 40, right: panelPadding },
      duration: 0
    })

    const deckOverlay = new (deckMaplibre as DeckMaplibreModule).MapLibreOverlay({
      interleaved: false,
      layers: []
    })
    overlay = deckOverlay
    map.addControl(deckOverlay)

    map.on('load', () => {
      mapLoaded = true
      tryReady()
    })
    map.on('zoom', onZoom)
    // 视角变化时重算定位针抬升量，保证针始终贴柱顶
    map.on('move', scheduleMarkerOffsets)
    map.on('pitch', scheduleMarkerOffsets)
    map.on('error', (event) => {
      if (!readyEmitted) fail(event.error?.message ?? '地图初始化失败')
      else console.error('[origin-map]', event.error)
    })
    map.on('webglcontextlost', () => {
      fail('WebGL 上下文丢失')
    })

    // GeoJSON 中找不到对应市州数据时给出警告，不崩溃
    const known = new Set((heat.data.value?.cities ?? []).map((city) => city.adcode))
    if (known.size) {
      for (const feature of geo.features) {
        if (!known.has(featureAdcode(feature))) {
          console.warn('[origin-map] GeoJSON 市州无热力数据：', feature.properties.name)
        }
      }
    }
    tryReady()
  } catch (err) {
    fail(err instanceof Error ? err.message : String(err))
  }
})

watch(
  [
    () => heat.data.value,
    () => heat.metric.value,
    () => heat.activeCityAdcode.value,
    () => heat.selectedCityAdcode.value,
    () => heat.hoveredOriginId.value,
    labelKey
  ],
  () => {
    if (readyEmitted) {
      syncLayers()
      syncCityLabels()
    } else {
      tryReady()
    }
  }
)

watch(
  () => heat.hoveredOriginId.value,
  () => syncMarkerHover()
)

watch(
  () => heat.error.value,
  (message) => {
    if (message) fail(message)
  }
)

onBeforeUnmount(() => {
  disposed = true
  if (offsetFrame) {
    window.cancelAnimationFrame(offsetFrame)
    offsetFrame = 0
  }
  for (const marker of markers) marker.remove()
  markers.length = 0
  markerEls.clear()
  markerObjs.clear()
  for (const marker of cityLabels.values()) marker.remove()
  cityLabels.clear()
  if (map) {
    map.off('zoom', onZoom)
    map.off('move', scheduleMarkerOffsets)
    map.off('pitch', scheduleMarkerOffsets)
    // map.remove() 会移除 MapLibreOverlay 控件并触发 deck.finalize()
    map.remove()
  }
  map = null
  overlay = null
  deckLayers = null
  maplibreModule = null
  geo = null
})
</script>

<template>
  <div
    ref="container"
    class="heat-map-canvas"
    role="img"
    aria-label="甘肃产地热力地图，可通过右侧产地榜浏览"
  ></div>
</template>
