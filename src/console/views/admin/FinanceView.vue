<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleFilterBar from '@/console/components/ConsoleFilterBar.vue'
import ConsoleStatusTabs from '@/console/components/ConsoleStatusTabs.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleKpiCard from '@/console/components/ConsoleKpiCard.vue'
import ConsoleExportButton from '@/console/components/ConsoleExportButton.vue'
import ConsoleDetailDrawer from '@/console/components/ConsoleDetailDrawer.vue'
import ConsoleReasonDialog from '@/console/components/ConsoleReasonDialog.vue'
import type { TableColumn } from '@/console/components/types'
import {
  adminApi,
  type AdminWithdrawalRow,
  type CommissionSettings,
  type Settlement,
  type SettlementBill,
  type SettlementPreview
} from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { useCompactTable } from '@/console/composables/useCompactTable'
import { useConsoleUi } from '@/console/install'
import { formatDateTime, formatMoney, formatPeriod } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

useConsoleUi()

const auth = useConsoleAuth()
const route = useRoute()
const router = useRouter()
const canManage = computed(() => auth.can('finance:manage') || auth.can('*'))
const activeTab = ref(String(route.query.tab || 'settlements'))
const { compact } = useCompactTable()

watch(
  () => route.query.tab,
  (value) => {
    const next = String(value || 'settlements')
    activeTab.value = ['settlements', 'withdrawals', 'commission'].includes(next)
      ? next
      : 'settlements'
  }
)

const stores = ref<Array<{ id: string; name: string; merchantId: string }>>([])

const settlements = ref<Settlement[]>([])
const settlementTotal = ref(0)
const settlementPage = ref(1)
const settlementPageSize = ref(20)
const settlementStatus = ref('all')
const settlementKeyword = ref('')
const settlementStoreId = ref('')
const settlementLoading = ref(false)
const settlementError = ref('')
const settlementRequestId = ref('')
const settlementCounts = ref<Record<string, number>>({})

const withdrawals = ref<AdminWithdrawalRow[]>([])
const withdrawalTotal = ref(0)
const withdrawalPage = ref(1)
const withdrawalPageSize = ref(20)
const withdrawalStatus = ref('all')
const withdrawalKeyword = ref('')
const withdrawalLoading = ref(false)
const withdrawalError = ref('')
const withdrawalRequestId = ref('')
const withdrawalCounts = ref<Record<string, number>>({})

const acting = ref(false)
const billVisible = ref(false)
const billLoading = ref(false)
const billError = ref('')
const bills = ref<SettlementBill[]>([])
const billSettlement = ref<Settlement | null>(null)

const generateVisible = ref(false)
const generating = ref(false)
const previewLoading = ref(false)
const preview = ref<SettlementPreview | null>(null)
const generateForm = reactive({
  storeId: '',
  range: null as [string, string] | null
})
const generateError = ref('')

const rejectVisible = ref(false)
const rejectTarget = ref<AdminWithdrawalRow | null>(null)

const commission = ref<CommissionSettings | null>(null)
const commissionForm = reactive<CommissionSettings>({
  rate: '5.00',
  cycle: 'T+7',
  minWithdrawal: '100.00',
  autoConfirm: false
})
const commissionLoading = ref(false)
const commissionSaving = ref(false)

const settlementTabs = computed(() => [
  { label: '全部', value: 'all', count: settlementCounts.value.all },
  { label: '待确认', value: 'pending', count: settlementCounts.value.pending },
  { label: '已确认', value: 'confirmed', count: settlementCounts.value.confirmed },
  { label: '已打款', value: 'paid', count: settlementCounts.value.paid }
])
const withdrawalTabs = computed(() => [
  { label: '全部', value: 'all', count: withdrawalCounts.value.all },
  { label: '待审核', value: 'pending', count: withdrawalCounts.value.pending },
  { label: '已通过', value: 'approved', count: withdrawalCounts.value.approved },
  { label: '已驳回', value: 'rejected', count: withdrawalCounts.value.rejected }
])

