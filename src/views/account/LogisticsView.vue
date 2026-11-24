<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { logisticsApi, orderApi } from '@/api'
import type { Order, Shipment } from '@/api/types'
import { errorText, formatDateTime } from '@/utils/format'
import { useRefreshOnFocus } from '@/composables/useRefreshOnFocus'
import AppIcon from '@/components/AppIcon.vue'
import OrderStatusTag from '@/components/OrderStatusTag.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const orderId = computed(() => String(route.params.id))
const order = ref<Order | null>(null)
const shipments = ref<Shipment[]>([])
const loading = ref(true)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [orderResult, shipmentResult] = await Promise.allSettled([
      orderApi.detail(orderId.value),
      logisticsApi.forOrder(orderId.value)
    ])
    if (orderResult.status === 'rejected') throw orderResult.reason
    order.value = orderResult.value
    shipments.value = shipmentResult.status === 'fulfilled' ? shipmentResult.value : []
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
useRefreshOnFocus(load)
</script>

<template>
  <div class="logistics-view">
    <header class="account-page-head">
      <div>
        <RouterLink :to="`/account/orders/${orderId}`" class="back-link">
          <AppIcon name="chevron-left" :size="15" />返回订单详情
        </RouterLink>
        <span class="eyebrow">LOGISTICS</span>
        <h2>物流详情</h2>
        <p v-if="order">订单 {{ order.order_no }}</p>
      </div>
      <OrderStatusTag v-if="order" :status="order.status" />
    </header>

    <StateBlock v-if="loading" :loading="true" />
    <StateBlock v-else-if="error" :error="error" @retry="load" />
    <StateBlock
      v-else-if="!shipments.length"
      :empty="true"
      empty-text="商家尚未发货，发货后可在此查看物流轨迹"
    >
      <template #empty-action>
        <RouterLink :to="`/account/orders/${orderId}`" class="outline-button small"
          >返回订单</RouterLink
        >
      </template>
    </StateBlock>

    <div v-else class="shipment-list">
      <article v-for="shipment in shipments" :key="shipment.id" class="shipment-card">
        <header class="shipment-head">
          <span class="shipment-icon"><AppIcon name="truck" :size="22" /></span>
          <div>
            <strong>{{ shipment.carrier }}</strong>
            <span>运单号 {{ shipment.tracking_no }}</span>
            <small>发货时间 {{ formatDateTime(shipment.shipped_at) }}</small>
          </div>
          <span class="status-tag tone-primary">{{
            shipment.status === 'shipped' ? '运输中' : shipment.status
          }}</span>
        </header>

        <ol class="track-list">
          <li
            v-for="track in [...shipment.tracks].reverse()"
            :key="`${track.status}-${track.occurred_at}`"
            :class="{ latest: track === [...shipment.tracks].reverse()[0] }"
          >
            <span class="track-dot" />
            <div>
              <strong>{{ track.description || track.status }}</strong>
              <small>{{ formatDateTime(track.occurred_at) }}</small>
            </div>
          </li>
        </ol>

        <p v-if="shipment.mock" class="sandbox-note">
          <AppIcon name="info" :size="14" />该物流轨迹为 Mock 演示数据，不代表真实承运信息。
        </p>
      </article>
    </div>
  </div>
</template>
