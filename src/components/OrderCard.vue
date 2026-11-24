<script setup lang="ts">
import { computed } from 'vue'
import { assetUrl } from '@/api/http'
import type { Order } from '@/api/types'
import { formatDateTime, money, productFallbackImage } from '@/utils/format'
import AppIcon from './AppIcon.vue'
import OrderStatusTag from './OrderStatusTag.vue'

const props = withDefaults(defineProps<{ order: Order; compact?: boolean }>(), { compact: false })
const emit = defineEmits<{ action: [type: string, order: Order] }>()

const items = computed(() => props.order.store_orders.flatMap((store) => store.items))
const itemCount = computed(() => items.value.reduce((sum, item) => sum + item.quantity, 0))
const visibleItems = computed(() => items.value.slice(0, 3))

function act(type: string): void {
  emit('action', type, props.order)
}
</script>

<template>
  <article class="order-card" :class="{ compact }">
    <header class="order-card-head">
      <div>
        <span class="order-no">订单号 {{ order.order_no }}</span>
        <span class="order-date">{{ formatDateTime(order.created_at) }}</span>
      </div>
      <OrderStatusTag :status="order.status" />
    </header>

    <div class="order-card-items">
      <div v-for="item in visibleItems" :key="item.id" class="order-item-row">
        <img :src="assetUrl(item.image_url, productFallbackImage(item.title))" :alt="item.title" />
        <div>
          <strong>{{ item.title }}</strong>
          <span>{{ item.spec }} × {{ item.quantity }}</span>
        </div>
        <span class="order-item-subtotal">¥{{ money(item.subtotal) }}</span>
      </div>
      <div v-if="items.length > 3" class="order-more-items">
        另有 {{ items.length - 3 }} 种商品，共 {{ itemCount }} 件
      </div>
    </div>

    <footer class="order-card-foot">
      <span class="order-count">共 {{ itemCount }} 件</span>
      <span
        v-if="
          order.points_earned &&
          !['refunding', 'refunded', 'partially_refunded', 'cancelled'].includes(order.status)
        "
        class="order-count"
        >+{{ order.points_earned }} 绿色积分</span
      >
      <span class="order-total"
        >实付 <strong>¥{{ money(order.pay_amount) }}</strong></span
      >
      <div class="order-actions">
        <button
          v-if="order.status === 'pending_payment'"
          class="ghost-button small"
          type="button"
          @click="act('cancel')"
        >
          取消订单
        </button>
        <button
          v-if="order.status === 'pending_payment'"
          class="primary-button small"
          type="button"
          @click="act('pay')"
        >
          去支付
        </button>
        <button
          v-if="order.status === 'shipped'"
          class="ghost-button small"
          type="button"
          @click="act('logistics')"
        >
          <AppIcon name="truck" :size="14" />查看物流
        </button>
        <button
          v-if="order.status === 'shipped'"
          class="primary-button small"
          type="button"
          @click="act('confirm')"
        >
          确认收货
        </button>
        <button
          v-if="['paid', 'shipped', 'completed', 'partially_refunded'].includes(order.status)"
          class="ghost-button small"
          type="button"
          @click="act('refund')"
        >
          申请退款
        </button>
        <button class="ghost-button small" type="button" @click="act('detail')">查看详情</button>
      </div>
    </footer>
  </article>
</template>
