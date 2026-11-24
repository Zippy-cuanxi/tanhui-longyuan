<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { orderApi } from '@/api'
import type { Order, Refund, StoreOrder } from '@/api/types'
import { errorText, formatDateTime, money, refundStatusLabel } from '@/utils/format'
import { useToastStore } from '@/stores/toast'
import AppIcon from '@/components/AppIcon.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const toast = useToastStore()
const orderId = computed(() => String(route.params.id))

const order = ref<Order | null>(null)
const refunds = ref<Refund[]>([])
const loading = ref(true)
const error = ref('')
const selectedStoreOrderId = ref('')
const amount = ref('')
const reason = ref('')
const submitting = ref(false)
const submitError = ref('')
const successRefund = ref<Refund | null>(null)

const eligibleStoreOrders = computed(() =>
  (order.value?.store_orders || []).filter(
    (store) =>
      ['paid', 'shipped', 'completed', 'partially_refunded'].includes(store.status) &&
      Number(store.pay_amount) - Number(store.refund_amount) > 0
  )
)
const selectedStoreOrder = computed(
  () => eligibleStoreOrders.value.find((store) => store.id === selectedStoreOrderId.value) || null
)

function refundableOf(store: StoreOrder): string {
  return Math.max(0, Number(store.pay_amount) - Number(store.refund_amount)).toFixed(2)
}

function selectStore(store: StoreOrder): void {
  selectedStoreOrderId.value = store.id
  amount.value = refundableOf(store)
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [detailResult, refundResult] = await Promise.allSettled([
      orderApi.detail(orderId.value),
      orderApi.refunds(orderId.value)
    ])
    if (detailResult.status === 'rejected') throw detailResult.reason
    order.value = detailResult.value
    refunds.value = refundResult.status === 'fulfilled' ? refundResult.value : []
    if (!selectedStoreOrderId.value && eligibleStoreOrders.value.length) {
      selectStore(eligibleStoreOrders.value[0])
    } else if (selectedStoreOrder.value) {
      amount.value = refundableOf(selectedStoreOrder.value)
    }
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

async function submit(): Promise<void> {
  submitError.value = ''
  successRefund.value = null
  if (!selectedStoreOrder.value) {
    submitError.value = '请选择需要退款的店铺订单'
    return
  }
  if (!reason.value.trim()) {
    submitError.value = '请填写退款原因'
    return
  }
  const value = Number(amount.value)
  const refundable = Number(refundableOf(selectedStoreOrder.value))
  if (!Number.isFinite(value) || value <= 0) {
    submitError.value = '请填写有效的退款金额'
    return
  }
  if (value > refundable) {
    submitError.value = `退款金额不能超过可退金额 ¥${refundable.toFixed(2)}`
    return
  }
  submitting.value = true
  try {
    const refund = await orderApi.requestRefund(orderId.value, {
      reason: reason.value.trim(),
      amount: value.toFixed(2),
      store_order_id: selectedStoreOrder.value.id
    })
    successRefund.value = refund
    toast.show('退款申请已提交', 'success')
    reason.value = ''
    await load()
  } catch (err) {
    submitError.value = errorText(err)
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="refund-view">
    <header class="account-page-head">
      <div>
        <RouterLink :to="`/account/orders/${orderId}`" class="back-link">
          <AppIcon name="chevron-left" :size="15" />返回订单详情
        </RouterLink>
        <span class="eyebrow">AFTER SALES</span>
        <h2>申请退款</h2>
        <p v-if="order">订单 {{ order.order_no }} · 币种 {{ order.currency }}</p>
      </div>
    </header>

    <StateBlock v-if="loading" :loading="true" />
    <StateBlock v-else-if="error" :error="error" @retry="load" />

    <template v-else-if="order">
      <div class="refund-notice">
        <AppIcon name="info" :size="18" />
        <p>退款按店铺子单申请；当前为 Mock 原路退回，未发生真实资金交易。多店铺订单需分别提交。</p>
      </div>

      <div v-if="successRefund" class="refund-success">
        <span class="payment-result-icon"><AppIcon name="check" :size="26" /></span>
        <div>
          <strong>退款申请已提交</strong>
          <p>
            退款单号 {{ successRefund.refund_no }} · ¥{{ money(successRefund.amount) }} ·
            {{ refundStatusLabel(successRefund.status) }}
          </p>
        </div>
      </div>

      <StateBlock
        v-if="!successRefund"
        :empty="!eligibleStoreOrders.length"
        :empty-text="
          refunds.length ? '退款申请已提交，可在下方查看进度' : '当前订单没有可退款的店铺子单'
        "
      >
        <template #empty-action>
          <RouterLink :to="`/account/orders/${orderId}`" class="outline-button small"
            >返回订单</RouterLink
          >
        </template>

        <form class="refund-form" @submit.prevent="submit">
          <section class="info-card">
            <header>
              <AppIcon name="package" :size="16" />
              <h3>选择退款子单</h3>
            </header>
            <div class="refund-store-options">
              <label
                v-for="store in eligibleStoreOrders"
                :key="store.id"
                class="refund-store-option"
                :class="{ active: selectedStoreOrderId === store.id }"
              >
                <input
                  v-model="selectedStoreOrderId"
                  type="radio"
                  name="store-order"
                  :value="store.id"
                  @change="selectStore(store)"
                />
                <div>
                  <strong>{{ store.store_order_no }}</strong>
                  <span
                    >实付 ¥{{ money(store.pay_amount) }} · 已退 ¥{{
                      money(store.refund_amount)
                    }}</span
                  >
                </div>
                <span class="refundable">可退 ¥{{ refundableOf(store) }}</span>
              </label>
            </div>
          </section>

          <section class="info-card">
            <header>
              <AppIcon name="wallet" :size="16" />
              <h3>退款金额</h3>
            </header>
            <label class="field">
              <span>退款金额（元）</span>
              <input
                v-model="amount"
                type="number"
                min="0.01"
                step="0.01"
                :max="selectedStoreOrder ? refundableOf(selectedStoreOrder) : undefined"
              />
            </label>
            <p class="muted-text">
              可退金额
              {{
                selectedStoreOrder ? `¥${refundableOf(selectedStoreOrder)}` : '—'
              }}，最终以服务端校验为准。
            </p>
          </section>

          <section class="info-card">
            <header>
              <AppIcon name="edit" :size="16" />
              <h3>退款原因</h3>
            </header>
            <label class="field">
              <span>请说明退款原因</span>
              <textarea
                v-model="reason"
                maxlength="255"
                rows="4"
                placeholder="如：商品与描述不符 / 不想要了 / 其他原因"
              />
            </label>
          </section>

          <p v-if="submitError" class="form-error">{{ submitError }}</p>
          <button class="primary-button" type="submit" :disabled="submitting">
            <span v-if="submitting" class="mini-spinner" />
            {{ submitting ? '提交中…' : '提交退款申请' }}
          </button>
        </form>
      </StateBlock>

      <section v-if="refunds.length" class="info-card">
        <header>
          <AppIcon name="refresh" :size="16" />
          <h3>退款记录</h3>
        </header>
        <ul class="refund-list">
          <li v-for="refund in refunds" :key="refund.id">
            <div>
              <strong>{{ refund.refund_no }}</strong>
              <span>{{ refund.reason }}</span>
              <small>{{ formatDateTime(refund.created_at) }}</small>
            </div>
            <div class="refund-list-side">
              <strong>¥{{ money(refund.amount) }}</strong>
              <span class="status-tag tone-warning">{{ refundStatusLabel(refund.status) }}</span>
              <small v-if="refund.result_note">{{ refund.result_note }}</small>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
