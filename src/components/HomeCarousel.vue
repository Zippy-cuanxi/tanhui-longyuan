<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'

interface CarouselSlide {
  key: string
  label: string
  image: string
  to: string
  alt: string
}

const props = withDefaults(
  defineProps<{
    slides: CarouselSlide[]
    interval?: number
  }>(),
  { interval: 5000 }
)

const current = ref(0)
const paused = ref(false)
let timer = 0
let remaining = props.interval
let startedAt = 0

function clearTimer(): void {
  window.clearTimeout(timer)
  timer = 0
}

function schedule(ms: number): void {
  clearTimer()
  if (paused.value || document.hidden || !props.slides.length) return
  remaining = Math.max(0, ms)
  startedAt = performance.now()
  timer = window.setTimeout(advance, remaining)
}

function advance(): void {
  if (!props.slides.length) return
  current.value = (current.value + 1) % props.slides.length
  remaining = props.interval
  schedule(remaining)
}

function goToSlide(index: number): void {
  if (!props.slides.length) return
  current.value = (index + props.slides.length) % props.slides.length
  remaining = props.interval
  schedule(remaining)
}

function previousSlide(): void {
  goToSlide(current.value - 1)
}

function nextSlide(): void {
  goToSlide(current.value + 1)
}

function pauseAutoplay(): void {
  if (paused.value) return
  paused.value = true
  if (timer) {
    remaining = Math.max(0, remaining - (performance.now() - startedAt))
    clearTimer()
  }
}

function resumeAutoplay(): void {
  if (!paused.value) return
  paused.value = false
  schedule(remaining)
}

function handleVisibilityChange(): void {
  if (document.hidden) {
    pauseAutoplay()
    return
  }
  if (paused.value) resumeAutoplay()
  else schedule(remaining)
}

watch(
  () => props.slides,
  () => {
    current.value = 0
    remaining = props.interval
    schedule(remaining)
  },
  { deep: true }
)

onMounted(() => {
  schedule(remaining)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  clearTimer()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <section
    class="home-carousel"
    role="region"
    aria-roledescription="carousel"
    aria-label="首页栏目推荐"
    @mouseenter="pauseAutoplay"
    @mouseleave="resumeAutoplay"
  >
    <RouterLink
      v-for="(slide, index) in slides"
      :key="slide.key"
      :to="slide.to"
      class="home-carousel-slide"
      :class="{ active: index === current }"
      :aria-hidden="index !== current"
      :tabindex="index === current ? 0 : -1"
    >
      <img
        :src="slide.image"
        :alt="slide.alt"
        :loading="index === 0 ? 'eager' : 'lazy'"
        decoding="async"
      />
    </RouterLink>

    <button
      type="button"
      class="home-carousel-arrow prev"
      aria-label="上一张"
      @click.stop="previousSlide"
    >
      <AppIcon name="chevron-left" :size="20" />
    </button>
    <button
      type="button"
      class="home-carousel-arrow next"
      aria-label="下一张"
      @click.stop="nextSlide"
    >
      <AppIcon name="chevron-right" :size="20" />
    </button>

    <div class="home-carousel-meta">
      <div class="home-carousel-dots" role="tablist" aria-label="切换轮播图">
        <button
          v-for="(slide, index) in slides"
          :key="slide.key"
          type="button"
          role="tab"
          :class="{ active: index === current }"
          :aria-selected="index === current"
          :aria-label="`第 ${index + 1} 张：${slide.label}`"
          @click.stop="goToSlide(index)"
        />
      </div>
      <span
        class="home-carousel-count"
        aria-live="polite"
        :aria-label="`当前第 ${current + 1} 张，共 ${slides.length} 张`"
      >
        {{ current + 1 }} / {{ slides.length }}
      </span>
    </div>
  </section>
</template>
