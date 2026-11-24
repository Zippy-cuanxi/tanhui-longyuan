<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { Product } from '@/api/types'
import { money, productFallbackImage } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import { useBadgeStore } from '@/stores/badges'
import { useCartStore } from '@/stores/cart'
import AppIcon from './AppIcon.vue'
import UserAvatar from './UserAvatar.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const badges = useBadgeStore()
const cart = useCartStore()
const keyword = ref(String(route.query.keyword || ''))
const userMenu = ref(false)
const userButtonRef = ref<HTMLButtonElement | null>(null)
const searchWrap = ref<HTMLFormElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const suggestions = ref<Product[]>([])
const suggestOpen = ref(false)
const suggestLoading = ref(false)
const activeIndex = ref(-1)
const mobileExpanded = ref(false)
const recentSearches = ref<string[]>([])
const recentExpanded = ref(false)
let suggestTimer = 0
let suggestSeq = 0

const SCROLL_THRESHOLD = 50
const headerHidden = ref(false)
const headerScrolled = ref(false)
let lastScrollY = 0
let downTravel = 0
let upTravel = 0
let scrollTicking = false
let scrollFrame = 0

/* 顶栏收起/展开时同步给 <html>，供吸顶元素用 --header-offset 贴边 */
watch(headerHidden, (hidden) => {
  document.documentElement.classList.toggle('header-hidden', hidden)
})

const RECENT_SEARCH_KEY = 'tanhui_recent_searches'
const MAX_RECENT_SEARCHES = 10
const discoveryTerms: Array<{ term: string; hot?: boolean }> = [
  { term: '苹果', hot: true },
  { term: '枸杞', hot: true },
  { term: '马铃薯' },
  { term: '蜜瓜', hot: true },
  { term: '小枣' },
  { term: '百合' },
  { term: '当归' },
  { term: '杂粮' },
  { term: '文创' }
]

const activeOptionId = computed(() => {
  const item = suggestions.value[activeIndex.value]
  return item ? `header-search-option-${item.id}` : undefined
})
const recentVisible = computed(() =>
  recentExpanded.value ? recentSearches.value : recentSearches.value.slice(0, 6)
)

watch(
  () => route.query.keyword,
  (value) => {
    keyword.value = String(value || '')
    resetSuggestions()
  }
)

watch(
  () => route.fullPath,
  () => {
    mobileExpanded.value = false
    resetHeaderScroll()
    if (auth.isAuthenticated) void badges.refresh()
  }
)

watch(
  () => auth.isAuthenticated,
  (value) => {
    if (value) void badges.refresh()
    else badges.reset()
  },
  { immediate: true }
)

function resetHeaderScroll(): void {
  headerHidden.value = false
  lastScrollY = Math.max(0, window.scrollY)
  downTravel = 0
  upTravel = 0
}

function updateHeaderOnScroll(): void {
  const y = Math.max(0, window.scrollY)
  headerScrolled.value = y > 8
  if (y <= SCROLL_THRESHOLD) {
    headerHidden.value = false
    downTravel = 0
    upTravel = 0
    lastScrollY = y
    return
  }
  const delta = y - lastScrollY
  lastScrollY = y
  if (delta > 0) {
    downTravel += delta
    upTravel = 0
    if (downTravel >= SCROLL_THRESHOLD) {
      if (!headerHidden.value && !suggestOpen.value && !userMenu.value && !mobileExpanded.value) {
        headerHidden.value = true
      }
      downTravel = 0
    }
  } else if (delta < 0) {
    upTravel += -delta
    downTravel = 0
    if (upTravel >= SCROLL_THRESHOLD) {
      if (headerHidden.value) headerHidden.value = false
      upTravel = 0
    }
  }
}

function onWindowScroll(): void {
  if (scrollTicking) return
  scrollTicking = true
  scrollFrame = window.requestAnimationFrame(() => {
    scrollTicking = false
    updateHeaderOnScroll()
  })
}

function clearResults(): void {
  window.clearTimeout(suggestTimer)
  suggestSeq += 1
  suggestions.value = []
  suggestLoading.value = false
  activeIndex.value = -1
}

function resetSuggestions(): void {
  clearResults()
  suggestOpen.value = false
}