const settlementDesktopColumns: TableColumn[] = [
  { label: '结算单号', prop: 'settlementNo', minWidth: 135 },
  { label: '店铺', prop: 'storeName', minWidth: 130, showOverflowTooltip: true },
  { label: '结算周期', slot: 'period', width: 190 },
  { label: '订单数', prop: 'orderCount', width: 65, align: 'right' },
  { label: '订单金额', slot: 'total', width: 100, align: 'right' },
  { label: '佣金', slot: 'commission', width: 85, align: 'right' },
  { label: '退款扣减', slot: 'deduct', width: 95, align: 'right' },
  { label: '应结金额', slot: 'payable', width: 100, align: 'right' },
  { label: '状态', slot: 'status', width: 88 },
  { label: '操作', slot: 'actions', width: 105, fixed: 'right' }
]
const settlementCompactColumns: TableColumn[] = [
  { label: '结算单号', prop: 'settlementNo', minWidth: 125 },
  { label: '店铺', prop: 'storeName', minWidth: 130, showOverflowTooltip: true },
  { label: '结算周期', slot: 'period', width: 205 },
  { label: '订单金额', slot: 'total', width: 100, align: 'right' },
  { label: '应结金额', slot: 'payable', width: 100, align: 'right' },
  { label: '状态', slot: 'status', width: 90 },
  { label: '操作', slot: 'actions', width: 100, fixed: 'right' }
]
const settlementColumns = computed<TableColumn[]>(() =>
  compact.value ? settlementCompactColumns : settlementDesktopColumns
)
const withdrawalDesktopColumns: TableColumn[] = [
  { label: '提现单号', prop: 'id', minWidth: 125 },
  { label: '商家 / 店铺', slot: 'merchant', minWidth: 150 },
  { label: '提现金额', slot: 'amount', width: 100, align: 'right' },
  { label: '收款账户', slot: 'account', minWidth: 200 },
  { label: '状态', slot: 'status', width: 88 },
  { label: '申请时间', slot: 'created', width: 140 },
  { label: '处理时间', slot: 'handled', width: 140 },
  { label: '操作', slot: 'actions', width: 105, fixed: 'right' }
]
const withdrawalCompactColumns: TableColumn[] = [
  { label: '提现单号', prop: 'id', minWidth: 125 },
  { label: '商家 / 店铺', slot: 'merchant', minWidth: 150 },
  { label: '提现金额', slot: 'amount', width: 100, align: 'right' },
  { label: '收款账户', slot: 'account', minWidth: 200 },
  { label: '状态', slot: 'status', width: 90 },
  { label: '申请时间', slot: 'created', width: 145 },
  { label: '操作', slot: 'actions', width: 100, fixed: 'right' }
]
const withdrawalColumns = computed<TableColumn[]>(() =>
  compact.value ? withdrawalCompactColumns : withdrawalDesktopColumns
)
const quickRejectReasons = [
  '结算账户信息需与营业执照一致',
  '提现金额异常',
  '存在未处理售后',
  '风控审核未通过'
]

function maskAccountNo(value?: string): string {
  if (!value) return '—'
  if (value.length <= 8) return value
  return `${value.slice(0, 4)} **** **** ${value.slice(-4)}`
}

async function loadStores(): Promise<void> {
  try {
    stores.value = await adminApi.storeOptions()
  } catch {
    stores.value = []
  }
}

async function loadSettlementCounts(): Promise<void> {
  try {
    settlementCounts.value = await adminApi.settlementStats()
  } catch {
    settlementCounts.value = {}
  }
}

async function loadSettlements(): Promise<void> {
  settlementLoading.value = true
  settlementError.value = ''
  settlementRequestId.value = ''
  try {
    const result = await adminApi.settlements({
      page: settlementPage.value,
      page_size: settlementPageSize.value,
      status: settlementStatus.value,
      keyword: settlementKeyword.value,
      storeId: settlementStoreId.value
    })
    settlements.value = result.items
    settlementTotal.value = result.pagination.total
    void loadSettlementCounts()
  } catch (err) {
    const state = toErrorState(err)
    settlementError.value = state.message
    settlementRequestId.value = state.requestId
  } finally {
    settlementLoading.value = false
  }
}

async function loadWithdrawalCounts(): Promise<void> {
  try {
    withdrawalCounts.value = await adminApi.withdrawalStats()
  } catch {
    withdrawalCounts.value = {}
  }
}

