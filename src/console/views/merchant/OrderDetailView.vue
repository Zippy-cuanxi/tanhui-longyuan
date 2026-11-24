<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleMasked from '@/console/components/ConsoleMasked.vue'
import ConsoleErrorState from '@/console/components/ConsoleErrorState.vue'
import ShipDrawer from './components/ShipDrawer.vue'
import { merchantApi, type Order } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { formatDateTime, formatMoney, hoursUntil, isOverdue } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const route = useRoute()
const router = useRouter()
const orderId = computed(() => String(route.params.id || ''))
const order = ref<Order | null>(null)
const loading = ref(true)
const error = ref('')
const requestId = ref('')
const shipVisible = ref(false)

const deadlineText = computed(() => {
  if (!order.value || order.value.status !== 'paid' || !order.value.shipDeadline) return ''
  const hours = hoursUntil(order.value.shipDeadline)
  return isOverdue(order.value.shipDeadline)
    ? `发货已超时 ${Math.abs(hours)} 小时，请尽快处理`
    : `请在 ${hours} 小时内完成发货`
})
const deadlineDanger = computed(
  () => Boolean(order.value?.shipDeadline) && isOverdue(order.value?.shipDeadline)
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    order.value = await merchantApi.order(auth.merchantAccount?.id || '', orderId.value)
  } catch (err) {
    const state = toErrorState(err)
    error.value = state.message
    requestId.value = state.requestId
  } finally {
    loading.value = false
  }
}

