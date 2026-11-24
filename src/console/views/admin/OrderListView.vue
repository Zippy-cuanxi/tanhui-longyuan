<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleFilterBar from '@/console/components/ConsoleFilterBar.vue'
import ConsoleStatusTabs from '@/console/components/ConsoleStatusTabs.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleMasked from '@/console/components/ConsoleMasked.vue'
import ConsoleExportButton from '@/console/components/ConsoleExportButton.vue'
import ConsoleDetailDrawer from '@/console/components/ConsoleDetailDrawer.vue'
import type { TableColumn } from '@/console/components/types'
import { adminApi, type Order } from '@/console/api'
import { downloadCsv, formatDateTime, formatMoney, maskPhone } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const query = reactive({ keyword: '', status: 'all', storeId: '', page: 1, page_size: 20 })
const dateRange = ref<[string, string] | null>(null)
const items = ref<Order[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const requestId = ref('')
const counts = ref<Record<string, number>>({})
const stores = ref<Array<{ id: string; name: string; merchantId: string }>>([])
const selected = ref<Order[]>([])

const drawerVisible = ref(false)
const detail = ref<Order | null>(null)
const detailLoading = ref(false)
const detailError = ref('')
const detailRequestId = ref('')
const activeId = ref('')

const tabs = computed(() => [
  { label: '全部', value: 'all', count: counts.value.all },
  { label: '待付款', value: 'pending_payment', count: counts.value.pending_payment },
  { label: '待发货', value: 'paid', count: counts.value.paid },
  { label: '待收货', value: 'shipped', count: counts.value.shipped },
  { label: '已完成', value: 'completed', count: counts.value.completed },
  { label: '退款中', value: 'refunding', count: counts.value.refunding },
  { label: '已退款', value: 'refunded', count: counts.value.refunded },
  { label: '部分退款', value: 'partially_refunded', count: counts.value.partially_refunded },
  { label: '已取消', value: 'cancelled', count: counts.value.cancelled }
])

const columns: TableColumn[] = [
  { label: '订单信息', slot: 'order', minWidth: 145 },
  { label: '店铺', prop: 'storeName', minWidth: 125, showOverflowTooltip: true },
  { label: '买家', slot: 'buyer', minWidth: 95 },
  { label: '商品', slot: 'items', minWidth: 135 },
  { label: '实付 / 退款', slot: 'amount', width: 100, align: 'right' },
  { label: '状态', slot: 'status', width: 90 },
  { label: '下单时间', slot: 'created', width: 138 },
  { label: '操作', slot: 'actions', width: 75, fixed: 'right' }
]

const exportRows = computed(() =>
  items.value.map((item) => ({
    orderNo: item.orderNo,
    storeName: item.storeName,
    buyer: item.buyerName,
    phone: maskPhone(item.buyerPhone),
    payAmount: item.payAmount,
    refundAmount: item.refundAmount,
    status: item.status,
    createdAt: formatDateTime(item.createdAt)
  }))
)

async function loadCounts(): Promise<void> {
  try {
    counts.value = await adminApi.orderStats()
  } catch {
    counts.value = {}
  }
}

async function loadStores(): Promise<void> {
  try {
    stores.value = await adminApi.storeOptions()
  } catch {
    stores.value = []
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const result = await adminApi.orders({
      page: query.page,
      page_size: query.page_size,
      status: query.status,
      keyword: query.keyword,
      storeId: query.storeId,
      date_from: dateRange.value?.[0],
      date_to: dateRange.value?.[1]
    })
    items.value = result.items
    total.value = result.pagination.total
    void loadCounts()
  } catch (err) {
    const state = toErrorState(err)
    error.value = state.message
    requestId.value = state.requestId
  } finally {
    loading.value = false
  }
}

function search(): void {
  query.page = 1
  load()
}

function reset(): void {
  query.keyword = ''
  query.status = 'all'
  query.storeId = ''
  query.page = 1
  dateRange.value = null
  load()
}

function changeTab(value: string): void {
  query.status = value
  query.page = 1
  load()
}

async function openDetail(row: Record<string, unknown> | Order): Promise<void> {
  const order = row as Order
  activeId.value = order.id
  drawerVisible.value = true
  detailLoading.value = true
  detailError.value = ''
  detailRequestId.value = ''
  try {
    detail.value = await adminApi.order(activeId.value)
  } catch (err) {
    const state = toErrorState(err)
    detailError.value = state.message
    detailRequestId.value = state.requestId
  } finally {
    detailLoading.value = false
  }
}

function retryDetail(): void {
  if (activeId.value) void openDetail({ id: activeId.value })
}

function onSelectionChange(rows: Record<string, any>[]): void {
  selected.value = rows as Order[]
}

function exportSelected(): void {
  if (!selected.value.length) return
  downloadCsv(
    '平台订单-所选.csv',
    selected.value.map((item) => ({
      orderNo: item.orderNo,
      storeName: item.storeName,
      buyer: item.buyerName,
      payAmount: item.payAmount,
      status: item.status,
      createdAt: formatDateTime(item.createdAt)
    })),
    [
      { key: 'orderNo', label: '订单号' },
      { key: 'storeName', label: '店铺' },
      { key: 'buyer', label: '买家' },
      { key: 'payAmount', label: '实付金额' },
      { key: 'status', label: '状态' },
      { key: 'createdAt', label: '下单时间' }
    ]
  )
  ElMessage.success(`已导出 ${selected.value.length} 条订单`)
}

onMounted(() => {
  void loadStores()
  void load()
})
</script>

<template>
  <div>
    <ConsolePageHeader
      title="订单管理"
      description="全平台订单查询；敏感联系信息默认脱敏，金额以支付快照为准。"
    >
      <template #actions>
        <ConsoleExportButton
          filename="平台订单.csv"
          :rows="exportRows"
          :headers="[
            { key: 'orderNo', label: '订单号' },
            { key: 'storeName', label: '店铺' },
            { key: 'buyer', label: '买家' },
            { key: 'phone', label: '手机号' },
            { key: 'payAmount', label: '实付金额' },
            { key: 'refundAmount', label: '退款金额' },
            { key: 'status', label: '状态' },
            { key: 'createdAt', label: '下单时间' }
          ]"
        />
      </template>
    </ConsolePageHeader>

    <ConsoleFilterBar :loading="loading" @search="search" @reset="reset">
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          clearable
          placeholder="订单号 / 买家 / 店铺"
          style="width: 220px"
          @keyup.enter="search"
        />
      </el-form-item>
      <el-form-item label="店铺">
        <el-select
          v-model="query.storeId"
          clearable
          filterable
          placeholder="全部店铺"
          style="width: 190px"
        >
          <el-option v-for="item in stores" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="下单日期">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 250px"
        />
      </el-form-item>
    </ConsoleFilterBar>

    <ConsoleStatusTabs :tabs="tabs" :model-value="query.status" @update:model-value="changeTab" />

    <ConsoleDataTable
      :columns="columns"
      :rows="items"
      :loading="loading"
      :error="error"
      :error-request-id="requestId"
      :total="total"
      :page="query.page"
      :page-size="query.page_size"
      selectable
      empty-text="暂无订单"
      :empty-image="assetUrl('/console-assets/images/empty-orders.webp')"
      @row-click="openDetail"
      @selection-change="onSelectionChange"
      @update:page="
        (value: number) => {
          query.page = value
          load()
        }
      "
      @update:page-size="
        (value: number) => {
          query.page_size = value
          query.page = 1
          load()
        }
      "
      @retry="load"
    >
      <template #bulk>
        <el-button size="small" plain @click="exportSelected">导出所选订单</el-button>
      </template>

      <template #order="{ row }">
        <div class="console-two-line">
          <strong class="console-mono">{{ row.orderNo }}</strong>
          <span>{{ row.storeName }}</span>
        </div>
      </template>

      <template #buyer="{ row }">
        <div class="console-two-line">
          <strong>{{ row.buyerName }}</strong>
          <span><ConsoleMasked :value="row.buyerPhone" /></span>
        </div>
      </template>

      <template #items="{ row }">
        <span class="console-ellipsis" :title="row.items.map((item: any) => item.title).join('、')">
          {{ row.items[0]?.title
          }}<template v-if="row.items.length > 1"> 等 {{ row.items.length }} 种</template>
        </span>
      </template>

      <template #amount="{ row }">
        <div class="console-amount">¥{{ formatMoney(row.payAmount) }}</div>
        <small v-if="Number(row.refundAmount) > 0" class="console-muted">
          已退 ¥{{ formatMoney(row.refundAmount) }}
        </small>
      </template>

      <template #status="{ row }">
        <ConsoleStatusTag kind="order" :value="row.status" />
      </template>

      <template #created="{ row }">{{ formatDateTime(row.createdAt) }}</template>

      <template #actions="{ row }">
        <el-button link type="primary" size="small" @click.stop="openDetail(row)">详情</el-button>
      </template>
    </ConsoleDataTable>

    <ConsoleDetailDrawer
      v-model="drawerVisible"
      :title="`订单详情 · ${detail?.orderNo || ''}`"
      :loading="detailLoading"
      :error="detailError"
      :error-request-id="detailRequestId"
      @retry="retryDetail"
    >
      <template v-if="detail">
        <div class="console-alert-row">
          <ConsoleStatusTag kind="order" :value="detail.status" />
          <span class="console-muted">{{ detail.storeName }}</span>
          <span class="console-muted">下单 {{ formatDateTime(detail.createdAt) }}</span>
          <span v-if="Number(detail.refundAmount) > 0" class="console-amount">
            退款 ¥{{ formatMoney(detail.refundAmount) }}
          </span>
        </div>

        <section class="console-detail-section">
          <h4>订单信息</h4>
          <div class="console-detail-grid">
            <div class="console-detail-field">
              <label>订单号</label><span class="console-mono">{{ detail.orderNo }}</span>
            </div>
            <div class="console-detail-field">
              <label>订单状态</label>
              <span><ConsoleStatusTag kind="order" :value="detail.status" /></span>
            </div>
            <div class="console-detail-field">
              <label>买家</label><span>{{ detail.buyerName }}</span>
            </div>
            <div class="console-detail-field">
              <label>手机号</label><span><ConsoleMasked :value="detail.buyerPhone" /></span>
            </div>
            <div class="console-detail-field">
              <label>邮箱</label>
              <span><ConsoleMasked :value="detail.buyerEmail" kind="email" /></span>
            </div>
            <div class="console-detail-field">
              <label>店铺</label><span>{{ detail.storeName }}</span>
            </div>
            <div class="console-detail-field full">
              <label>收货地址</label>
              <span><ConsoleMasked :value="detail.address" kind="address" /></span>
            </div>
            <div v-if="detail.remark" class="console-detail-field full">
              <label>买家备注</label><span>{{ detail.remark }}</span>
            </div>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>商品与金额</h4>
          <el-table :data="detail.items" size="small">
            <el-table-column label="商品" min-width="220">
              <template #default="{ row }">
                <div class="console-product-cell small">
                  <img :src="assetUrl(row.image)" :alt="row.title" />
                  <div>
                    <strong>{{ row.title }}</strong>
                    <span>{{ row.spec }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="单价" width="100" align="right">
              <template #default="{ row }">¥{{ formatMoney(row.price) }}</template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="70" align="right" />
            <el-table-column label="小计" width="110" align="right">
              <template #default="{ row }">
                <span class="console-amount"
                  >¥{{ formatMoney(Number(row.price) * row.quantity) }}</span
                >
              </template>
            </el-table-column>
          </el-table>
          <div style="max-width: 320px; margin: 12px 0 0 auto">
            <div class="console-detail-amount-row">
              <span>商品合计</span><span>¥{{ formatMoney(detail.itemsTotal) }}</span>
            </div>
            <div class="console-detail-amount-row">
              <span>运费</span><span>¥{{ formatMoney(detail.shippingFee) }}</span>
            </div>
            <div class="console-detail-amount-row">
              <span>已退款</span>
              <span class="console-amount">-¥{{ formatMoney(detail.refundAmount) }}</span>
            </div>
            <div class="console-detail-amount-row total">
              <span>买家实付</span><b>¥{{ formatMoney(detail.payAmount) }}</b>
            </div>
          </div>
        </section>

        <section v-if="detail.shipment" class="console-detail-section">
          <h4>物流轨迹</h4>
          <div class="console-detail-field">
            <label>物流单</label>
            <span>{{ detail.shipment.carrier }} · {{ detail.shipment.trackingNo }}</span>
          </div>
          <ul class="console-timeline" style="margin-top: 10px">
            <li v-for="track in detail.shipment.tracks" :key="track.time + track.text">
              {{ track.text }}<small>{{ formatDateTime(track.time) }}</small>
            </li>
          </ul>
        </section>

        <section class="console-detail-section">
          <h4>状态流转</h4>
          <ul class="console-timeline">
            <li v-for="log in detail.statusLogs.slice().reverse()" :key="log.time + log.action">
              {{ log.action }} · {{ log.status }}
              <div v-if="log.note" class="console-muted">{{ log.note }}</div>
              <small>{{ formatDateTime(log.time) }} · {{ log.operator }}</small>
            </li>
          </ul>
        </section>
      </template>

      <template #footer>
        <el-button @click="drawerVisible = false">关闭</el-button>
      </template>
    </ConsoleDetailDrawer>
  </div>
</template>
