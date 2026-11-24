// 甘肃产地热力数据服务层。
// 目前读取本地 mock；接入真实接口时只改本文件（保持返回结构一致），组件层零改动。

export type HeatMetricKey = 'sales' | 'aid' | 'carbon'

export interface HeatMetric {
  key: HeatMetricKey
  label: string
  unit: string
}

export interface HeatDomain {
  min: number
  max: number
  totalMax: number
}

export interface HeatMeta {
  schemaVersion: number
  isMock: boolean
  months: string[]
  metrics: HeatMetric[]
  domain: Record<HeatMetricKey, HeatDomain>
  summary: {
    originCount: number
    totals: Record<HeatMetricKey, number>
  }
}

export type HeatTotals = Record<HeatMetricKey, number>

export interface CityHeat {
  adcode: string
  name: string
  center: [number, number]
  totals: HeatTotals
  monthly: Record<HeatMetricKey, number[]>
}

export interface OriginHeat {
  id: string
  adcode: string
  cityAdcode: string
  name: string
  location: string
  productName: string
  tagline: string
  center: [number, number]
  productCount: number
  totals: HeatTotals
  monthly: Record<HeatMetricKey, number[]>
}

export interface HeatData {
  meta: HeatMeta
  cities: CityHeat[]
  origins: OriginHeat[]
}

// 与 DataV GeoAtlas 对应的 GeoJSON 类型（properties.adcode 可能是数字或字符串）
import type { Feature, FeatureCollection, Geometry } from 'geojson'

export interface GeoFeatureProps {
  adcode: number | string
  name: string
  center?: [number, number]
  centroid?: [number, number]
  [key: string]: unknown
}

export type GeoFeature = Feature<Geometry, GeoFeatureProps>
export type GeoCollection = FeatureCollection<Geometry, GeoFeatureProps>

export function featureAdcode(feature: GeoFeature): string {
  return String(feature.properties.adcode)
}

let heatPromise: Promise<HeatData> | null = null

export function getHeatData(): Promise<HeatData> {
  if (!heatPromise) {
    heatPromise = import('@/mocks/mock-origin-heat.json')
      .then((module) => module.default as unknown as HeatData)
      .catch((err) => {
        heatPromise = null
        throw err
      })
  }
  return heatPromise
}

const geoCache = new Map<string, Promise<GeoCollection>>()

// 只请求本地 public/geo/ 下的文件，运行时不访问外部地址
export function loadGeoJson(adcode: string): Promise<GeoCollection> {
  let pending = geoCache.get(adcode)
  if (!pending) {
    pending = fetch(`/geo/${adcode}_full.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`GeoJSON 加载失败：${adcode}（HTTP ${res.status}）`)
        return res.json() as Promise<GeoCollection>
      })
      .catch((err) => {
        geoCache.delete(adcode)
        throw err
      })
    geoCache.set(adcode, pending)
  }
  return pending
}
