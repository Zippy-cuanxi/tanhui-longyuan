// /origin 页热力地图的共享状态：数据加载、当前指标、悬停/选中、派生榜单。
// 由 OriginView 调 provideHeatData() 创建并注入，地图与浮层组件用 useHeatData() 读取。
import { computed, inject, provide, ref, shallowRef, type InjectionKey } from 'vue'
import { getHeatData, type HeatData, type HeatMetricKey, type OriginHeat } from '@/api/heat'
import { heatT, type HeatScaleDomain } from '@/utils/heatColor'

function createHeatContext() {
  const data = shallowRef<HeatData | null>(null)
  const loading = ref(true)
  const error = ref('')

  const metric = ref<HeatMetricKey>('sales')
  // 定位针/榜单悬停与地图市州面悬停分开记录，避免两类 onHover 互相覆盖
  const hoveredOriginId = ref('')
  const hoveredCityCode = ref('')
  const selectedOriginId = ref('')
  const selectedCityAdcode = ref('')

  async function load(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      data.value = await getHeatData()
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      console.error('[origin-heat] 热力数据加载失败', err)
    } finally {
      loading.value = false
    }
  }

  const metricMeta = computed(
    () => data.value?.meta.metrics.find((m) => m.key === metric.value) ?? null
  )

  // 全年累计视角用 totalMax 作为固定色彩域上限
  const scaleDomain = computed<HeatScaleDomain>(() => {
    const domain = data.value?.meta.domain[metric.value]
    return domain ? { min: domain.min, max: domain.totalMax } : { min: 0, max: 1 }
  })

  const originById = computed(() => {
    const map = new Map<string, OriginHeat>()
    for (const origin of data.value?.origins ?? []) map.set(origin.id, origin)
    return map
  })

  const activeCityAdcode = computed(() => {
    if (hoveredOriginId.value) {
      return originById.value.get(hoveredOriginId.value)?.cityAdcode ?? ''
    }
    return hoveredCityCode.value
  })

  const rankedOrigins = computed(() =>
    [...(data.value?.origins ?? [])].sort((a, b) => b.totals[metric.value] - a.totals[metric.value])
  )

  const selectedOrigin = computed(() =>
    selectedOriginId.value ? (originById.value.get(selectedOriginId.value) ?? null) : null
  )

  function cityValue(adcode: string): number {
    const city = data.value?.cities.find((c) => c.adcode === adcode)
    if (!city) return 0
    return city.totals[metric.value]
  }

  function cityT(adcode: string): number {
    return heatT(cityValue(adcode), scaleDomain.value)
  }

  function setMetric(key: HeatMetricKey): void {
    metric.value = key
  }

  function hoverOrigin(id: string): void {
    hoveredOriginId.value = id
  }

  function hoverCitySurface(adcode: string): void {
    hoveredCityCode.value = adcode
  }

  function selectOrigin(id: string): void {
    if (selectedOriginId.value === id) {
      clearSelection()
      return
    }
    selectedOriginId.value = id
    selectedCityAdcode.value = originById.value.get(id)?.cityAdcode ?? ''
  }

  function selectCity(adcode: string): void {
    if (selectedCityAdcode.value === adcode && !selectedOriginId.value) {
      clearSelection()
      return
    }
    selectedCityAdcode.value = adcode
    selectedOriginId.value = ''
  }

  function clearSelection(): void {
    selectedOriginId.value = ''
    selectedCityAdcode.value = ''
  }

  return {
    data,
    loading,
    error,
    metric,
    metricMeta,
    scaleDomain,
    hoveredOriginId,
    hoveredCityCode,
    activeCityAdcode,
    selectedOriginId,
    selectedCityAdcode,
    selectedOrigin,
    rankedOrigins,
    originById,
    load,
    cityValue,
    cityT,
    setMetric,
    hoverOrigin,
    hoverCitySurface,
    selectOrigin,
    selectCity,
    clearSelection
  }
}

export type OriginHeatContext = ReturnType<typeof createHeatContext>

const heatKey: InjectionKey<OriginHeatContext> = Symbol('origin-heat')

export function provideHeatData(): OriginHeatContext {
  const ctx = createHeatContext()
  provide(heatKey, ctx)
  return ctx
}

export function useHeatData(): OriginHeatContext {
  const ctx = inject(heatKey)
  if (!ctx) throw new Error('useHeatData 必须在 provideHeatData 的组件树内使用')
  return ctx
}
