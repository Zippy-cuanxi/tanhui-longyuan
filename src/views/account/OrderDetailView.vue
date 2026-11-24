<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { orderApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { Order, Refund } from '@/api/types'
import {
  errorText,
  formatDateTime,
  money,
  orderProgress,
  productFallbackImage,
  refundStatusLabel
} from '@/utils/format'
import { useOrderActions } from '@/composables/useOrderActions'
import AppIcon from '@/components/AppIcon.vue'
import OrderStatusTag from '@/components/OrderStatusTag.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const orderId = computed(() => String(route.params.id))
const order = ref<Order | null>(null)
const refunds = ref<Refund[]>([])
const loading = ref(true)
const error = ref('')

const steps = [
  { label: '提交订单', hint: '订单已创建' },
  { label: '支付成功', hint: '等待商家发货' },
  { label: '商家发货', hint: '包裹运输中' },
  { label: '确认收货', hint: '交易完成' }
]
const progress = computed(() => (order.value ? orderProgress(order.value.status) : -1))
const itemCount = computed(
  () =>
    order.value?.store_orders.reduce(
      (sum, store) => sum + store.items.reduce((s, item) => s + item.quantity, 0),
      0
    ) || 0
)
const isCancelled = computed(() => order.value?.status === 'cancelled')
const isAfterSale = computed(() =>
  ['refunding', 'refunded', 'partially_refunded'].includes(order.value?.status || '')
)

const actions = useOrderActions(load)

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
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="order-detail-view">
    <StateBlock v-if="loading" :loading="true" />
    <StateBlock v-else-if="error" :error="error" @retry="load" />

    <template v-else-if="order">
      <header class="account-page-head">
        <div>
          <RouterLink to="/account/orders" class="back-link">
            <AppIcon name="chevron-left" :size="15" />返回订单列表
          </RouterLink>
          <span class="eyebrow">ORDER DETAIL</span>
          <h2>订单详情</h2>
          <p>订单号 {{ order.order_no }} · {{ formatDateTime(order.created_at) }}</p>
        </div>
        <OrderStatusTag :status="order.status" />
      </header>

      <div v-if="isCancelled" class="order-banner danger">
        <AppIcon name="info" :size="18" />
        <div>
          <strong>订单已取消</strong>
          <p>{{ order.cancel_reason || '该订单已关闭。' }}</p>
        </div>
      </div>
      <div v-else-if="isAfterSale" class="order-banner warning">
        <AppIcon name="refresh" :size="18" />
        <div>
          <strong>订单处于售后状态</strong>
          <p>退款进度以退款单与平台处理结果为准。</p>
        </div>
      </div>

      <div v-if="!isCancelled && progress >= 0" class="order-steps">
        <div
          v-for="(step, index) in steps"
          :key="step.label"
          class="order-step"
          :class="{ done: index <= progress, current: index === progress }"
        >
          <span class="step-dot"
            ><AppIcon v-if="index < progress" name="check" :size="12" /><template v-else>{{
              index + 1
            }}</template></span
          >
          <div>
            <strong>{{ step.label }}</strong>
            <small>{{ step.hint }}</small>
          </div>
        </div>
      </div>

      <div class="order-detail-actions">
        <button
          v-if="order.status === 'pending_payment'"
          class="ghost-button"
          type="button"
          @click="actions.handle('cancel', order)"
        >
          取消订单
        </button>
        <button
          v-if="order.status === 'pending_payment'"
          class="primary-button"
          type="button"
          @click="actions.handle('pay', order)"
        >
          去支付
        </button>
        <button
          v-if="order.status === 'shipped'"
          class="ghost-button"
          type="button"
          @click="actions.handle('logistics', order)"
        >
          <AppIcon name="truck" :size="15" />查看物流
        </button>
        <button
          v-if="order.status === 'shipped'"
          class="primary-button"
          type="button"
          @click="actions.handle('confirm', order)"
        >
          确认收货
        </button>
        <button
          v-if="['paid', 'shipped', 'completed', 'partially_refunded'].includes(order.status)"
          class="ghost-button"
          type="button"
          @click="actions.handle('refund', order)"
        >
          申请退款
        </button>
      </div>

      <div class="order-info-grid">
        <section class="info-card">
          <header>
            <AppIcon name="location" :size="16" />
            <h3>收货信息</h3>
          </header>
          <strong>{{ order.receiver_name }} · {{ order.receiver_phone }}</strong>
          <p>{{ order.address }}</p>
          <p v-if="order.remark" class="muted-text">备注：{{ order.remark }}</p>
        </section>
        <section class="info-card">
          <header>
            <AppIcon name="wallet" :size="16" />
            <h3>金额明细</h3>
          </header>
          <dl class="amount-list">
            <div>
              <dt>商品金额</dt>
              <dd>¥{{ money(order.items_total) }}</dd>
            </div>
            <div>
              <dt>运费</dt>
              <dd>¥{{ money(order.shipping_fee) }}</dd>
            </div>
            <div v-if="order.points_deduct !== '0.00'">
              <dt>积分抵扣</dt>
              <dd>-¥{{ money(order.points_deduct) }}</dd>
            </div>
            <div class="total-row">
              <dt>实付金额</dt>
              <dd>¥{{ money(order.pay_amount) }}</dd>
            </div>
          </dl>
          <p class="muted-text">币种 {{ order.currency }} · 共 {{ itemCount }} 件商品</p>
        </section>
      </div>

      <section v-for="store in order.store_orders" :key="store.id" class="order-store-card">
        <header class="order-store-head">
          <div>
            <span class="eyebrow">STORE ORDER</span>
            <strong>{{ store.store_order_no }}</strong>
          </div>
          <OrderStatusTag :status="store.status" />
        </header>
        <ul class="order-store-items">
          <li v-for="item in store.items" :key="item.id">
            <RouterLink :to="`/products/${item.product_id}`">
              <img
                :src="assetUrl(item.image_url, productFallbackImage(item.title))"
                :alt="item.title"
                loading="lazy"
                decoding="async"
              />
            </RouterLink>
            <div>
              <RouterLink :to="`/products/${item.product_id}`"
                ><strong>{{ item.title }}</strong></RouterLink
              >
              <span>{{ item.spec }}</span>
            </div>
            <span>¥{{ money(item.unit_price) }} × {{ item.quantity }}</span>
            <strong>¥{{ money(item.subtotal) }}</strong>
          </li>
        </ul>
        <footer class="order-store-foot">
          <span>商品 ¥{{ money(store.items_total) }}</span>
          <span>运费 ¥{{ money(store.shipping_fee) }}</span>
          <span
            >实付 <strong>¥{{ money(store.pay_amount) }}</strong></span
          >
          <span v-if="store.refund_amount !== '0.00'">已退 ¥{{ money(store.refund_amount) }}</span>
        </footer>
      </section>

      <section v-if="refunds.length" class="info-card refund-list-card">
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
        <p class="muted-text">退款为 Mock 原路退回，未发生真实资金交易。</p>
      </section>
    </template>
  </div>
</template>
