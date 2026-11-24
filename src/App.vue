<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import SiteHeader from './components/SiteHeader.vue'
import SiteFooter from './components/SiteFooter.vue'
import ToastHost from './components/ToastHost.vue'
import ConfirmHost from './components/ConfirmHost.vue'
import { useAuthStore } from './stores/auth'
import { useCartStore } from './stores/cart'

const route = useRoute()
const auth = useAuthStore()
const cart = useCartStore()
const bare = computed(() => Boolean(route.meta.bare))

onMounted(async () => {
  await auth.bootstrap()
  if (auth.isAuthenticated) {
    try {
      await cart.fetchCart()
    } catch {
      // 购物车错误在购物车页/提示中展示
    }
  }
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
    <ToastHost />
    <ConfirmHost />
  </div>
</template>
