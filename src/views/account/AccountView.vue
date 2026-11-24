<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { usePointsStore } from '@/stores/points'
import AppIcon from '@/components/AppIcon.vue'
import UserAvatar from '@/components/UserAvatar.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const cart = useCartStore()
const points = usePointsStore()

const navItems = [
  { name: 'account', label: '概览', icon: 'home', to: '/account' },
  { name: 'orders', label: '我的订单', icon: 'package', to: '/account/orders' },
  { name: 'points', label: '绿色积分', icon: 'leaf', to: '/account/points' },
  { name: 'addresses', label: '收货地址', icon: 'location', to: '/account/addresses' },
  { name: 'profile', label: '个人资料', icon: 'user', to: '/account/profile' },
  { name: 'notifications', label: '消息通知', icon: 'bell', to: '/account/notifications' }
]

function isActive(name: string): boolean {
  if (name === 'orders') {
    return ['orders', 'order-detail', 'order-logistics', 'order-refund'].includes(
      String(route.name)
    )
  }
  return route.name === name
}

async function logout(): Promise<void> {
  await auth.logout()
  cart.clear()
  points.clear()
  router.push({ name: 'home' })
}

onMounted(() => {
  points.fetchBalance()
})
</script>

<template>
  <main class="page-main account-page">
    <div class="page-container account-layout">
      <aside class="account-sidebar">
        <section class="account-profile">
          <UserAvatar :url="auth.avatarUrl" :text="auth.avatarText" :size="58" />
          <div>
            <span class="eyebrow">MEMBER</span>
            <h1>{{ auth.displayName }}</h1>
            <p>{{ auth.email }}</p>
          </div>
          <RouterLink to="/account/profile" class="profile-edit">
            <AppIcon name="edit" :size="14" />编辑资料
          </RouterLink>
        </section>

        <RouterLink to="/account/points" class="account-points-card">
          <span class="points-leaf"><AppIcon name="leaf" :size="24" /></span>
          <div>
            <span>绿色积分</span>
            <strong>{{ points.balance === null ? '—' : points.balance }}</strong>
          </div>
          <AppIcon name="chevron-right" :size="16" />
        </RouterLink>

        <nav class="account-nav" aria-label="个人中心导航">
          <RouterLink
            v-for="item in navItems"
            :key="item.name"
            :to="item.to"
            :class="{ active: isActive(item.name) }"
          >
            <AppIcon :name="item.icon" :size="18" />
            <span>{{ item.label }}</span>
            <AppIcon name="chevron-right" :size="13" class="nav-chevron" />
          </RouterLink>
        </nav>

        <button type="button" class="account-logout" @click="logout">
          <AppIcon name="logout" :size="16" />退出登录
        </button>
      </aside>

      <section class="account-content">
        <RouterView />
      </section>
    </div>
  </main>
</template>
