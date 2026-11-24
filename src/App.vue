<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import SiteHeader from './components/SiteHeader.vue'
import SiteFooter from './components/SiteFooter.vue'
import ToastHost from './components/ToastHost.vue'
import ConfirmHost from './components/ConfirmHost.vue'
import AppIcon from './components/AppIcon.vue'
import { useAuthStore } from './stores/auth'
import { useCartStore } from './stores/cart'

const route = useRoute()
const auth = useAuthStore()
const cart = useCartStore()
const bare = computed(() => Boolean(route.meta.bare))

/* ---------- 返回顶部 ---------- */
const showBackTop = ref(false)
let backTopFrame = 0

function onBackTopScroll(): void {
  if (backTopFrame) return
  backTopFrame = window.requestAnimationFrame(() => {
    backTopFrame = 0
    showBackTop.value = window.scrollY > 480
  })
}

function backToTop(): void {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

/* ---------- 滚动显现（IntersectionObserver，分批次错峰入场） ---------- */
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const REVEAL_SELECTOR = [
  '.page-intro',
  '.section-heading',
  '.section-block',
  '.product-card',
  '.quick-categories',
  '.origin-card',
  '.aid-grid > *',
  '.green-product-grid > *',
  '.account-shortcuts > *',
  '.help-grid > *',
  '.quick-link-grid > *'
].join(',')

let revealObserver: IntersectionObserver | null = null
let revealTimer = 0
/* 预渲染骨架已在首屏展示完整内容；首次挂载跳过入场动画，避免「内容先出现、再被隐藏重播」的闪烁 */
let revealSkippedForShell = document.documentElement.dataset.prerender === '1'

function initReveal(): void {
  if (revealSkippedForShell) {
    revealSkippedForShell = false
    delete document.documentElement.dataset.prerender
    return
  }
  window.clearTimeout(revealTimer)
  revealTimer = window.setTimeout(() => {
    revealObserver?.disconnect()
    if (reducedMotion) return
    const candidates = Array.from(
      document.querySelectorAll<HTMLElement>(`main ${REVEAL_SELECTOR}`)
    ).filter((el) => !el.closest('.rv'))
    if (!candidates.length || !('IntersectionObserver' in window)) return
    revealObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          const el = entry.target as HTMLElement
          el.classList.add('rv-in')
          revealObserver?.unobserve(el)
        }
      },
      { rootMargin: '0px 0px 80px 0px', threshold: 0.02 }
    )
    /* 按文档顺序每 6 个一组，组内依次递增 40ms 延迟，形成错峰入场 */
    candidates.forEach((el, index) => {
      el.classList.add('rv')
      el.style.setProperty('--rv-delay', `${(index % 6) * 40}ms`)
      revealObserver?.observe(el)
    })
  }, 60)
}

watch(
  () => route.fullPath,
  () => {
    void nextTick(initReveal)
  }
)

onMounted(async () => {
  await auth.bootstrap()
  if (auth.isAuthenticated) {
    try {
      await cart.fetchCart()
    } catch {
      // 购物车错误在购物车页/提示中展示
    }
  }
  window.addEventListener('scroll', onBackTopScroll, { passive: true })
  void nextTick(initReveal)
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onBackTopScroll)
  window.cancelAnimationFrame(backTopFrame)
  window.clearTimeout(revealTimer)
  revealObserver?.disconnect()
})

watch(
  () => auth.isAuthenticated,
  async (authenticated) => {
    if (!authenticated) {
      cart.clear()
      return
    }
    try {
      await cart.fetchCart()
    } catch {
      // 忽略，页面会展示错误
    }
  }
)
</script>

<template>
  <div class="app-shell">
    <a href="#main-content" class="skip-link">跳到主要内容</a>
    <SiteHeader v-if="!bare" />
    <RouterView v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
    <SiteFooter v-if="!bare" />
    <Transition name="back-top">
      <button
        v-if="!bare && showBackTop"
        class="back-top"
        type="button"
        aria-label="返回顶部"
        @click="backToTop"
      >
        <AppIcon name="chevron-up" :size="20" />
      </button>
    </Transition>
    <ToastHost />
    <ConfirmHost />
  </div>
</template>
