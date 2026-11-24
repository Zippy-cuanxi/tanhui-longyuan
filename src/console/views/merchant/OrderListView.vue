<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleFilterBar from '@/console/components/ConsoleFilterBar.vue'
import ConsoleStatusTabs from '@/console/components/ConsoleStatusTabs.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleMasked from '@/console/components/ConsoleMasked.vue'
import ConsoleExportButton from '@/console/components/ConsoleExportButton.vue'
import type { TableColumn } from '@/console/components/types'
import ShipDrawer from './components/ShipDrawer.vue'
import { useCompactTable } from '@/console/composables/useCompactTable'
import { merchantApi, type Order } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import {
  downloadCsv,
  formatDateTime,
  formatMoney,
  hoursUntil,
  isOverdue,
  maskPhone
} from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const route = useRoute()
const router = useRouter()
const merchantId = computed(() => auth.merchantAccount?.id || '')

const query = reactive({
  keyword: '',
  status: String(route.query.status || 'all'),
  page: 1,
  page_size: 20
})
const dateRange = ref<[string, string] | null>(null)
const items = ref<Order[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const requestId = ref('')
const counts = ref<Record<string, number>>({})
const selected = ref<Order[]>([])
const shipVisible = ref(false)
const shipOrder = ref<Order | null>(null)
const { compact } = useCompactTable()

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

const desktopColumns: TableColumn[] = [
  { label: '订单信息', slot: 'order', minWidth: 145 },
  { label: '买家', slot: 'buyer', minWidth: 95 },
  { label: '商品', slot: 'items', minWidth: 145 },
  { label: '实付金额', slot: 'amount', width: 95, align: 'right' },
  { label: '订单状态', slot: 'status', width: 100 },
  { label: '发货时效', slot: 'deadline', width: 105 },
  { label: '下单时间', slot: 'created', width: 138 },
  { label: '操作', slot: 'actions', width: 100, fixed: 'right' }
]
const compactColumns: TableColumn[] = [
  { label: '订单信息', slot: 'order', minWidth: 150 },
  { label: '买家', slot: 'buyer', minWidth: 100 },
  { label: '实付金额', slot: 'amount', width: 105, align: 'right' },
  { label: '订单状态', slot: 'status', width: 105 },
  { label: '发货时效', slot: 'deadline', width: 120 },
  { label: '下单时间', slot: 'created', width: 148 },
  { label: '操作', slot: 'actions', width: 115, fixed: 'right' }
]
const columns = computed<TableColumn[]>(() => (compact.value ? compactColumns : desktopColumns))

const exportRows = computed(() =>
  items.value.map((item) => ({
    orderNo: item.orderNo,
    buyer: item.buyerName,
    phone: maskPhone(item.buyerPhone),
    items: item.items.map((product) => `${product.title}×${product.quantity}`).join('；'),
    payAmount: item.payAmount,
    status: item.status,
    createdAt: formatDateTime(item.createdAt)
  }))
)

async function loadCounts(): Promise<void> {
  try {
    counts.value = await merchantApi.orderStats(merchantId.value)
  } catch {
    counts.value = {}
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const result = await merchantApi.orders(merchantId.value, {
      page: query.page,
      page_size: query.page_size,
      status: query.status,
      keyword: query.keyword,
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
  query.page = 1
  dateRange.value = null
  load()
}

function changeTab(value: string): void {
  query.status = value
  query.page = 1
  router.replace({ path: route.path, query: value === 'all' ? {} : { status: value } })
  load()
}

function openDetail(row: Record<string, unknown>): void {
  const order = row as unknown as Order
  router.push(`/console/merchant/orders/${order.id}`)
}

function openShip(row: Order): void {
  shipOrder.value = row
  shipVisible.value = true
}

function onShipped(): void {
  load()
}

function deadlineMeta(order: Order): { text: string; danger: boolean } {
  if (order.status !== 'paid' || !order.shipDeadline) return { text: '—', danger: false }
  const hours = hoursUntil(order.shipDeadline)
  if (isOverdue(order.shipDeadline)) {
    return { text: `已超时 ${Math.abs(hours)} 小时`, danger: true }
  }
  return { text: `剩余 ${hours} 小时`, danger: hours <= 6 }
}

function onSelectionChange(rows: Record<string, any>[]): void {
  selected.value = rows as Order[]
}

function exportSelected(): void {
  if (!selected.value.length) return
  downloadCsv(
    '商家订单-所选.csv',
    selected.value.map((item) => ({
      orderNo: item.orderNo,
      buyer: item.buyerName,
      phone: maskPhone(item.buyerPhone),
      payAmount: item.payAmount,
      status: item.status,
      createdAt: formatDateTime(item.createdAt)
    })),
    [
      { key: 'orderNo', label: '订单号' },
      { key: 'buyer', label: '买家' },
      { key: 'phone', label: '手机号' },
      { key: 'payAmount', label: '实付金额' },
      { key: 'status', label: '状态' },
      { key: 'createdAt', label: '下单时间' }
    ]
  )
  ElMessage.success(`已导出 ${selected.value.length} 条所选订单`)
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="订单管理"
      description="查看订单、核对收货信息，并在承诺时效内完成发货。"
    >
      <template #actions>
        <ConsoleExportButton
          filename="商家订单.csv"
          :rows="exportRows"
          :headers="[
            { key: 'orderNo', label: '订单号' },
            { key: 'buyer', label: '买家' },
            { key: 'phone', label: '手机号' },
            { key: 'items', label: '商品' },
            { key: 'payAmount', label: '实付金额' },
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
          placeholder="订单号 / 买家 / 手机号"
          style="width: 220px"
          @keyup.enter="search"
        />
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
      empty-description="新订单产生后会出现在这里。"
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
          }}<template v-if="row.items.length > 1"> 等 {{ row.items.length }} 件</template>
          <span class="console-muted">
            × {{ row.items.reduce((sum: number, item: any) => sum + item.quantity, 0) }}</span
          >
        </span>
      </template>

      <template #amount="{ row }">
        <span class="console-amount">¥{{ formatMoney(row.payAmount) }}</span>
      </template>

      <template #status="{ row }">
        <ConsoleStatusTag kind="order" :value="row.status" />
      </template>

      <template #deadline="{ row }">
        <span
          :style="{
            color: deadlineMeta(row).danger ? '#D64545' : '#7B8881',
            fontSize: '11px',
            fontWeight: deadlineMeta(row).danger ? 700 : 400
          }"
        >
          {{ deadlineMeta(row).text }}
        </span>
      </template>

      <template #created="{ row }"
        ><span class="console-nowrap">{{ formatDateTime(row.createdAt) }}</span></template
      >

      <template #actions="{ row }">
        <div class="console-inline-actions" @click.stop>
          <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
          <el-button
            v-if="row.status === 'paid'"
            link
            type="primary"
            size="small"
            @click="openShip(row)"
          >
            发货
          </el-button>
        </div>
      </template>
    </ConsoleDataTable>

    <ShipDrawer v-model="shipVisible" :order="shipOrder" @shipped="onShipped" />
  </div>
</template>
