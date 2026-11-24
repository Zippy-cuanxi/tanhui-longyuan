<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import AppIcon from './AppIcon.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const cart = useCartStore()
const keyword = ref(String(route.query.keyword || ''))
const userMenu = ref(false)

watch(
  () => route.query.keyword,
  (value) => {
    keyword.value = String(value || '')
  }
)

function search(): void {
  const text = keyword.value.trim()
  router.push({ name: 'products', query: text ? { keyword: text } : {} })
}

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
</script>

<template>
  <header class="site-header">
    <div class="header-inner">
      <RouterLink to="/" class="brand" aria-label="碳惠陇原首页">
        <img src="/assets/brand/logo.png" alt="碳惠陇原 · 甘肃特色农产品绿色电商平台" />
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
        <RouterLink to="/account/points" :class="{ active: isActive('points') }">
          绿色积分
        </RouterLink>
        <RouterLink to="/aid" :class="{ active: isActive('aid') || isActive('aid-detail') }">
          助农公益
        </RouterLink>
        <RouterLink to="/brand" :class="{ active: isActive('brand') }">关于我们</RouterLink>
      </nav>

      <div class="header-actions">
        <form class="header-search" role="search" @submit.prevent="search">
          <input
            v-model="keyword"
            type="search"
            maxlength="64"
            placeholder="搜索陇原好物"
            aria-label="搜索商品"
          />
          <button type="submit" aria-label="搜索">
            <AppIcon name="search" :size="18" />
          </button>
        </form>

        <div class="user-wrap">
          <button
            class="round-action user-action"
            type="button"
            aria-label="个人中心"
            @click="openUser"
          >
            <span v-if="auth.isAuthenticated" class="avatar-mini">{{ auth.avatarText }}</span>
            <AppIcon v-else name="user" :size="19" />
          </button>
          <div
            v-if="userMenu && auth.isAuthenticated"
            class="menu-backdrop"
            @click="userMenu = false"
          />
          <Transition name="pop">
            <div v-if="userMenu && auth.isAuthenticated" class="user-menu">
              <div class="user-menu-head">
                <span class="avatar">{{ auth.avatarText }}</span>
                <div>
                  <strong>{{ auth.displayName }}</strong>
                  <span>{{ auth.email }}</span>
                </div>
              </div>
              <RouterLink to="/account" @click="userMenu = false">个人中心</RouterLink>
              <RouterLink to="/account/orders" @click="userMenu = false">我的订单</RouterLink>
              <RouterLink to="/account/points" @click="userMenu = false">绿色积分</RouterLink>
              <RouterLink to="/account/addresses" @click="userMenu = false">收货地址</RouterLink>
              <RouterLink to="/account/notifications" @click="userMenu = false"
                >消息通知</RouterLink
              >
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