function loadRecentSearches(): void {
  try {
    const raw = window.localStorage.getItem(RECENT_SEARCH_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return
    recentSearches.value = parsed
      .filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
      .slice(0, MAX_RECENT_SEARCHES)
  } catch {
    recentSearches.value = []
  }
}

function saveRecentSearch(term: string): void {
  const text = term.trim()
  if (!text) return
  recentSearches.value = [text, ...recentSearches.value.filter((item) => item !== text)].slice(
    0,
    MAX_RECENT_SEARCHES
  )
  try {
    window.localStorage.setItem(RECENT_SEARCH_KEY, JSON.stringify(recentSearches.value))
  } catch {
    // 忽略本地存储失败
  }
}

function clearRecentSearches(): void {
  recentSearches.value = []
  recentExpanded.value = false
  try {
    window.localStorage.removeItem(RECENT_SEARCH_KEY)
  } catch {
    // 忽略本地存储失败
  }
}

function searchTerm(term: string): void {
  keyword.value = term
  activeIndex.value = -1
  search()
}

async function loadSuggestions(text: string, seq: number): Promise<void> {
  try {
    const data = await catalogApi.products({ keyword: text, page_size: 6 })
    if (seq !== suggestSeq) return
    suggestions.value = data.items
  } catch {
    if (seq !== suggestSeq) return
    suggestions.value = []
  } finally {
    if (seq === suggestSeq) suggestLoading.value = false
  }
}

function onInput(): void {
  const text = keyword.value.trim()
  window.clearTimeout(suggestTimer)
  activeIndex.value = -1
  if (!text) {
    clearResults()
    suggestOpen.value = true
    return
  }
  const seq = ++suggestSeq
  suggestions.value = []
  suggestLoading.value = true
  suggestOpen.value = true
  suggestTimer = window.setTimeout(() => {
    void loadSuggestions(text, seq)
  }, 220)
}

function onFocus(): void {
  if (keyword.value.trim()) {
    if (!suggestOpen.value) onInput()
    return
  }
  clearResults()
  suggestOpen.value = true
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    resetSuggestions()
    mobileExpanded.value = false
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
    return
  }
  if (event.key === 'Tab') {
    resetSuggestions()
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    if (!suggestOpen.value) {
      onInput()
      return
    }
    if (!suggestions.value.length) return
    activeIndex.value =
      activeIndex.value >= suggestions.value.length - 1 ? 0 : activeIndex.value + 1
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    if (!suggestions.value.length) return
    activeIndex.value =
      activeIndex.value <= 0 ? suggestions.value.length - 1 : activeIndex.value - 1
  }
}

function highlightParts(title: string): Array<{ text: string; hit: boolean }> {
  const text = keyword.value.trim()
  if (!text) return [{ text: title, hit: false }]
  const lowerTitle = title.toLowerCase()
  const lowerText = text.toLowerCase()
  const parts: Array<{ text: string; hit: boolean }> = []
  let start = 0
  let index = lowerTitle.indexOf(lowerText)
  while (index !== -1) {
    if (index > start) parts.push({ text: title.slice(start, index), hit: false })
    parts.push({ text: title.slice(index, index + text.length), hit: true })
    start = index + text.length
    index = lowerTitle.indexOf(lowerText, start)
  }
  if (start < title.length) parts.push({ text: title.slice(start), hit: false })
  return parts
}

function thumbFor(product: Product): string {
  return assetUrl(product.cover_url, productFallbackImage(product.title))
}

function onThumbError(event: Event): void {
  const img = event.target as HTMLImageElement
  const fallback = assetUrl('/images/products/jingning-apple.webp')
  if (!img.src.endsWith(fallback)) img.src = fallback
}

function search(): void {
  const picked = suggestions.value[activeIndex.value]
  if (suggestOpen.value && activeIndex.value >= 0 && picked) keyword.value = picked.title
  const text = keyword.value.trim()
  if (text) saveRecentSearch(text)
  resetSuggestions()
  mobileExpanded.value = false
  router.push({ name: 'products', query: text ? { keyword: text } : {} })
}

function chooseSuggestion(product: Product): void {
  keyword.value = product.title
  activeIndex.value = -1
  search()
}

function onSearchButtonClick(event: MouseEvent): void {
  if (window.matchMedia('(max-width: 640px)').matches && !mobileExpanded.value) {
    event.preventDefault()
    mobileExpanded.value = true
    void nextTick(() => inputRef.value?.focus())
  }
}

function handleDocumentPointerDown(event: PointerEvent): void {
  if (!searchWrap.value?.contains(event.target as Node)) {
    resetSuggestions()
    mobileExpanded.value = false
  }
}

let badgeTimer = 0

function handleWindowFocus(): void {
  if (auth.isAuthenticated) void badges.refresh()
}

onMounted(() => {
  loadRecentSearches()
  lastScrollY = Math.max(0, window.scrollY)
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  window.addEventListener('focus', handleWindowFocus)
  window.addEventListener('scroll', onWindowScroll, { passive: true })
  badgeTimer = window.setInterval(() => {
    if (auth.isAuthenticated) void badges.refresh()
  }, 60000)
})
onBeforeUnmount(() => {
  document.documentElement.classList.remove('header-hidden')
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
  window.removeEventListener('focus', handleWindowFocus)
  window.removeEventListener('scroll', onWindowScroll)
  window.cancelAnimationFrame(scrollFrame)
  window.clearInterval(badgeTimer)
})

