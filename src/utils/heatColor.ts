// 热力色阶工具：低 #F6EFD2（浅米黄）→ 中 #E9B949（金黄）→ 高 #1F7A4D（品牌深绿）。
// 三色为改版规格指定，统一在此定义；CSS 侧对应 origin-map.css 的 --heat-low/mid/high。
// 色彩域固定取 meta.domain，切换月份/指标时不做逐帧归一化，避免颜色跳变。

export type RGB = [number, number, number]

export const HEAT_LOW: RGB = [246, 239, 210]
export const HEAT_MID: RGB = [233, 185, 73]
export const HEAT_HIGH: RGB = [31, 122, 77]

export interface HeatScaleDomain {
  min: number
  max: number
}

export function heatT(value: number, domain: HeatScaleDomain): number {
  const span = domain.max - domain.min
  if (span <= 0) return 0
  return Math.min(1, Math.max(0, (value - domain.min) / span))
}

function lerp(a: number, b: number, t: number): number {
  return Math.round(a + (b - a) * t)
}

function mix(a: RGB, b: RGB, t: number): RGB {
  return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)]
}

export function heatColor(t: number): RGB {
  const clamped = Math.min(1, Math.max(0, t))
  return clamped < 0.5
    ? mix(HEAT_LOW, HEAT_MID, clamped / 0.5)
    : mix(HEAT_MID, HEAT_HIGH, (clamped - 0.5) / 0.5)
}

// 悬停/选中提亮：向白色混合
export function brighten(color: RGB, amount = 0.16): RGB {
  return mix(color, [255, 255, 255], amount)
}

export function cssRgb(color: RGB): string {
  return `rgb(${color[0]}, ${color[1]}, ${color[2]})`
}
