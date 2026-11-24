<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { orderApi, paymentApi } from '@/api'
import type { Order, Payment } from '@/api/types'
import { errorText, formatDateTime, money } from '@/utils/format'
import { useToastStore } from '@/stores/toast'
import AppIcon from '@/components/AppIcon.vue'
import OrderStatusTag from '@/components/OrderStatusTag.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const orderId = computed(() => String(route.params.orderId))

const order = ref<Order | null>(null)
const payment = ref<Payment | null>(null)
const loading = ref(true)
const error = ref('')
const initError = ref('')
const paying = ref(false)
const payError = ref('')

const isPaid = computed(() =>
  Boolean(order.value && order.value.status !== 'pending_payment' && order.value.paid_at)
)
const itemCount = computed(
  () =>
    order.value?.store_orders.reduce(
      (sum, store) => sum + store.items.reduce((s, item) => s + item.quantity, 0),
      0
    ) || 0
)

async function loadOrder(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    order.value = await orderApi.detail(orderId.value)
    if (order.value.status === 'pending_payment') {
      await initPayment()
    }
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

async function initPayment(): Promise<void> {
  initError.value = ''
  try {
    payment.value = await paymentApi.init(orderId.value)
  } catch (err) {
    initError.value = errorText(err)
  }
}

async function pay(): Promise<void> {
  if (!payment.value || paying.value) return
  paying.value = true
  payError.value = ''
  try {
    const result = await paymentApi.mockPay(payment.value.pay_no)
    if (result.return_code && result.return_code !== 'SUCCESS') {
      throw new Error('沙箱支付未成功，请稍后重试')
    }
    order.value = await orderApi.detail(orderId.value)
    if (order.value.status === 'pending_payment') {
      payError.value = '支付未完成，请稍后重试'
      return
    }
    toast.show('沙箱支付成功，订单状态已更新', 'success')
  } catch (err) {
    payError.value = errorText(err)
  } finally {
    paying.value = false
  }
}

onMounted(loadOrder)
</script>

<template>
  <main class="page-main payment-page">
    <div class="page-container narrow-container">
      <StateBlock v-if="loading" :loading="true" />
      <StateBlock v-else-if="error" :error="error" @retry="loadOrder" />

      <template v-else-if="order">
        <div v-if="isPaid" class="payment-result success">
          <span class="payment-result-icon"><AppIcon name="check" :size="34" /></span>
          <span class="eyebrow">PAYMENT SUCCESS</span>
          <h1>支付成功</h1>
          <p>订单 {{ order.order_no }} 已完成支付，商家将尽快为您发货。</p>
          <div class="payment-result-amount">¥{{ money(order.pay_amount) }}</div>
          <div class="payment-result-meta">
            <span>订单状态 <OrderStatusTag :status="order.status" /></span>
            <span>商品 {{ itemCount }} 件</span>
            <span>{{ order.receiver_name }} · {{ order.address }}</span>
          </div>
          <div class="payment-result-actions">
            <RouterLink :to="`/account/orders/${order.id}`" class="primary-button"
              >查看订单</RouterLink
            >
            <RouterLink to="/products" class="outline-button">继续选购</RouterLink>
          </div>
          <p class="sandbox-note">
            <AppIcon name="info" :size="14" /> 本次为沙箱支付（Mock），未发生真实资金交易。
          </p>
        </div>

        <div v-else-if="order.status === 'cancelled'" class="payment-result">
          <span class="payment-result-icon muted"><AppIcon name="clock" :size="32" /></span>
          <h1>订单已取消</h1>
          <p>该订单已关闭，无法继续支付。</p>
          <div class="payment-result-actions">
            <RouterLink to="/products" class="primary-button">重新选购</RouterLink>
            <RouterLink :to="`/account/orders/${order.id}`" class="outline-button"
              >查看订单</RouterLink
            >
          </div>
        </div>

        <template v-else>
          <header class="page-heading">
            <div>
              <span class="eyebrow">CHECKOUT · PAY</span>
              <h1>订单支付</h1>
              <p>订单号 {{ order.order_no }} · 共 {{ itemCount }} 件商品</p>
            </div>
            <OrderStatusTag :status="order.status" />
          </header>

          <div class="payment-layout">
            <section class="payment-card">
              <div class="payment-amount">
                <span>应付金额</span>
                <strong><small>¥</small>{{ money(order.pay_amount) }}</strong>
                <em v-if="payment" class="sandbox-badge">Mock 沙箱</em>
              </div>
              <dl class="payment-meta">
                <div>
                  <dt>支付单号</dt>
                  <dd>{{ payment?.pay_no || '—' }}</dd>
                </div>
                <div>
                  <dt>支付渠道</dt>
                  <dd>{{ payment?.provider || 'mock_sandbox' }}（仿真）</dd>
                </div>
                <div>
                  <dt>支付截止</dt>
                  <dd>{{ formatDateTime(payment?.expires_at) }}</dd>
                </div>
                <div>
                  <dt>收货信息</dt>
                  <dd>
                    {{ order.receiver_name }} · {{ order.receiver_phone }} · {{ order.address }}
                  </dd>
                </div>
              </dl>

              <p v-if="initError" class="form-error">{{ initError }}</p>
              <p v-if="payError" class="form-error">{{ payError }}</p>

              <button
                class="primary-button full-button pay-button"
                type="button"
                :disabled="paying || !payment"
                @click="pay"
              >
                <span v-if="paying" class="mini-spinner" />
                <AppIcon v-else name="card" :size="18" />
                {{ paying ? '支付处理中…' : '沙箱支付（演示）' }}
              </button>
              <button
                v-if="initError"
                class="ghost-button full-button"
                type="button"
                @click="initPayment"
              >
                <AppIcon name="refresh" :size="15" />重新发起支付
              </button>
              <p class="sandbox-note">
                <AppIcon name="info" :size="14" />
                当前支付渠道为 Mock 沙箱，未接入真实支付；点击后由后端模拟签名回调并更新订单状态。
              </p>
            </section>

            <aside class="payment-summary">
              <span class="eyebrow">ORDER INFO</span>
              <h2>订单信息</h2>
              <dl>
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
                  <dt>应付</dt>
                  <dd>¥{{ money(order.pay_amount) }}</dd>
                </div>
              </dl>
              <div v-for="store in order.store_orders" :key="store.id" class="payment-store">
                <header>
                  <AppIcon name="package" :size="14" /><strong>{{ store.store_order_no }}</strong>
                </header>
                <ul>
                  <li v-for="item in store.items" :key="item.id">
                    <span>{{ item.title }} · {{ item.spec }} × {{ item.quantity }}</span>
                    <strong>¥{{ money(item.subtotal) }}</strong>
                  </li>
                </ul>
              </div>
              <button
                class="ghost-button full-button"
                type="button"
                @click="router.push(`/account/orders/${order.id}`)"
              >
                稍后支付，查看订单
              </button>
            </aside>
          </div>
        </template>
      </template>
    </div>
  </main>
</template>