async function loadWithdrawals(): Promise<void> {
  withdrawalLoading.value = true
  withdrawalError.value = ''
  withdrawalRequestId.value = ''
  try {
    const result = await adminApi.withdrawals({
      page: withdrawalPage.value,
      page_size: withdrawalPageSize.value,
      status: withdrawalStatus.value,
      keyword: withdrawalKeyword.value
    })
    withdrawals.value = result.items
    withdrawalTotal.value = result.pagination.total
    void loadWithdrawalCounts()
  } catch (err) {
    const state = toErrorState(err)
    withdrawalError.value = state.message
    withdrawalRequestId.value = state.requestId
  } finally {
    withdrawalLoading.value = false
  }
}

async function loadCommission(): Promise<void> {
  commissionLoading.value = true
  try {
    commission.value = await adminApi.commission()
    commissionForm.rate = commission.value.rate
    commissionForm.cycle = commission.value.cycle
    commissionForm.minWithdrawal = commission.value.minWithdrawal
    commissionForm.autoConfirm = commission.value.autoConfirm
  } catch (err) {
    ElMessage.error(toErrorState(err, '佣金设置加载失败').message)
  } finally {
    commissionLoading.value = false
  }
}

function refreshAll(): void {
  void loadSettlements()
  void loadWithdrawals()
  void loadCommission()
}

