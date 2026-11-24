<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { aidApi, orderApi } from '@/api'
import type { AidDonation, Order } from '@/api/types'
import { errorText, formatDateTime, money } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import { usePointsStore } from '@/stores/points'
import { useOrderActions } from '@/composables/useOrderActions'
import AppIcon from '@/components/AppIcon.vue'
import OrderCard from '@/components/OrderCard.vue'
import StateBlock from '@/components/StateBlock.vue'

const auth = useAuthStore()
const points = usePointsStore()
const recentOrders = ref<Order[]>([])
const donations = ref<AidDonation[]>([])
const loading = ref(true)
const error = ref('')
const donationsLoading = ref(true)
const donationsError = ref('')
const counts = reactive<Record<string, number>>({
  pending_payment: 0,
  paid: 0,
  shipped: 0,
  completed: 0,
  refunding: 0
})

const statusShortcuts = [
  { status: 'pending_payment', label: '待付款', icon: 'card', hint: '待完成支付' },
  { status: 'paid', label: '待发货', icon: 'package', hint: '商家准备中' },
  { status: 'shipped', label: '待收货', icon: 'truck', hint: '包裹在路上' },
  { status: 'completed', label: '已完成', icon: 'check', hint: '交易完成' },
  { status: 'refunding', label: '退款售后', icon: 'refresh', hint: '退款处理中' }
]

const quickLinks = [
  { to: '/account/points', label: '绿色积分', icon: 'leaf', desc: '查看积分与兑换' },
  { to: '/account/addresses', label: '收货地址', icon: 'location', desc: '管理常用地址' },
  { to: '/aid', label: '助农项目', icon: 'heart', desc: '每一单都是助农力量' },
  { to: '/help', label: '帮助中心', icon: 'info', desc: '下单与售后说明' }
]

const actions = useOrderActions(load)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  points.fetchBalance()
  try {
    const statuses = ['pending_payment', 'paid', 'shipped', 'completed', 'refunding']
    const [recent, ...statusResults] = await Promise.all([
      orderApi.list({ page: 1, page_size: 3 }),
      ...statuses.map((status) => orderApi.list({ status, page: 1, page_size: 1 }))
    ])
    recentOrders.value = recent.items
    statuses.forEach((status, index) => {
      counts[status] = statusResults[index]?.pagination.total || 0
    })
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

async function loadDonations(): Promise<void> {
  donationsLoading.value = true
  donationsError.value = ''
  try {
    donations.value = await aidApi.myDonations()
  } catch (err) {
    donationsError.value = errorText(err)
    donations.value = []
  } finally {
    donationsLoading.value = false
  }
}

onMounted(() => {
  load()
  loadDonations()
})
</script>

<template>
  <div class="account-home">
    <section class="account-welcome">
      <div>
        <span class="eyebrow">MY TANHUI</span>
        <h2>你好，{{ auth.displayName }}</h2>
        <p>欢迎回到碳惠陇原。这里可以查看订单、绿色积分与收货地址。</p>
      </div>
      <RouterLink to="/account/points" class="welcome-points">
        <span><AppIcon name="leaf" :size="20" />绿色积分</span>
        <strong>{{ points.balance === null ? '—' : points.balance }}</strong>
        <small>绿色积分</small>
      </RouterLink>
    </section>

    <section class="account-shortcuts">
      <RouterLink
        v-for="shortcut in statusShortcuts"
        :key="shortcut.status"
        :to="`/account/orders?status=${shortcut.status}`"
        class="shortcut-card"
      >
        <span class="shortcut-icon"><AppIcon :name="shortcut.icon" :size="21" /></span>
        <div>
          <strong>{{ counts[shortcut.status] }}</strong>
          <span>{{ shortcut.label }}</span>
        </div>
        <small>{{ shortcut.hint }}</small>
      </RouterLink>
    </section>

    <section class="account-section">
      <header class="section-heading">
        <h2>最近订单</h2>
        <RouterLink to="/account/orders" class="more-link"
          >查看全部 <AppIcon name="chevron-right" :size="14"
        /></RouterLink>
      </header>
      <StateBlock :loading="loading" :error="error" @retry="load">
        <div v-if="recentOrders.length" class="order-list">
          <OrderCard
            v-for="order in recentOrders"
            :key="order.id"
            :order="order"
            compact
            @action="actions.handle"
          />
        </div>
        <div v-else class="empty-inline">
          <span><AppIcon name="package" :size="30" /></span>
          <p>还没有订单，去挑选几件陇原好物吧。</p>
          <RouterLink to="/products" class="outline-button small">去逛逛</RouterLink>
        </div>
      </StateBlock>
    </section>

    <section class="account-section">
      <header class="section-heading">
        <h2>我的资助记录</h2>
        <RouterLink to="/aid" class="more-link">
          去支持助农 <AppIcon name="chevron-right" :size="14" />
        </RouterLink>
      </header>
      <StateBlock
        :loading="donationsLoading"
        :error="donationsError"
        :empty="!donationsLoading && !donationsError && !donations.length"
        empty-text="暂无资助记录"
        @retry="loadDonations"
      >
        <ul class="aid-record-list">
          <li v-for="donation in donations" :key="donation.id">
            <span class="aid-record-icon"><AppIcon name="heart" :size="18" /></span>
            <div class="aid-record-main">
              <strong>{{ donation.project_title || '助农项目' }}</strong>
              <span>
                {{ formatDateTime(donation.created_at) }} ·
                {{ donation.display_mode === 'anonymous' ? '匿名资助' : '实名资助' }}
              </span>
            </div>
            <div class="aid-record-value">
              <em>¥{{ money(donation.amount) }}</em>
              <small>+{{ donation.points_earned }} 绿色积分</small>
            </div>
            <RouterLink :to="`/aid/${donation.project_id}`" class="aid-record-link">
              查看项目
            </RouterLink>
          </li>
        </ul>
      </StateBlock>
    </section>

    <section class="account-section">
      <header class="section-heading"><h2>快捷入口</h2></header>
      <div class="quick-link-grid">
        <RouterLink v-for="link in quickLinks" :key="link.to" :to="link.to" class="quick-link-card">
          <span class="quick-link-icon"><AppIcon :name="link.icon" :size="21" /></span>
          <div>
            <strong>{{ link.label }}</strong>
            <span>{{ link.desc }}</span>
          </div>
          <AppIcon name="chevron-right" :size="15" />
        </RouterLink>
      </div>
    </section>
  </div>
</template>
