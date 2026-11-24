<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { orderApi } from '@/api'
import type { Order, Pagination } from '@/api/types'
import { errorText } from '@/utils/format'
import { useOrderActions } from '@/composables/useOrderActions'
import AppIcon from '@/components/AppIcon.vue'
import OrderCard from '@/components/OrderCard.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const router = useRouter()

const tabs = [
  { key: 'all', label: '全部订单' },
  { key: 'pending_payment', label: '待付款' },
  { key: 'paid', label: '待发货' },
  { key: 'shipped', label: '待收货' },
  { key: 'completed', label: '已完成' },
  { key: 'after_sale', label: '退款售后' }
]

const orders = ref<Order[]>([])
const pagination = ref<Pagination>({ page: 1, page_size: 5, total: 0, total_pages: 0 })
const activeTab = ref('all')
const loading = ref(true)
const error = ref('')

const actions = useOrderActions(load)

function normalizeTab(value: unknown): string {
  const text = String(value || 'all')
  return tabs.some((tab) => tab.key === text) ? text : 'all'
}

function updateTab(tab: string): void {
  const query = { ...route.query }
  if (tab === 'all') delete query.status
  else query.status = tab
  query.page = '1'
  router.replace({ name: 'orders', query })
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  const page = Math.max(1, Number(route.query.page) || 1)
  try {
    if (activeTab.value === 'after_sale') {
      const data = await orderApi.list({ page: 1, page_size: 100 })
      const filtered = data.items.filter((order) =>
        ['refunding', 'refunded', 'partially_refunded'].includes(order.status)
      )
      orders.value = filtered.slice(0, 20)
      pagination.value = {
        page: 1,
        page_size: 20,
        total: filtered.length,
        total_pages: filtered.length > 20 ? 1 : 1
      }
    } else {
      const data = await orderApi.list({
        status: activeTab.value === 'all' ? undefined : activeTab.value,
        page,
        page_size: 5
      })
      orders.value = data.items
      pagination.value = data.pagination
    }
  } catch (err) {
    error.value = errorText(err)
    orders.value = []
  } finally {
    loading.value = false
  }
}

function applyRoute(): void {
  activeTab.value = normalizeTab(route.query.status)
  load()
}

function pageTo(page: number): void {
  router.replace({ name: 'orders', query: { ...route.query, page: String(page) } })
}

watch(() => route.query, applyRoute, { immediate: true })
</script>

<template>
  <div class="orders-view">
    <header class="account-page-head">
      <div>
        <span class="eyebrow">MY ORDERS</span>
        <h2>我的订单</h2>
        <p>查看订单状态、物流与售后进度。</p>
      </div>
      <RouterLink to="/products" class="outline-button small">
        <AppIcon name="arrow-right" :size="15" />继续选购
      </RouterLink>
    </header>

    <nav class="order-tabs" aria-label="订单状态筛选">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="updateTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <StateBlock
      :loading="loading"
      :error="error"
      :empty="!loading && !error && !orders.length"
      empty-text="该状态下暂无订单"
      @retry="load"
    >
      <template #empty-action>
        <RouterLink to="/products" class="primary-button small">去逛逛</RouterLink>
      </template>
      <div class="order-list">
        <OrderCard
          v-for="order in orders"
          :key="order.id"
          :order="order"
          @action="actions.handle"
        />
      </div>
    </StateBlock>

    <PaginationBar
      v-if="activeTab !== 'after_sale' && !loading && !error"
      :pagination="pagination"
      @change="pageTo"
    />
  </div>
</template>