function switchTab(value: string | number): void {
  const tab = String(value)
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

function changeSettlementStatus(value: string): void {
  settlementStatus.value = value
  settlementPage.value = 1
  loadSettlements()
}

function changeWithdrawalStatus(value: string): void {
  withdrawalStatus.value = value
  withdrawalPage.value = 1
  loadWithdrawals()
}

function searchSettlements(): void {
  settlementPage.value = 1
  loadSettlements()
}

function resetSettlements(): void {
  settlementKeyword.value = ''
  settlementStoreId.value = ''
  settlementStatus.value = 'all'
  settlementPage.value = 1
  loadSettlements()
}

function searchWithdrawals(): void {
  withdrawalPage.value = 1
  loadWithdrawals()
}

function resetWithdrawals(): void {
  withdrawalKeyword.value = ''
  withdrawalStatus.value = 'all'
  withdrawalPage.value = 1
  loadWithdrawals()
}

async function openBills(settlement: Settlement): Promise<void> {
  billSettlement.value = settlement
  billVisible.value = true
  billLoading.value = true
  billError.value = ''
  bills.value = []
  try {
    bills.value = await adminApi.settlementBills(settlement.id)
  } catch (err) {
    billError.value = toErrorState(err, '明细加载失败').message
  } finally {
    billLoading.value = false
  }
}

async function confirmSettlement(settlement: Settlement): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认结算单 ${settlement.settlementNo}？确认后进入待打款状态。`,
      '确认结算',
      { type: 'info', confirmButtonText: '确认' }
    )
  } catch {
    return
  }
  acting.value = true
  try {
    await adminApi.confirmSettlement(settlement.id)
    ElMessage.success('结算单已确认')
    await loadSettlements()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

async function paySettlement(settlement: Settlement): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认向「${settlement.storeName}」打款 ¥${formatMoney(settlement.payable)}？`,
      '结算打款',
      { type: 'warning', confirmButtonText: '确认打款' }
    )
  } catch {
    return
  }
  acting.value = true
  try {
    await adminApi.paySettlement(settlement.id)
    ElMessage.success('已标记打款，商家可提现余额已更新')
    await loadSettlements()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

function openGenerate(): void {
  generateForm.storeId = ''
  generateForm.range = null
  preview.value = null
  generateError.value = ''
  generateVisible.value = true
}

async function previewSettlement(): Promise<void> {
  generateError.value = ''
  if (!generateForm.storeId || !generateForm.range) {
    generateError.value = '请选择店铺与结算周期'
    return
  }
  previewLoading.value = true
  preview.value = null
  try {
    preview.value = await adminApi.previewSettlement(
      generateForm.storeId,
      generateForm.range[0],
      generateForm.range[1]
    )
  } catch (err) {
    generateError.value = toErrorState(err, '预览失败').message
  } finally {
    previewLoading.value = false
  }
}

async function generate(): Promise<void> {
  if (!preview.value) return
  generating.value = true
  try {
    await adminApi.generateSettlement(
      preview.value.storeId,
      preview.value.periodStart,
      preview.value.periodEnd
    )
    ElMessage.success('结算单已生成，等待确认')
    generateVisible.value = false
    await loadSettlements()
  } catch (err) {
    generateError.value = toErrorState(err, '生成失败').message
  } finally {
    generating.value = false
  }
}

async function approveWithdrawal(row: AdminWithdrawalRow): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认通过 ${row.merchantName} 的提现 ¥${formatMoney(row.amount)}？该操作会写入高风险日志。`,
      '提现审核通过',
      { type: 'warning', confirmButtonText: '通过' }
    )
  } catch {
    return
  }
  acting.value = true
  try {
    await adminApi.reviewWithdrawal(row.id, 'approve')
    ElMessage.success('提现已通过，冻结金额转为已提现')
    await loadWithdrawals()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

function openReject(row: AdminWithdrawalRow): void {
  rejectTarget.value = row
  rejectVisible.value = true
}

async function confirmReject(reason: string): Promise<void> {
  if (!rejectTarget.value) return
  acting.value = true
  try {
    await adminApi.reviewWithdrawal(rejectTarget.value.id, 'reject', reason)
    ElMessage.success('提现已驳回，冻结金额退回可提现余额')
    rejectVisible.value = false
    await loadWithdrawals()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

async function saveCommission(): Promise<void> {
  commissionSaving.value = true
  try {
    const saved = await adminApi.saveCommission({
      rate: commissionForm.rate,
      cycle: commissionForm.cycle,
      minWithdrawal: commissionForm.minWithdrawal,
      autoConfirm: commissionForm.autoConfirm
    })
    commission.value = saved
    ElMessage.success('佣金与结算规则已保存，变更已记录日志')
  } catch (err) {
    ElMessage.error(toErrorState(err, '保存失败').message)
  } finally {
    commissionSaving.value = false
  }
}

const settlementExportRows = computed(() =>
  settlements.value.map((item) => ({
    settlementNo: item.settlementNo,
    storeName: item.storeName,
    period: formatPeriod(item.periodStart, item.periodEnd),
    orderCount: item.orderCount,
    ordersTotal: item.ordersTotal,
    commission: item.commission,
    refundDeduct: item.refundDeduct,
    payable: item.payable,
    status: item.status
  }))
)
const withdrawalExportRows = computed(() =>
  withdrawals.value.map((item) => ({
    merchant: item.merchantName,
    store: item.storeName,
    amount: item.amount,
    account: `${item.accountName} ${maskAccountNo(item.accountNo)}`,
    status: item.status,
    createdAt: formatDateTime(item.createdAt),
    reason: item.reason || ''
  }))
)

onMounted(() => {
  void loadStores()
  void loadSettlements()
  void loadWithdrawals()
  void loadCommission()
})
</script>

<template>
  <div>
    <ConsolePageHeader
      title="财务管理"
      description="平台结算、提现审核与佣金规则；提现审核与佣金调整属于高风险操作。"
    >
      <template #actions>
        <el-button @click="refreshAll">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
        <el-button v-if="canManage" type="primary" @click="openGenerate">
          <el-icon><Plus /></el-icon>生成结算单
        </el-button>
      </template>
    </ConsolePageHeader>

    <div
      v-loading="settlementLoading || withdrawalLoading || commissionLoading"
      class="console-kpi-grid"
      style="grid-template-columns: repeat(4, minmax(0, 1fr))"
    >
      <ConsoleKpiCard
        label="待确认结算"
        :value="String(settlementCounts.pending ?? '—')"
        hint="需财务确认后打款"
        tone="gold"
      />
      <ConsoleKpiCard
        label="已确认待打款"
        :value="String(settlementCounts.confirmed ?? '—')"
        hint="确认后执行打款"
      />
      <ConsoleKpiCard
        label="待审核提现"
        :value="String(withdrawalCounts.pending ?? '—')"
        hint="高风险审核操作"
        tone="gold"
      />
      <ConsoleKpiCard
        label="平台佣金率"
        :value="`${commission?.rate ?? '—'}%`"
        hint="结算单按此比例扣除"
        tone="green"
      />
    </div>

    <div class="console-card" style="margin-top: 14px">
      <el-tabs :model-value="activeTab" @tab-change="switchTab">
        <el-tab-pane label="结算管理" name="settlements" />
        <el-tab-pane label="提现审核" name="withdrawals" />
        <el-tab-pane label="佣金设置" name="commission" />
      </el-tabs>

      <div v-if="activeTab === 'settlements'">
        <ConsoleFilterBar
          :loading="settlementLoading"
          @search="searchSettlements"
          @reset="resetSettlements"
        >
          <el-form-item label="关键词">
            <el-input
              v-model="settlementKeyword"
              clearable
              placeholder="结算单号 / 店铺"
              style="width: 210px"
              @keyup.enter="searchSettlements"
            />
          </el-form-item>
          <el-form-item label="店铺">
            <el-select
              v-model="settlementStoreId"
              clearable
              filterable
              placeholder="全部店铺"
              style="width: 190px"
            >
              <el-option
                v-for="item in stores"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </ConsoleFilterBar>
        <ConsoleStatusTabs
          :tabs="settlementTabs"
          :model-value="settlementStatus"
          @update:model-value="changeSettlementStatus"
        />
        <div style="display: flex; justify-content: flex-end; margin-bottom: 10px">
          <ConsoleExportButton
            filename="平台结算单.csv"
            :rows="settlementExportRows"
            :headers="[
              { key: 'settlementNo', label: '结算单号' },
              { key: 'storeName', label: '店铺' },
              { key: 'period', label: '结算周期' },
              { key: 'orderCount', label: '订单数' },
              { key: 'ordersTotal', label: '订单金额' },
              { key: 'commission', label: '佣金' },
              { key: 'refundDeduct', label: '退款扣减' },
              { key: 'payable', label: '应结金额' },
              { key: 'status', label: '状态' }
            ]"
          />
        </div>
        <ConsoleDataTable
          :columns="settlementColumns"
          :rows="settlements"
          :loading="settlementLoading"
          :error="settlementError"
          :error-request-id="settlementRequestId"
          :total="settlementTotal"
          :page="settlementPage"
          :page-size="settlementPageSize"
          empty-text="暂无结算单"
          @row-click="(row: any) => openBills(row as Settlement)"
          @update:page="
            (value: number) => {
              settlementPage = value
              loadSettlements()
            }
          "
          @update:page-size="
            (value: number) => {
              settlementPageSize = value
              settlementPage = 1
              loadSettlements()
            }
          "
          @retry="loadSettlements"
        >
          <template #period="{ row }"
            ><span class="console-period">{{
              formatPeriod(row.periodStart, row.periodEnd)
            }}</span></template
          >
          <template #total="{ row }">¥{{ formatMoney(row.ordersTotal) }}</template>
          <template #commission="{ row }">
            <span class="console-muted">-¥{{ formatMoney(row.commission) }}</span>
          </template>
          <template #deduct="{ row }">
            <span class="console-muted">-¥{{ formatMoney(row.refundDeduct) }}</span>
          </template>
          <template #payable="{ row }">
            <span class="console-amount">¥{{ formatMoney(row.payable) }}</span>
          </template>
          <template #status="{ row }">
            <ConsoleStatusTag kind="settlement" :value="row.status" />
          </template>
          <template #actions="{ row }">
            <div class="console-inline-actions" style="flex-wrap: nowrap" @click.stop>
              <el-button link type="primary" size="small" @click="openBills(row)">明细</el-button>
              <template v-if="canManage">
                <el-button
                  v-if="row.status === 'pending'"
                  link
                  type="primary"
                  size="small"
                  :disabled="acting"
                  @click="confirmSettlement(row)"
                >
                  确认
                </el-button>
                <el-button
                  v-if="row.status === 'confirmed'"
                  link
                  type="success"
                  size="small"
                  :disabled="acting"
                  @click="paySettlement(row)"
                >
                  打款
                </el-button>
              </template>
            </div>
          </template>
        </ConsoleDataTable>
      </div>

      <div v-else-if="activeTab === 'withdrawals'">
        <ConsoleFilterBar
          :loading="withdrawalLoading"
          @search="searchWithdrawals"
          @reset="resetWithdrawals"
        >
          <el-form-item label="关键词">
            <el-input
              v-model="withdrawalKeyword"
              clearable
              placeholder="商家 / 开户名 / 银行"
              style="width: 230px"
              @keyup.enter="searchWithdrawals"
            />
          </el-form-item>
        </ConsoleFilterBar>
        <ConsoleStatusTabs
          :tabs="withdrawalTabs"
          :model-value="withdrawalStatus"
          @update:model-value="changeWithdrawalStatus"
        />
        <div style="display: flex; justify-content: flex-end; margin-bottom: 10px">
          <ConsoleExportButton
            filename="平台提现审核.csv"
            :rows="withdrawalExportRows"
            :headers="[
              { key: 'merchant', label: '商家' },
              { key: 'store', label: '店铺' },
              { key: 'amount', label: '提现金额' },
              { key: 'account', label: '收款账户' },
              { key: 'status', label: '状态' },
              { key: 'createdAt', label: '申请时间' },
              { key: 'reason', label: '备注' }
            ]"
          />
        </div>
        <ConsoleDataTable
          :columns="withdrawalColumns"
          :rows="withdrawals"
          :loading="withdrawalLoading"
          :error="withdrawalError"
          :error-request-id="withdrawalRequestId"
          :total="withdrawalTotal"
          :page="withdrawalPage"
          :page-size="withdrawalPageSize"
          empty-text="暂无提现申请"
          @update:page="
            (value: number) => {
              withdrawalPage = value
              loadWithdrawals()
            }
          "
          @update:page-size="
            (value: number) => {
              withdrawalPageSize = value
              withdrawalPage = 1
              loadWithdrawals()
            }
          "
          @retry="loadWithdrawals"
        >
          <template #merchant="{ row }">
            <div class="console-two-line">
              <strong>{{ row.merchantName }}</strong>
              <span>{{ row.storeName }}</span>
            </div>
          </template>
          <template #amount="{ row }">
            <span class="console-amount">¥{{ formatMoney(row.amount) }}</span>
          </template>
          <template #account="{ row }">
            <div class="console-two-line">
              <strong>{{ row.accountName }}</strong>
              <span>{{ row.bankName }} · {{ maskAccountNo(row.accountNo) }}</span>
            </div>
          </template>
          <template #status="{ row }">
            <ConsoleStatusTag kind="withdrawal" :value="row.status" />
          </template>
          <template #created="{ row }">{{ formatDateTime(row.createdAt) }}</template>
          <template #handled="{ row }">{{ formatDateTime(row.handledAt) }}</template>
          <template #actions="{ row }">
            <div class="console-inline-actions" style="flex-wrap: nowrap" @click.stop>
              <template v-if="canManage && row.status === 'pending'">
                <el-button
                  link
                  type="success"
                  size="small"
                  :disabled="acting"
                  @click="approveWithdrawal(row)"
                >
                  通过
                </el-button>
                <el-button
                  link
                  type="danger"
                  size="small"
                  :disabled="acting"
                  @click="openReject(row)"
                >
                  驳回
                </el-button>
              </template>
              <span v-else class="console-muted">{{ row.reason || '—' }}</span>
            </div>
          </template>
        </ConsoleDataTable>
      </div>

      <div v-else>
        <div v-loading="commissionLoading" style="max-width: 620px">
          <el-form label-position="top">
            <div class="console-form-grid">
              <el-form-item label="平台佣金比例（%）">
                <el-input
                  v-model="commissionForm.rate"
                  inputmode="decimal"
                  :disabled="!canManage"
                />
              </el-form-item>
              <el-form-item label="结算周期">
                <el-select
                  v-model="commissionForm.cycle"
                  :disabled="!canManage"
                  style="width: 100%"
                >
                  <el-option label="T+7（交易完成 7 天后可结算）" value="T+7" />
                  <el-option label="T+15" value="T+15" />
                  <el-option label="月结" value="monthly" />
                </el-select>
              </el-form-item>
              <el-form-item label="最低提现金额（元）">
                <el-input
                  v-model="commissionForm.minWithdrawal"
                  inputmode="decimal"
                  :disabled="!canManage"
                />
              </el-form-item>
              <el-form-item label="结算单自动确认">
                <el-switch v-model="commissionForm.autoConfirm" :disabled="!canManage" />
              </el-form-item>
            </div>
            <el-alert
              type="warning"
              :closable="false"
              show-icon
              title="佣金与结算规则调整属于高风险操作，会写入平台操作日志。演示环境仅影响本地 mock 计算。"
              style="margin-bottom: 14px"
            />
            <el-button
              v-if="canManage"
              type="primary"
              :loading="commissionSaving"
              @click="saveCommission"
            >
              保存佣金设置
            </el-button>
            <p v-else class="console-muted">当前账号仅有财务查看权限，不能修改佣金设置。</p>
          </el-form>
        </div>
      </div>
    </div>

    <ConsoleDetailDrawer
      v-model="billVisible"
      :title="`结算明细 · ${billSettlement?.settlementNo || ''}`"
      :loading="billLoading"
      :error="billError"
      @retry="billSettlement && openBills(billSettlement)"
    >
      <template v-if="billSettlement">
        <div class="console-summary-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr))">
          <div class="console-summary-item">
            <span>店铺</span><strong style="font-size: 14px">{{ billSettlement.storeName }}</strong>
          </div>
          <div class="console-summary-item">
            <span>应结金额</span>
            <strong class="amount">¥{{ formatMoney(billSettlement.payable) }}</strong>
          </div>
        </div>
        <el-table :data="bills" style="margin-top: 14px" empty-text="暂无明细">
          <el-table-column prop="orderNo" label="订单号" min-width="150" />
          <el-table-column prop="storeOrderNo" label="店铺订单号" min-width="150" />
          <el-table-column label="支付时间" width="150">
            <template #default="{ row }">{{ formatDateTime(row.paidAt) }}</template>
          </el-table-column>
          <el-table-column label="订单金额" width="110" align="right">
            <template #default="{ row }">¥{{ formatMoney(row.amount) }}</template>
          </el-table-column>
          <el-table-column label="佣金" width="100" align="right">
            <template #default="{ row }">-¥{{ formatMoney(row.commission) }}</template>
          </el-table-column>
          <el-table-column label="应结" width="110" align="right">
            <template #default="{ row }">
              <span class="console-amount">¥{{ formatMoney(row.payable) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </template>
      <template #footer>
        <el-button @click="billVisible = false">关闭</el-button>
      </template>
    </ConsoleDetailDrawer>

    <el-dialog v-model="generateVisible" title="生成结算单" width="600px">
      <el-form label-position="top">
        <el-form-item label="店铺" required>
          <el-select
            v-model="generateForm.storeId"
            filterable
            placeholder="选择需要结算的店铺"
            style="width: 100%"
            @change="preview = null"
          >
            <el-option v-for="item in stores" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="结算周期" required>
          <el-date-picker
            v-model="generateForm.range"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 100%"
            @change="preview = null"
          />
        </el-form-item>
        <div class="console-inline-actions">
          <el-button :loading="previewLoading" @click="previewSettlement">预览结算数据</el-button>
        </div>
        <p v-if="generateError" class="console-login-error" style="margin-top: 10px">
          {{ generateError }}
        </p>
        <div v-if="preview" style="margin-top: 12px">
          <div class="console-summary-grid">
            <div class="console-summary-item">
              <span>订单数</span><strong>{{ preview.orderCount }}</strong>
            </div>
            <div class="console-summary-item">
              <span>订单金额</span
              ><strong style="font-size: 16px">¥{{ formatMoney(preview.ordersTotal) }}</strong>
            </div>
            <div class="console-summary-item">
              <span>平台佣金</span
              ><strong style="font-size: 16px">¥{{ formatMoney(preview.commission) }}</strong>
            </div>
            <div class="console-summary-item">
              <span>应结金额</span>
              <strong class="amount" style="font-size: 18px"
                >¥{{ formatMoney(preview.payable) }}</strong
              >
            </div>
          </div>
          <div class="console-audit-tip">
            结算周期：{{ preview.periodStart }} 至
            {{ preview.periodEnd }}；演示环境按当前佣金率计算。
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="generateVisible = false">取消</el-button>
        <el-button type="primary" :loading="generating" :disabled="!preview" @click="generate">
          生成结算单
        </el-button>
      </template>
    </el-dialog>

    <ConsoleReasonDialog
      v-model:visible="rejectVisible"
      title="驳回提现"
      label="驳回原因"
      :quick-reasons="quickRejectReasons"
      :min-length="4"
      danger
      :loading="acting"
      @confirm="confirmReject"
    />
  </div>
</template>
