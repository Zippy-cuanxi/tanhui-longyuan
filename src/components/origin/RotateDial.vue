<script setup lang="ts">
// 镜头旋转轮盘：按住盘面绕圆心拖动，指针跟随手指/鼠标实时转动；
// 不拖动直接点按 = 缓动回正；键盘 ← / → 每次 ±6°，Home 回正。
import { ref } from 'vue'

const props = defineProps<{ bearing: number }>()
const emit = defineEmits<{ rotate: [number]; reset: [] }>()

const dial = ref<HTMLButtonElement | null>(null)
let drag: { last: number; accum: number; moved: boolean; startBearing: number } | null = null

function angleAt(clientX: number, clientY: number): number {
  const el = dial.value
  if (!el) return 0
  const rect = el.getBoundingClientRect()
  const dx = clientX - (rect.left + rect.width / 2)
  const dy = clientY - (rect.top + rect.height / 2)
  return (Math.atan2(dy, dx) * 180) / Math.PI
}

function normalizeDelta(delta: number): number {
  if (delta > 180) return delta - 360
  if (delta < -180) return delta + 360
  return delta
}

function onDown(event: PointerEvent): void {
  drag = {
    last: angleAt(event.clientX, event.clientY),
    accum: 0,
    moved: false,
    startBearing: props.bearing
  }
  dial.value?.setPointerCapture(event.pointerId)
}

function onMove(event: PointerEvent): void {
  if (!drag) return
  const current = angleAt(event.clientX, event.clientY)
  drag.accum += normalizeDelta(current - drag.last)
  drag.last = current
  // 小于 3° 视为抖动，避免误触后指针乱跳
  if (!drag.moved && Math.abs(drag.accum) < 3) return
  drag.moved = true
  // 单次拖动限制 ±180°，绕圈时不会与地图脱节
  drag.accum = Math.max(-180, Math.min(180, drag.accum))
  emit('rotate', drag.startBearing + drag.accum)
}

function onUp(): void {
  if (drag && !drag.moved) emit('reset')
  drag = null
}

function onKey(event: KeyboardEvent): void {
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    emit('rotate', props.bearing - 6)
  } else if (event.key === 'ArrowRight') {
    event.preventDefault()
    emit('rotate', props.bearing + 6)
  } else if (event.key === 'Home' || event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    emit('reset')
  }
}
</script>

<template>
  <button
    ref="dial"
    type="button"
    class="rotate-dial"
    role="slider"
    aria-label="按住拖动旋转视角，点按回正，方向键微调"
    title="按住拖动旋转视角，点按回正"
    aria-valuemin="-180"
    aria-valuemax="180"
    :aria-valuenow="Math.round(bearing)"
    @pointerdown="onDown"
    @pointermove="onMove"
    @pointerup="onUp"
    @pointercancel="onUp"
    @keydown="onKey"
  >
    <span class="dial-ring" aria-hidden="true"></span>
    <span class="dial-needle" :style="{ transform: `rotate(${-bearing}deg)` }" aria-hidden="true">
      <i class="dial-tip"></i>
      <i class="dial-tail"></i>
    </span>
    <span class="dial-hub" aria-hidden="true"></span>
    <span class="dial-label" aria-hidden="true">N</span>
  </button>
</template>