function requireLogin(): void {
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}

function openUser(): void {
  if (!auth.isAuthenticated) {
    requireLogin()
    return
  }
  userMenu.value = !userMenu.value
}

/* Escape 关闭用户菜单并把焦点还给触发按钮 */
function closeUserMenu(): void {
  if (!userMenu.value) return
  userMenu.value = false
  userButtonRef.value?.focus()
}

function openCart(): void {
  if (!auth.isAuthenticated) {
    requireLogin()
    return
  }
  router.push({ name: 'cart' })
}

async function logout(): Promise<void> {
  userMenu.value = false
  await auth.logout()
  cart.clear()
  router.push({ name: 'home' })
}

function isActive(name: string): boolean {
  return route.name === name
}

function badgeText(count: number): string {
  return count > 99 ? '+99' : String(count)
}
</script>

<template>
  <header
    class="site-header"
    :class="{ 'header-hidden': headerHidden, 'header-scrolled': headerScrolled }"
  >
    <div class="header-inner">
      <RouterLink to="/" class="brand" aria-label="碳惠陇原首页">
        <img
          :src="assetUrl('/images/logo/logo.webp')"
          alt="碳惠陇原 · 甘肃特色农产品绿色电商平台"
          width="420"
          height="163"
          decoding="async"
        />
      </RouterLink>

      <nav class="main-nav" aria-label="主导航">
        <RouterLink to="/" :class="{ active: isActive('home') }">首页</RouterLink>
        <RouterLink
          to="/products"
          :class="{ active: isActive('products') || isActive('product-detail') }"
        >
          全部商品
        </RouterLink>
        <RouterLink to="/origin" :class="{ active: isActive('origin') }">甘肃产地</RouterLink>
        <RouterLink to="/green" :class="{ active: isActive('green') }">绿色消费专区</RouterLink>
        <RouterLink to="/aid" :class="{ active: isActive('aid') || isActive('aid-detail') }">
          助农公益
        </RouterLink>
        <RouterLink to="/join" :class="{ active: isActive('merchant-join') }">
          商家入驻
        </RouterLink>
        <RouterLink to="/account" :class="{ active: route.path.startsWith('/account') }">
          个人中心
        </RouterLink>
      </nav>

      <div class="header-actions">
        <form
          ref="searchWrap"
          class="header-search"
          :class="{ expanded: mobileExpanded, suggesting: suggestOpen }"
          role="search"
          @submit.prevent="search"
        >
          <input
            ref="inputRef"
            v-model="keyword"
            type="search"
            maxlength="64"
            placeholder="搜索陇原好物"
            aria-label="搜索商品"
            role="combobox"
            aria-autocomplete="list"
            aria-controls="header-search-suggestions"
            :aria-expanded="suggestOpen"
            :aria-activedescendant="activeOptionId"
            autocomplete="off"
            @input="onInput"
            @focus="onFocus"
            @keydown="onKeydown"
          />
          <button type="submit" aria-label="搜索" @click="onSearchButtonClick">
            <AppIcon name="search" :size="18" />
          </button>

          <Transition name="pop">
            <div
              v-if="suggestOpen"
              id="header-search-suggestions"
              class="search-suggestions"
              :role="keyword.trim() ? 'listbox' : 'dialog'"
              :aria-label="keyword.trim() ? '商品搜索建议' : '搜索推荐'"
            >
              <template v-if="keyword.trim()">
                <p v-if="suggestLoading" class="suggest-status">
                  <span class="mini-spinner dark" />正在匹配商品…
                </p>
                <template v-else-if="suggestions.length">
                  <button
                    v-for="(item, index) in suggestions"
                    :id="`header-search-option-${item.id}`"
                    :key="item.id"
                    type="button"
                    class="suggest-item"
                    :class="{ active: index === activeIndex }"
                    role="option"
                    :aria-selected="index === activeIndex"
                    @mouseenter="activeIndex = index"
                    @click="chooseSuggestion(item)"
                  >
                    <img
                      :src="thumbFor(item)"
                      :alt="item.title"
                      loading="lazy"
                      @error="onThumbError"
                    />
                    <span class="suggest-name">
                      <template
                        v-for="(part, partIndex) in highlightParts(item.title)"
                        :key="partIndex"
                      >
                        <mark v-if="part.hit">{{ part.text }}</mark>
                        <template v-else>{{ part.text }}</template>
                      </template>
                    </span>
                    <span class="suggest-price">¥{{ money(item.min_price) }}</span>
                  </button>
                  <button type="button" class="suggest-all" @click="search">
                    <span class="suggest-all-text">搜索“{{ keyword.trim() }}”查看全部结果</span>
                    <AppIcon name="arrow-right" :size="13" />
                  </button>
                </template>
                <p v-else class="suggest-status">没有匹配的商品，换个关键词试试</p>
              </template>

              <template v-else>
                <section v-if="recentSearches.length" class="search-section">
                  <header class="search-section-head">
                    <span class="search-section-title">
                      <AppIcon name="clock" :size="13" />最近搜索
                    </span>
                    <button
                      type="button"
                      class="search-clear"
                      aria-label="清空最近搜索"
                      @click="clearRecentSearches"
                    >
                      <AppIcon name="trash" :size="14" />
                    </button>
                  </header>
                  <div class="search-chips">
                    <button
                      v-for="term in recentVisible"
                      :key="term"
                      type="button"
                      class="search-chip"
                      @click="searchTerm(term)"
                    >
                      {{ term }}
                    </button>
                    <button
                      v-if="recentSearches.length > 6"
                      type="button"
                      class="search-more"
                      @click="recentExpanded = !recentExpanded"
                    >
                      {{ recentExpanded ? '收起' : '更多' }}
                      <AppIcon :name="recentExpanded ? 'chevron-up' : 'chevron-down'" :size="12" />
                    </button>
                  </div>
                </section>

                <section class="search-section">
                  <header class="search-section-head">
                    <span class="search-section-title">
                      <AppIcon name="sparkle" :size="13" />搜索发现
                    </span>
                  </header>
                  <div class="search-chips">
                    <button
                      v-for="item in discoveryTerms"
                      :key="item.term"
                      type="button"
                      class="search-chip"
                      @click="searchTerm(item.term)"
                    >
                      {{ item.term }}
                      <em v-if="item.hot" class="search-hot">热</em>
                    </button>
                  </div>
                </section>
              </template>
            </div>
          </Transition>
        </form>

        <div class="user-wrap" @keydown.esc="closeUserMenu">
          <button
            ref="userButtonRef"
            class="round-action user-action"
            type="button"
            aria-label="个人中心"
            :aria-expanded="userMenu && auth.isAuthenticated"
            @click="openUser"
          >
            <UserAvatar
              v-if="auth.isAuthenticated"
              :url="auth.avatarUrl"
              :text="auth.avatarText"
              :size="36"
            />
            <AppIcon v-else name="user" :size="19" />
            <span v-if="auth.isAuthenticated && badges.total" class="user-badge">
              {{ badgeText(badges.total) }}
            </span>
          </button>
          <div
            v-if="userMenu && auth.isAuthenticated"
            class="menu-backdrop"
            @click="userMenu = false"
          />
          <Transition name="pop">
            <div v-if="userMenu && auth.isAuthenticated" class="user-menu">
              <div class="user-menu-head">
                <UserAvatar :url="auth.avatarUrl" :text="auth.avatarText" :size="38" />
                <div>
                  <strong>{{ auth.displayName }}</strong>
                  <span>{{ auth.email }}</span>
                </div>
              </div>
              <RouterLink to="/account" @click="userMenu = false">个人中心</RouterLink>
              <RouterLink to="/account/orders" @click="userMenu = false">
                我的订单
                <span v-if="badges.orderUpdates" class="menu-badge">
                  {{ badgeText(badges.orderUpdates) }}
                </span>
              </RouterLink>
              <RouterLink to="/account/points" @click="userMenu = false">
                绿色积分
                <span v-if="badges.pointUpdates" class="menu-badge">
                  {{ badgeText(badges.pointUpdates) }}
                </span>
              </RouterLink>
              <RouterLink to="/account/addresses" @click="userMenu = false">收货地址</RouterLink>
              <RouterLink to="/account/notifications" @click="userMenu = false">
                消息通知
                <span v-if="badges.unreadNotifications" class="menu-badge">
                  {{ badgeText(badges.unreadNotifications) }}
                </span>
              </RouterLink>
              <button type="button" class="logout-link" @click="logout">
                <AppIcon name="logout" :size="15" />退出登录
              </button>
            </div>
          </Transition>
        </div>

        <button
          class="round-action cart-action"
          type="button"
          aria-label="购物车"
          @click="openCart"
        >
          <AppIcon name="cart" :size="19" />
          <span v-if="cart.count" class="cart-count">{{
            cart.count > 99 ? '99+' : cart.count
          }}</span>
        </button>
      </div>
    </div>
  </header>
</template>
