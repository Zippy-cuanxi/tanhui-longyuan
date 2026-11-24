<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { pointsApi } from '@/api'
import type { Pagination, PointTransaction, Redemption, RedeemResult } from '@/api/types'
import { errorText, formatDateTime, pointTypeLabel } from '@/utils/format'
import { usePointsStore } from '@/stores/points'
import { useConfirmStore } from '@/stores/confirm'
import { useToastStore } from '@/stores/toast'
import AppIcon from '@/components/AppIcon.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import StateBlock from '@/components/StateBlock.vue'

const points = usePointsStore()
const confirm = useConfirmStore()
const toast = useToastStore()

const transactions = ref<PointTransaction[]>([])
const pagination = ref<Pagination>({ page: 1, page_size: 8, total: 0, total_pages: 0 })
const catalog = ref<Redemption[]>([])
const loading = ref(true)
const error = ref('')
const transactionsLoading = ref(false)
const catalogLoading = ref(true)
const filter = ref('all')
const redeeming = ref('')
const voucher = ref<RedeemResult | null>(null)

const filters = [
  { key: 'all', label: '全部' },
  { key: 'earn', label: '获得' },
  { key: 'spend', label: '消费' },
  { key: 'reverse', label: '冲正' },
  { key: 'adjust', label: '调整' }
]

async function loadTransactions(page = 1): Promise<void> {
  transactionsLoading.value = true
  try {
    const data = await pointsApi.transactions({
      type_: filter.value === 'all' ? undefined : filter.value,
      page,
      page_size: 8
    })
    transactions.value = data.items
    pagination.value = data.pagination
  } catch (err) {
    if (page === 1) error.value = errorText(err)
  } finally {
    transactionsLoading.value = false
  }
}

async function loadCatalog(): Promise<void> {
  catalogLoading.value = true
  try {
    catalog.value = await pointsApi.catalog()
  } catch {
    catalog.value = []
  } finally {
    catalogLoading.value = false
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  await Promise.all([points.fetchBalance(), loadTransactions(1), loadCatalog()])
  loading.value = false
}

function setFilter(key: string): void {
  filter.value = key
  loadTransactions(1)
}

function pageTo(page: number): void {
  loadTransactions(page)
}

async function redeem(item: Redemption): Promise<void> {
  const ok = await confirm.ask({
    title: '兑换权益',
    message: `确认使用 ${item.points} 绿豆兑换「${item.name}」吗？兑换权益为 Mock 演示。`,
    confirmText: '确认兑换'
  })
  if (!ok) return
  redeeming.value = item.reward_code
  try {
    const result = await pointsApi.redeem(item.reward_code)
    voucher.value = result
    toast.show('兑换成功', 'success')
    await points.fetchBalance()
    await loadTransactions(1)
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  } finally {
    redeeming.value = ''
  }
}

onMounted(load)
</script>

<template>
  <div class="points-view">
    <header class="account-page-head">
      <div>
        <span class="eyebrow">GREEN POINTS</span>
        <h2>绿色积分</h2>
        <p>绿豆为平台内部激励，不等同于碳信用或现金。</p>
      </div>
      <RouterLink to="/green" class="outline-button small">
        <AppIcon name="leaf" :size="15" />绿色消费专区
      </RouterLink>
    </header>

    <section class="points-hero">
      <div>
        <span class="eyebrow">MY BALANCE</span>
        <p>当前绿色积分</p>
        <strong>{{ points.balance === null ? '—' : points.balance }}<small> 绿豆</small></strong>
        <p class="points-hero-note">积分获取、抵扣与有效期规则以平台配置为准。</p>
      </div>
      <span class="points-hero-icon"><AppIcon name="leaf" :size="64" /></span>
    </section>

    <section class="account-section">
      <header class="section-heading">
        <h2>积分兑换</h2>
        <span class="muted-text">兑换权益为 Mock 演示</span>
      </header>
      <StateBlock
        :loading="catalogLoading"
        :empty="!catalogLoading && !catalog.length"
        empty-text="暂无可兑换权益"
      >
        <div class="redemption-grid">
          <article v-for="item in catalog" :key="item.reward_code" class="redemption-card">
            <span class="redemption-icon"><AppIcon name="gift" :size="22" /></span>
            <div>
              <strong>{{ item.name }}</strong>
              <span>{{ item.points }} 绿豆</span>
              <em v-if="item.mock">Mock 权益</em>
            </div>
            <button
              type="button"
              class="outline-button small"
              :disabled="redeeming === item.reward_code"
              @click="redeem(item)"
            >
              {{ redeeming === item.reward_code ? '兑换中…' : '兑换' }}
            </button>
          </article>
        </div>
      </StateBlock>
    </section>

    <section class="account-section">
      <header class="section-heading">
        <h2>积分流水</h2>
        <RouterLink to="/help" class="more-link"
          >规则说明 <AppIcon name="chevron-right" :size="13"
        /></RouterLink>
      </header>
      <nav class="filter-tabs" aria-label="积分流水筛选">
        <button
          v-for="item in filters"
          :key="item.key"
          type="button"
          :class="{ active: filter === item.key }"
          @click="setFilter(item.key)"
        >
          {{ item.label }}
        </button>
      </nav>

      <StateBlock
        :loading="transactionsLoading && !transactions.length"
        :error="error"
        :empty="!transactionsLoading && !error && !transactions.length"
        empty-text="暂无积分流水"
        @retry="loadTransactions(1)"
      >
        <ul class="transaction-list">
          <li v-for="txn in transactions" :key="txn.id">
            <span class="transaction-icon" :class="txn.amount >= 0 ? 'plus' : 'minus'">
              <AppIcon :name="txn.amount >= 0 ? 'plus' : 'minus'" :size="16" />
            </span>
            <div>
              <strong>{{ pointTypeLabel(txn.type) }} · {{ txn.note || '绿色积分变动' }}</strong>
              <span>{{ formatDateTime(txn.created_at) }} · 余额 {{ txn.balance_after }}</span>
            </div>
            <strong class="transaction-amount" :class="{ positive: txn.amount >= 0 }">
              {{ txn.amount >= 0 ? '+' : '' }}{{ txn.amount }}
            </strong>
          </li>
        </ul>
      </StateBlock>
      <PaginationBar :pagination="pagination" @change="pageTo" />
    </section>

    <Teleport to="body">
      <Transition name="modal">
        <div v-if="voucher" class="modal-mask" @click.self="voucher = null">
          <div
            class="modal-card voucher-modal"
            role="dialog"
            aria-modal="true"
            aria-label="兑换成功"
          >
            <span class="payment-result-icon"><AppIcon name="gift" :size="28" /></span>
            <span class="eyebrow">REDEEMED</span>
            <h2>兑换成功</h2>
            <p>{{ voucher.reward_name }}</p>
            <div class="voucher-code">{{ voucher.voucher_code }}</div>
            <p class="muted-text">消耗 {{ voucher.points_spent }} 绿豆 · Mock 凭证码，仅用于演示</p>
            <button type="button" class="primary-button full-button" @click="voucher = null">
              知道了
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