async function onShipped(): Promise<void> {
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="订单详情"
      description="订单、收货、金额与物流轨迹均来自本地仿真数据。"
    >
      <template #actions>
        <el-button @click="router.push('/console/merchant/orders')">返回列表</el-button>
        <el-button v-if="order?.status === 'paid'" type="primary" @click="shipVisible = true">
          订单发货
        </el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleErrorState v-if="error" :message="error" :request-id="requestId" @retry="load" />
    <div v-else-if="loading" class="console-card">
      <el-skeleton :rows="10" animated />
    </div>
    <template v-else-if="order">
      <div
        v-if="order.status === 'paid'"
        class="console-alert-row"
        :style="
          deadlineDanger ? { borderColor: '#F1D4D4', background: '#FFF5F5', color: '#B5454C' } : {}
        "
      >
        <el-icon><Timer /></el-icon>
        <strong>{{ deadlineText }}</strong>
        <span v-if="order.shipDeadline" class="console-muted">
          发货截止：{{ formatDateTime(order.shipDeadline) }}
        </span>
      </div>

      <section class="console-card">
        <div class="console-card-title">
          <span>订单概览</span>
          <ConsoleStatusTag kind="order" :value="order.status" />
        </div>
        <div class="console-summary-grid">
          <div class="console-summary-item">
            <span>订单号</span>
            <strong style="font-size: 14px">{{ order.orderNo }}</strong>
          </div>
          <div class="console-summary-item">
            <span>实付金额</span>
            <strong class="amount">¥{{ formatMoney(order.payAmount) }}</strong>
          </div>
          <div class="console-summary-item">
            <span>下单时间</span>
            <strong style="font-size: 14px">{{ formatDateTime(order.createdAt) }}</strong>
          </div>
          <div class="console-summary-item">
            <span>支付时间</span>
            <strong style="font-size: 14px">{{ formatDateTime(order.paidAt) }}</strong>
          </div>
        </div>
      </section>

      <div class="console-detail-layout" style="margin-top: 14px">
        <div>
          <section class="console-card">
            <div class="console-card-title">收货信息</div>
            <div class="console-detail-field">
              <label>收货人</label><span>{{ order.buyerName }}</span>
            </div>
            <div class="console-detail-field">
              <label>手机号</label><span><ConsoleMasked :value="order.buyerPhone" /></span>
            </div>
            <div class="console-detail-field">
              <label>邮箱</label
              ><span><ConsoleMasked :value="order.buyerEmail" kind="email" /></span>
            </div>
            <div class="console-detail-field">
              <label>收货地址</label
              ><span><ConsoleMasked :value="order.address" kind="address" /></span>
            </div>
            <div v-if="order.remark" class="console-detail-field">
              <label>买家备注</label><span>{{ order.remark }}</span>
            </div>
          </section>

          <section class="console-card">
            <div class="console-card-title">
              <span>商品明细</span>
              <span class="console-muted">{{ order.items.length }} 种商品</span>
            </div>
            <el-table :data="order.items">
              <el-table-column label="商品" min-width="240">
                <template #default="{ row }">
                  <div class="console-product-cell">
                    <img :src="row.image" :alt="row.title" />
                    <div>
                      <strong>{{ row.title }}</strong>
                      <span>{{ row.spec }}</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="单价" width="110" align="right">
                <template #default="{ row }">¥{{ formatMoney(row.price) }}</template>
              </el-table-column>
              <el-table-column prop="quantity" label="数量" width="70" align="right" />
              <el-table-column label="小计" width="120" align="right">
                <template #default="{ row }">
                  <span class="console-amount">
                    ¥{{ formatMoney(Number(row.price) * row.quantity) }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
            <div style="margin-top: 14px; max-width: 320px; margin-left: auto">
              <div class="console-detail-amount-row">
                <span>商品合计</span><span>¥{{ formatMoney(order.itemsTotal) }}</span>
              </div>
              <div class="console-detail-amount-row">
                <span>运费</span><span>¥{{ formatMoney(order.shippingFee) }}</span>
              </div>
              <div v-if="Number(order.refundAmount) > 0" class="console-detail-amount-row">
                <span>已退款</span>
                <span class="console-amount">-¥{{ formatMoney(order.refundAmount) }}</span>
              </div>
              <div class="console-detail-amount-row total">
                <span>买家实付</span><b>¥{{ formatMoney(order.payAmount) }}</b>
              </div>
            </div>
          </section>

          <section class="console-card">
            <div class="console-card-title">物流信息</div>
            <template v-if="order.shipment">
              <div class="console-detail-field">
                <label>快递公司</label><span>{{ order.shipment.carrier }}</span>
              </div>
              <div class="console-detail-field">
                <label>快递单号</label>
                <span class="console-mono">{{ order.shipment.trackingNo }}</span>
              </div>
              <div class="console-detail-field">
                <label>发货时间</label><span>{{ formatDateTime(order.shipment.shippedAt) }}</span>
              </div>
              <ul class="console-timeline" style="margin-top: 12px">
                <li v-for="track in order.shipment.tracks" :key="track.time + track.text">
                  {{ track.text }}
                  <small>{{ formatDateTime(track.time) }}</small>
                </li>
              </ul>
            </template>
            <div v-else class="console-muted">尚未发货，请及时处理待发货订单。</div>
          </section>
        </div>

        <div>
          <section class="console-card">
            <div class="console-card-title">订单状态</div>
            <ul class="console-timeline">
              <li v-for="log in order.statusLogs.slice().reverse()" :key="log.time + log.action">
                <strong>{{ log.action }}</strong> · {{ log.status }}
                <div v-if="log.note" class="console-muted">{{ log.note }}</div>
                <small>{{ formatDateTime(log.time) }} · {{ log.operator }}</small>
              </li>
            </ul>
          </section>

          <section class="console-card">
            <div class="console-card-title">操作提示</div>
            <p class="console-card-note">
              · 待发货订单请在 48 小时内发货，超时会影响店铺服务评分。<br />
              · 修改价格、库存不涉及商品审核，但订单金额以支付快照为准。<br />
              · 售后由买家发起后进入「售后处理」，平台仲裁结果会同步订单与结算。
            </p>
          </section>
        </div>
      </div>

      <ShipDrawer v-model="shipVisible" :order="order" @shipped="onShipped" />
    </template>
  </div>
</template>
