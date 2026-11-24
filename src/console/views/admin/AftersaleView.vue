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
import ConsoleReasonDialog from '@/console/components/ConsoleReasonDialog.vue'
import type { TableColumn } from '@/console/components/types'
import { adminApi, type Aftersale } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { useConsoleUi } from '@/console/install'
import { formatDateTime, formatMoney, maskPhone } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

useConsoleUi()

const auth = useConsoleAuth()
const canArbitrate = computed(() => auth.can('refund:approve') || auth.can('*'))

const query = reactive({ keyword: '', status: 'all', storeId: '', page: 1, page_size: 20 })
const items = ref<Aftersale[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const requestId = ref('')
const counts = ref<Record<string, number>>({})
const stores = ref<Array<{ id: string; name: string }>>([])
const selected = ref<Aftersale[]>([])

const drawerVisible = ref(false)
const active = ref<Aftersale | null>(null)
const acting = ref(false)
const reasonVisible = ref(false)
const reasonMode = ref<'refund' | 'reject'>('refund')

const tabs = computed(() => [
  { label: '全部', value: 'all', count: counts.value.all },
  { label: '待商家处理', value: 'requested', count: counts.value.requested },
  { label: '平台仲裁', value: 'arbitrating', count: counts.value.arbitrating },
  { label: '已退款', value: 'refunded', count: counts.value.refunded },
  { label: '已驳回', value: 'rejected', count: counts.value.rejected }
])

const columns: TableColumn[] = [
  { label: '退款单 / 订单', slot: 'refund', minWidth: 170 },
  { label: '店铺', prop: 'storeName', minWidth: 120, showOverflowTooltip: true },
  { label: '买家', slot: 'buyer', minWidth: 95 },
  { label: '退款金额', slot: 'amount', width: 85, align: 'right' },
  { label: '退款原因', prop: 'reason', minWidth: 110, showOverflowTooltip: true },
  { label: '状态', slot: 'status', width: 88 },
  { label: '申请时间', slot: 'created', width: 138 },
  { label: '操作', slot: 'actions', width: 100, fixed: 'right' }
]

const reasonQuick = computed(() =>
  reasonMode.value === 'refund'
    ? ['平台核实商品存在质量问题', '商家举证不足', '符合平台退款规则', '买家未收到货']
    : ['买家举证不足', '商品已拆封影响二次销售', '不符合平台退款条件', '已超过售后时效']
)

const exportRows = computed(() =>
  items.value.map((item) => ({
    refundNo: item.refundNo,
    orderNo: item.orderNo,
    storeName: item.storeName,
    buyer: item.buyerName,
    phone: maskPhone(item.buyerPhone),
    amount: item.amount,
    reason: item.reason,
    status: item.status,
    createdAt: formatDateTime(item.createdAt)
  }))
)

async function loadCounts(): Promise<void> {
  try {
    counts.value = await adminApi.aftersaleStats()
  } catch {
    counts.value = {}
  }
}

async function loadStores(): Promise<void> {
  try {
    stores.value = (await adminApi.storeOptions()).map((item) => ({
      id: item.id,
      name: item.name
    }))
  } catch {
    stores.value = []
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const result = await adminApi.aftersales({
      page: query.page,
      page_size: query.page_size,
      status: query.status,
      keyword: query.keyword,
      storeId: query.storeId
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
  load()
}

function changeTab(value: string): void {
  query.status = value
  query.page = 1
  load()
}

function openDetail(row: Record<string, unknown> | Aftersale): void {
  active.value = row as Aftersale
  drawerVisible.value = true
}

function openArbitrate(mode: 'refund' | 'reject', row: Aftersale | null): void {
  if (!row) return
  active.value = row
  reasonMode.value = mode
  reasonVisible.value = true
}

async function confirmArbitrate(reason: string): Promise<void> {
  if (!active.value) return
  acting.value = true
  try {
    const updated = await adminApi.arbitrateAftersale(active.value.id, reasonMode.value, reason)
    ElMessage.success(
      reasonMode.value === 'refund'
        ? '已裁决支持退款，订单与结算金额已更新'
        : '已裁决驳回退款，订单状态已恢复'
    )
    active.value = updated
    reasonVisible.value = false
    drawerVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '裁决失败').message)
  } finally {
    acting.value = false
  }
}

function onSelectionChange(rows: Record<string, any>[]): void {
  selected.value = rows as Aftersale[]
}

onMounted(() => {
  void loadStores()
  void load()
})
</script>

<template>
  <div>
    <ConsolePageHeader
      title="售后仲裁"
      description="商家拒绝退款后进入平台仲裁；裁决属于高风险操作，必须填写理由并记录日志。"
    >
      <template #actions>
        <ConsoleExportButton
          filename="平台售后单.csv"
          :rows="exportRows"
          :headers="[
            { key: 'refundNo', label: '退款单号' },
            { key: 'orderNo', label: '订单号' },
            { key: 'storeName', label: '店铺' },
            { key: 'buyer', label: '买家' },
            { key: 'phone', label: '手机号' },
            { key: 'amount', label: '退款金额' },
            { key: 'reason', label: '退款原因' },
            { key: 'status', label: '状态' },
            { key: 'createdAt', label: '申请时间' }
          ]"
        />
      </template>
    </ConsolePageHeader>

    <ConsoleFilterBar :loading="loading" @search="search" @reset="reset">
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          clearable
          placeholder="退款单 / 订单 / 买家 / 店铺"
          style="width: 250px"
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
      empty-text="暂无售后单"
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
        <span class="console-muted">已选择 {{ selected.length }} 条售后单</span>
      </template>

      <template #refund="{ row }">
        <div class="console-two-line">
          <strong class="console-mono">{{ row.refundNo }}</strong>
          <span class="console-mono">{{ row.orderNo }}</span>
        </div>
      </template>

      <template #buyer="{ row }">
        <div class="console-two-line">
          <strong>{{ row.buyerName }}</strong>
          <span><ConsoleMasked :value="row.buyerPhone" /></span>
        </div>
      </template>

      <template #amount="{ row }">
        <span class="console-amount">¥{{ formatMoney(row.amount) }}</span>
      </template>

      <template #status="{ row }">
        <ConsoleStatusTag kind="aftersale" :value="row.status" />
      </template>

      <template #created="{ row }">{{ formatDateTime(row.createdAt) }}</template>

      <template #actions="{ row }">
        <div class="console-inline-actions" style="flex-wrap: nowrap" @click.stop>
          <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
          <el-button
            v-if="(row.status === 'arbitrating' || row.status === 'requested') && canArbitrate"
            link
            type="warning"
            size="small"
            @click="openArbitrate('refund', row)"
          >
            裁决
          </el-button>
        </div>
      </template>
    </ConsoleDataTable>

    <ConsoleDetailDrawer v-model="drawerVisible" :title="`售后详情 · ${active?.refundNo || ''}`">
      <template v-if="active">
        <div class="console-alert-row">
          <ConsoleStatusTag kind="aftersale" :value="active.status" />
          <span class="console-muted">{{ active.storeName }}</span>
          <span class="console-muted">申请 {{ formatDateTime(active.createdAt) }}</span>
        </div>

        <section class="console-detail-section">
          <h4>订单与买家</h4>
          <div class="console-detail-grid">
            <div class="console-detail-field">
              <label>退款单号</label><span class="console-mono">{{ active.refundNo }}</span>
            </div>
            <div class="console-detail-field">
              <label>订单号</label><span class="console-mono">{{ active.orderNo }}</span>
            </div>
            <div class="console-detail-field">
              <label>买家</label><span>{{ active.buyerName }}</span>
            </div>
            <div class="console-detail-field">
              <label>手机号</label><span><ConsoleMasked :value="active.buyerPhone" /></span>
            </div>
            <div class="console-detail-field">
              <label>订单实付</label><span>¥{{ formatMoney(active.orderPayAmount) }}</span>
            </div>
            <div class="console-detail-field">
              <label>申请退款</label>
              <span class="console-amount">¥{{ formatMoney(active.amount) }}</span>
            </div>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>退款原因与证据</h4>
          <div class="console-detail-field">
            <label>退款原因</label><span>{{ active.reason }}</span>
          </div>
          <div class="console-detail-images" style="margin-top: 10px">
            <el-image
              v-for="(image, index) in active.evidence"
              :key="image + index"
              :src="image"
              :preview-src-list="active.evidence"
              :initial-index="index"
              fit="cover"
              style="width: 92px; height: 92px; border-radius: 8px"
              preview-teleported
            />
            <span v-if="!active.evidence.length" class="console-image-placeholder">无凭证</span>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>商家处理</h4>
          <div class="console-detail-field">
            <label>商家理由</label>
            <span>{{ active.merchantReason || '商家尚未拒绝或未填写' }}</span>
          </div>
          <div v-if="active.handledAt" class="console-muted" style="margin-top: 6px">
            处理时间：{{ formatDateTime(active.handledAt) }}
          </div>
        </section>

        <section v-if="active.adminReason" class="console-detail-section">
          <h4>平台裁决</h4>
          <p class="console-card-note" style="margin: 0">{{ active.adminReason }}</p>
        </section>

        <section class="console-detail-section">
          <h4>裁决提示</h4>
          <p class="console-card-note" style="margin: 0">
            支持退款：订单退款金额增加，按全额 / 部分退款更新订单状态，并从待结算金额中扣减；
            驳回退款：订单恢复到发货前 / 已发货 / 已完成状态，不产生退款。
            两种裁决均会写入高风险操作日志。
          </p>
        </section>
      </template>

      <template #footer>
        <el-button @click="drawerVisible = false">关闭</el-button>
        <template
          v-if="
            (active?.status === 'arbitrating' || active?.status === 'requested') && canArbitrate
          "
        >
          <el-button
            type="danger"
            plain
            :disabled="acting"
            @click="openArbitrate('reject', active)"
          >
            驳回退款
          </el-button>
          <el-button type="primary" :loading="acting" @click="openArbitrate('refund', active)">
            支持退款
          </el-button>
        </template>
      </template>
    </ConsoleDetailDrawer>

    <ConsoleReasonDialog
      v-model:visible="reasonVisible"
      :title="reasonMode === 'refund' ? '裁决：支持退款' : '裁决：驳回退款'"
      label="裁决理由"
      :quick-reasons="reasonQuick"
      :min-length="4"
      :danger="reasonMode === 'reject'"
      :loading="acting"
      @confirm="confirmArbitrate"
    />
  </div>
</template>
