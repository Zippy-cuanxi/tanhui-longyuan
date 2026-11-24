<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
import { merchantApi, type Aftersale } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { downloadCsv, formatDateTime, formatMoney, maskPhone } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const merchantId = computed(() => auth.merchantAccount?.id || '')

const query = reactive({ keyword: '', status: 'all', page: 1, page_size: 20 })
const items = ref<Aftersale[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const requestId = ref('')
const counts = ref<Record<string, number>>({})
const selected = ref<Aftersale[]>([])
const drawerVisible = ref(false)
const active = ref<Aftersale | null>(null)
const rejectVisible = ref(false)
const rejectTarget = ref<Aftersale | null>(null)
const acting = ref(false)

const tabs = computed(() => [
  { label: '全部', value: 'all', count: counts.value.all },
  { label: '待处理', value: 'requested', count: counts.value.requested },
  { label: '平台仲裁', value: 'arbitrating', count: counts.value.arbitrating },
  { label: '已退款', value: 'refunded', count: counts.value.refunded },
  { label: '已驳回', value: 'rejected', count: counts.value.rejected }
])

const columns: TableColumn[] = [
  { label: '退款单号 / 订单号', slot: 'refund', minWidth: 175 },
  { label: '买家', slot: 'buyer', minWidth: 100 },
  { label: '退款金额', slot: 'amount', width: 90, align: 'right' },
  { label: '退款原因', prop: 'reason', minWidth: 120, showOverflowTooltip: true },
  { label: '状态', slot: 'status', width: 90 },
  { label: '申请时间', slot: 'created', width: 138 },
  { label: '操作', slot: 'actions', width: 135, fixed: 'right' }
]

const rejectQuickReasons = [
  '商品已拆封影响二次销售',
  '超过平台售后时限',
  '买家举证不足',
  '不符合平台退款规则'
]

const exportRows = computed(() =>
  items.value.map((item) => ({
    refundNo: item.refundNo,
    orderNo: item.orderNo,
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
    counts.value = await merchantApi.aftersaleStats(merchantId.value)
  } catch {
    counts.value = {}
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const result = await merchantApi.aftersales(merchantId.value, {
      page: query.page,
      page_size: query.page_size,
      status: query.status,
      keyword: query.keyword
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
  load()
}

function changeTab(value: string): void {
  query.status = value
  query.page = 1
  load()
}

function openDetail(row: Record<string, unknown>): void {
  active.value = row as unknown as Aftersale
  drawerVisible.value = true
}

async function approve(row: Aftersale): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认同意退款 ¥${formatMoney(row.amount)}？同意后订单将进入退款完成状态，结算金额同步扣减。`,
      '同意退款',
      { type: 'warning', confirmButtonText: '同意退款' }
    )
  } catch {
    return
  }
  acting.value = true
  try {
    const updated = await merchantApi.handleAftersale(merchantId.value, row.id, 'approve')
    ElMessage.success('已同意退款')
    if (active.value?.id === updated.id) active.value = updated
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

function openReject(row: Aftersale): void {
  rejectTarget.value = row
  rejectVisible.value = true
}

async function confirmReject(reason: string): Promise<void> {
  if (!rejectTarget.value) return
  acting.value = true
  try {
    const updated = await merchantApi.handleAftersale(
      merchantId.value,
      rejectTarget.value.id,
      'reject',
      reason
    )
    ElMessage.success('已拒绝退款，售后单进入平台仲裁')
    rejectVisible.value = false
    if (active.value?.id === updated.id) active.value = updated
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

function onSelectionChange(rows: Record<string, any>[]): void {
  selected.value = rows as Aftersale[]
}

function exportSelected(): void {
  if (!selected.value.length) return
  downloadCsv(
    '售后单-所选.csv',
    selected.value.map((item) => ({
      refundNo: item.refundNo,
      orderNo: item.orderNo,
      buyer: item.buyerName,
      amount: item.amount,
      reason: item.reason,
      status: item.status,
      createdAt: formatDateTime(item.createdAt)
    })),
    [
      { key: 'refundNo', label: '退款单号' },
      { key: 'orderNo', label: '订单号' },
      { key: 'buyer', label: '买家' },
      { key: 'amount', label: '退款金额' },
      { key: 'reason', label: '退款原因' },
      { key: 'status', label: '状态' },
      { key: 'createdAt', label: '申请时间' }
    ]
  )
  ElMessage.success(`已导出 ${selected.value.length} 条售后单`)
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="售后处理"
      description="买家退款申请需及时处理；拒绝退款后售后单进入平台仲裁。"
    >
      <template #actions>
        <ConsoleExportButton
          filename="商家售后单.csv"
          :rows="exportRows"
          :headers="[
            { key: 'refundNo', label: '退款单号' },
            { key: 'orderNo', label: '订单号' },
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
          placeholder="退款单号 / 订单号"
          style="width: 230px"
          @keyup.enter="search"
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
      empty-text="暂无售后单"
      :empty-image="assetUrl('/console-assets/images/empty-orders.webp')"
      empty-description="买家发起退款后会展示在这里。"
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
        <el-button size="small" plain @click="exportSelected">导出所选售后单</el-button>
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
          <template v-if="row.status === 'requested'">
            <el-button link type="success" size="small" :loading="acting" @click="approve(row)">
              同意
            </el-button>
            <el-button link type="danger" size="small" :disabled="acting" @click="openReject(row)">
              拒绝
            </el-button>
          </template>
        </div>
      </template>
    </ConsoleDataTable>

    <ConsoleDetailDrawer v-model="drawerVisible" :title="`售后详情 · ${active?.refundNo || ''}`">
      <template v-if="active">
        <div class="console-alert-row">
          <ConsoleStatusTag kind="aftersale" :value="active.status" />
          <span class="console-muted">申请时间：{{ formatDateTime(active.createdAt) }}</span>
          <span v-if="active.status === 'arbitrating'" class="console-muted">
            商家已拒绝，等待平台仲裁
          </span>
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
          <h4>退款原因与凭证</h4>
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
              style="width: 82px; height: 82px; border-radius: 8px"
              preview-teleported
            />
            <span v-if="!active.evidence.length" class="console-image-placeholder">无凭证</span>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>处理记录</h4>
          <div v-if="active.merchantReason" class="console-detail-field">
            <label>商家理由</label><span>{{ active.merchantReason }}</span>
          </div>
          <div v-if="active.adminReason" class="console-detail-field">
            <label>平台裁决</label><span>{{ active.adminReason }}</span>
          </div>
          <div v-if="!active.merchantReason && !active.adminReason" class="console-muted">
            尚未处理，请核实商品与凭证后尽快响应买家。
          </div>
          <div v-if="active.handledAt" class="console-muted" style="margin-top: 8px">
            最近处理时间：{{ formatDateTime(active.handledAt) }}
          </div>
        </section>
      </template>

      <template #footer>
        <template v-if="active?.status === 'requested'">
          <el-button type="danger" plain :disabled="acting" @click="openReject(active)">
            拒绝退款
          </el-button>
          <el-button type="primary" :loading="acting" @click="approve(active)">
            同意退款
          </el-button>
        </template>
        <el-button v-else @click="drawerVisible = false">关闭</el-button>
      </template>
    </ConsoleDetailDrawer>

    <ConsoleReasonDialog
      v-model:visible="rejectVisible"
      title="拒绝退款"
      label="拒绝原因"
      :quick-reasons="rejectQuickReasons"
      :min-length="4"
      danger
      :loading="acting"
      @confirm="confirmReject"
    />
  </div>
</template>
