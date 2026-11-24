<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleKpiCard from '@/console/components/ConsoleKpiCard.vue'
import ConsoleStatusTabs from '@/console/components/ConsoleStatusTabs.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleMoney from '@/console/components/ConsoleMoney.vue'
import ConsoleExportButton from '@/console/components/ConsoleExportButton.vue'
import ConsoleDetailDrawer from '@/console/components/ConsoleDetailDrawer.vue'
import ConsoleErrorState from '@/console/components/ConsoleErrorState.vue'
import type { TableColumn } from '@/console/components/types'
import {
  merchantApi,
  type MerchantFinanceOverview,
  type Settlement,
  type SettlementAccount,
  type SettlementBill,
  type Withdrawal
} from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { useCompactTable } from '@/console/composables/useCompactTable'
import { formatDateTime, formatMoney, formatPeriod } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const route = useRoute()
const router = useRouter()
const merchantId = computed(() => auth.merchantAccount?.id || '')
const activeTab = ref(String(route.query.tab || 'overview'))
const { compact } = useCompactTable()

watch(
  () => route.query.tab,
  (value) => {
    const next = String(value || 'overview')
    activeTab.value = ['overview', 'bills', 'withdraw', 'records', 'account'].includes(next)
      ? next
      : 'overview'
  }
)

const overview = ref<MerchantFinanceOverview | null>(null)
const overviewLoading = ref(false)
const overviewError = ref('')
const overviewRequestId = ref('')

const settlements = ref<Settlement[]>([])
const settlementTotal = ref(0)
const settlementPage = ref(1)
const settlementPageSize = ref(20)
const settlementStatus = ref('all')
const settlementLoading = ref(false)
const settlementError = ref('')
const settlementRequestId = ref('')
const settlementCounts = ref<Record<string, number>>({})

const withdrawals = ref<Withdrawal[]>([])
const withdrawalTotal = ref(0)
const withdrawalPage = ref(1)
const withdrawalPageSize = ref(20)
const withdrawalStatus = ref('all')
const withdrawalLoading = ref(false)
const withdrawalError = ref('')
const withdrawalRequestId = ref('')
const withdrawalCounts = ref<Record<string, number>>({})

const account = ref<SettlementAccount | null>(null)
const accountFormRef = ref<FormInstance>()
const accountForm = reactive({
  accountName: '',
  bankName: '',
  accountNo: '',
  branch: ''
})
const accountSaving = ref(false)
const accountLoading = ref(false)
const accountError = ref('')
const accountRules: FormRules = {
  accountName: [{ required: true, message: '请输入开户名称', trigger: 'blur' }],
  bankName: [{ required: true, message: '请输入开户银行', trigger: 'blur' }],
  accountNo: [
    { required: true, message: '请输入银行账号', trigger: 'blur' },
    { pattern: /^\d{8,24}$/, message: '账号应为 8–24 位数字', trigger: 'blur' }
  ],
  branch: [{ required: true, message: '请输入开户支行', trigger: 'blur' }]
}

const withdrawForm = reactive({ amount: '' })
const withdrawing = ref(false)
const withdrawError = ref('')

const billVisible = ref(false)
const billLoading = ref(false)
const billError = ref('')
const bills = ref<SettlementBill[]>([])
const billSettlement = ref<Settlement | null>(null)

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
  { label: '结算单号', prop: 'settlementNo', minWidth: 130 },
  { label: '结算周期', slot: 'period', width: 190 },
  { label: '订单数', prop: 'orderCount', width: 65, align: 'right' },
  { label: '订单金额', slot: 'total', width: 100, align: 'right' },
  { label: '平台佣金', slot: 'commission', width: 90, align: 'right' },
  { label: '退款扣减', slot: 'deduct', width: 90, align: 'right' },
  { label: '应结金额', slot: 'payable', width: 100, align: 'right' },
  { label: '状态', slot: 'status', width: 90 },
  { label: '生成时间', slot: 'created', width: 140 }
]
const settlementCompactColumns: TableColumn[] = [
  { label: '结算单号', prop: 'settlementNo', minWidth: 125 },
  { label: '结算周期', slot: 'period', width: 205 },
  { label: '订单金额', slot: 'total', width: 100, align: 'right' },
  { label: '应结金额', slot: 'payable', width: 100, align: 'right' },
  { label: '状态', slot: 'status', width: 90 },
  { label: '生成时间', slot: 'created', width: 145 }
]
const settlementColumns = computed<TableColumn[]>(() =>
  compact.value ? settlementCompactColumns : settlementDesktopColumns
)
const withdrawalDesktopColumns: TableColumn[] = [
  { label: '提现单号', prop: 'id', minWidth: 130 },
  { label: '提现金额', slot: 'amount', width: 100, align: 'right' },
  { label: '收款账户', slot: 'account', minWidth: 200 },
  { label: '状态', slot: 'status', width: 85 },
  { label: '申请时间', slot: 'created', width: 140 },
  { label: '处理时间', slot: 'handled', width: 140 },
  { label: '备注', slot: 'reason', minWidth: 160 }
]
const withdrawalCompactColumns: TableColumn[] = [
  { label: '提现单号', prop: 'id', minWidth: 125 },
  { label: '提现金额', slot: 'amount', width: 100, align: 'right' },
  { label: '收款账户', slot: 'account', minWidth: 210 },
  { label: '状态', slot: 'status', width: 90 },
  { label: '申请时间', slot: 'created', width: 145 },
  { label: '备注', slot: 'reason', minWidth: 170 }
]
const withdrawalColumns = computed<TableColumn[]>(() =>
  compact.value ? withdrawalCompactColumns : withdrawalDesktopColumns
)
const available = computed(() => Number(overview.value?.balance.available || 0))

function maskAccountNo(value?: string): string {
  if (!value) return '—'
  if (value.length <= 8) return value
  return `${value.slice(0, 4)} **** **** ${value.slice(-4)}`
}

async function loadOverview(): Promise<void> {
  overviewLoading.value = true
  overviewError.value = ''
  overviewRequestId.value = ''
  try {
    overview.value = await merchantApi.financeOverview(merchantId.value)
  } catch (err) {
    const state = toErrorState(err)
    overviewError.value = state.message
    overviewRequestId.value = state.requestId
  } finally {
    overviewLoading.value = false
  }
}

async function loadSettlementCounts(): Promise<void> {
  try {
    settlementCounts.value = await merchantApi.settlementStats(merchantId.value)
  } catch {
    settlementCounts.value = {}
  }
}

async function loadSettlements(): Promise<void> {
  settlementLoading.value = true
  settlementError.value = ''
  settlementRequestId.value = ''
  try {
    const result = await merchantApi.settlements(merchantId.value, {
      page: settlementPage.value,
      page_size: settlementPageSize.value,
      status: settlementStatus.value
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
    withdrawalCounts.value = await merchantApi.withdrawalStats(merchantId.value)
  } catch {
    withdrawalCounts.value = {}
  }
}

async function loadWithdrawals(): Promise<void> {
  withdrawalLoading.value = true
  withdrawalError.value = ''
  withdrawalRequestId.value = ''
  try {
    const result = await merchantApi.withdrawals(merchantId.value, {
      page: withdrawalPage.value,
      page_size: withdrawalPageSize.value,
      status: withdrawalStatus.value
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

async function loadAccount(): Promise<void> {
  accountLoading.value = true
  accountError.value = ''
  try {
    account.value = await merchantApi.settlementAccount(merchantId.value)
    accountForm.accountName = account.value.accountName
    accountForm.bankName = account.value.bankName
    accountForm.accountNo = account.value.accountNo
    accountForm.branch = account.value.branch
  } catch (err) {
    accountError.value = toErrorState(err).message
  } finally {
    accountLoading.value = false
  }
}

function switchTab(value: string | number): void {
  const tab = String(value)
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
  if (tab === 'bills' && !settlements.value.length) loadSettlements()
  if (tab === 'records' && !withdrawals.value.length) loadWithdrawals()
  if (tab === 'account' && !account.value) loadAccount()
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

async function openBills(settlement: Settlement): Promise<void> {
  billSettlement.value = settlement
  billVisible.value = true
  billLoading.value = true
  billError.value = ''
  bills.value = []
  try {
    bills.value = await merchantApi.settlementBills(merchantId.value, settlement.id)
  } catch (err) {
    billError.value = toErrorState(err).message
  } finally {
    billLoading.value = false
  }
}

function fillAll(): void {
  withdrawForm.amount = available.value.toFixed(2)
  withdrawError.value = ''
}

async function submitWithdrawal(): Promise<void> {
  withdrawError.value = ''
  const amount = Number(withdrawForm.amount)
  if (!Number.isFinite(amount) || amount <= 0) {
    withdrawError.value = '提现金额必须大于 0'
    return
  }
  if (amount > available.value) {
    withdrawError.value = '提现金额不能超过可提现余额'
    return
  }
  withdrawing.value = true
  try {
    await merchantApi.applyWithdrawal(merchantId.value, amount.toFixed(2))
    ElMessage.success('提现申请已提交，等待平台财务审核')
    withdrawForm.amount = ''
    await Promise.all([loadOverview(), loadWithdrawals()])
  } catch (err) {
    withdrawError.value = toErrorState(err, '提现申请失败').message
  } finally {
    withdrawing.value = false
  }
}

async function saveAccount(): Promise<void> {
  const valid = await accountFormRef.value?.validate().catch(() => false)
  if (!valid) return
  accountSaving.value = true
  try {
    account.value = await merchantApi.saveSettlementAccount(merchantId.value, {
      merchantId: merchantId.value,
      accountName: accountForm.accountName,
      bankName: accountForm.bankName,
      accountNo: accountForm.accountNo,
      branch: accountForm.branch,
      verified: account.value?.verified || false
    })
    ElMessage.success('结算账户已保存')
  } catch (err) {
    ElMessage.error(toErrorState(err, '保存失败').message)
  } finally {
    accountSaving.value = false
  }
}

const settlementExportRows = computed(() =>
  settlements.value.map((item) => ({
    settlementNo: item.settlementNo,
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
    id: item.id,
    amount: item.amount,
    account: `${item.accountName} ${maskAccountNo(item.accountNo)}`,
    status: item.status,
    createdAt: formatDateTime(item.createdAt),
    reason: item.reason || ''
  }))
)

onMounted(() => {
  void loadOverview()
  void loadSettlements()
  void loadWithdrawals()
  void loadAccount()
})
</script>

<template>
  <div>
    <ConsolePageHeader
      title="结算中心"
      description="查看结算账单、申请提现并维护结算账户；金额均为仿真数据。"
    >
      <template #actions>
        <el-button @click="activeTab = 'withdraw'">
          <el-icon><Wallet /></el-icon>申请提现
        </el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleErrorState
      v-if="overviewError"
      :message="overviewError"
      :request-id="overviewRequestId"
      @retry="loadOverview"
    />
    <template v-else>
      <div v-loading="overviewLoading" class="console-kpi-grid">
        <ConsoleKpiCard
          label="可提现余额"
          :value="`¥${formatMoney(overview?.balance.available)}`"
          hint="提现申请将冻结对应金额"
          tone="green"
        />
        <ConsoleKpiCard
          label="待结算金额"
          :value="`¥${formatMoney(overview?.balance.pendingSettlement)}`"
          hint="平台结算周期结束后可提现"
        />
        <ConsoleKpiCard
          label="冻结金额"
          :value="`¥${formatMoney(overview?.balance.frozen)}`"
          hint="提现审核中金额"
          tone="gold"
        />
        <ConsoleKpiCard
          label="累计提现"
          :value="`¥${formatMoney(overview?.balance.withdrawn)}`"
          hint="历史已打款金额"
        />
        <ConsoleKpiCard
          label="待确认结算"
          :value="String(overview?.settlementPending ?? '—')"
          hint="财务待确认账单数"
          :to="'/console/merchant/finance?tab=bills'"
        />
        <ConsoleKpiCard
          label="待审核提现"
          :value="String(overview?.withdrawalPending ?? '—')"
          hint="平台财务审核中"
          :to="'/console/merchant/finance?tab=records'"
        />
      </div>

      <div class="console-card" style="margin-top: 14px">
        <el-tabs :model-value="activeTab" @tab-change="switchTab">
          <el-tab-pane label="结算概览" name="overview" />
          <el-tab-pane label="账单明细" name="bills" />
          <el-tab-pane label="提现申请" name="withdraw" />
          <el-tab-pane label="提现记录" name="records" />
          <el-tab-pane label="结算账户" name="account" />
        </el-tabs>

        <div v-if="activeTab === 'overview'">
          <div class="console-card-title">
            <span>最近结算单</span>
            <button type="button" class="console-link" @click="switchTab('bills')">查看全部</button>
          </div>
          <el-table
            v-loading="overviewLoading"
            :data="overview?.recentSettlements || []"
            @row-click="openBills"
          >
            <el-table-column prop="settlementNo" label="结算单号" min-width="160" />
            <el-table-column label="结算周期" min-width="200">
              <template #default="{ row }">
                {{ formatPeriod(row.periodStart, row.periodEnd) }}
              </template>
            </el-table-column>
            <el-table-column label="应结金额" width="120" align="right">
              <template #default="{ row }">
                <span class="console-amount">¥{{ formatMoney(row.payable) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <ConsoleStatusTag kind="settlement" :value="row.status" />
              </template>
            </el-table-column>
            <el-table-column label="生成时间" width="150">
              <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
            </el-table-column>
          </el-table>
        </div>

        <div v-else-if="activeTab === 'bills'">
          <ConsoleStatusTabs
            :tabs="settlementTabs"
            :model-value="settlementStatus"
            @update:model-value="changeSettlementStatus"
          />
          <div style="display: flex; justify-content: flex-end; margin-bottom: 10px">
            <ConsoleExportButton
              filename="结算账单.csv"
              :rows="settlementExportRows"
              :headers="[
                { key: 'settlementNo', label: '结算单号' },
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
            empty-text="暂无结算账单"
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
            <template #period="{ row }">{{
              formatPeriod(row.periodStart, row.periodEnd)
            }}</template>
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
            <template #created="{ row }">{{ formatDateTime(row.createdAt) }}</template>
          </ConsoleDataTable>
        </div>

        <div v-else-if="activeTab === 'withdraw'">
          <div class="console-withdraw-layout">
            <section class="console-form-card" style="flex: 1">
              <h3>申请提现</h3>
              <el-form label-position="top" @submit.prevent="submitWithdrawal">
                <el-form-item label="提现金额" required>
                  <el-input
                    v-model="withdrawForm.amount"
                    size="large"
                    inputmode="decimal"
                    placeholder="请输入提现金额"
                  >
                    <template #prefix>¥</template>
                  </el-input>
                  <div class="console-muted" style="font-size: 11px; margin-top: 6px">
                    可提现余额 ¥{{ formatMoney(overview?.balance.available) }}
                    <button
                      type="button"
                      class="console-link"
                      style="margin-left: 8px"
                      @click="fillAll"
                    >
                      全部提现
                    </button>
                  </div>
                </el-form-item>
                <el-form-item label="收款账户">
                  <div class="console-card-note">
                    {{ account?.accountName || '—' }} · {{ account?.bankName || '—' }}
                    <br />
                    <span class="console-mono">{{ maskAccountNo(account?.accountNo) }}</span>
                  </div>
                </el-form-item>
                <p v-if="withdrawError" class="console-login-error">{{ withdrawError }}</p>
                <el-button
                  type="primary"
                  :loading="withdrawing"
                  :disabled="!account"
                  @click="submitWithdrawal"
                >
                  提交提现申请
                </el-button>
                <p
                  class="console-muted"
                  style="font-size: 11px; line-height: 1.8; margin-top: 10px"
                >
                  提现申请提交后金额进入冻结，平台财务审核通过后打款；驳回则退回可提现余额。
                </p>
              </el-form>
            </section>
            <section class="console-card" style="flex: 1">
              <div class="console-card-title">结算账户</div>
              <div v-if="account" class="console-detail-grid">
                <div class="console-detail-field">
                  <label>开户名称</label><span>{{ account.accountName }}</span>
                </div>
                <div class="console-detail-field">
                  <label>开户银行</label><span>{{ account.bankName }}</span>
                </div>
                <div class="console-detail-field">
                  <label>银行账号</label
                  ><span class="console-mono">{{ maskAccountNo(account.accountNo) }}</span>
                </div>
                <div class="console-detail-field">
                  <label>开户支行</label><span>{{ account.branch }}</span>
                </div>
                <div class="console-detail-field">
                  <label>认证状态</label>
                  <span>
                    <el-tag :type="account.verified ? 'success' : 'warning'" size="small">
                      {{ account.verified ? '已认证' : '待认证' }}
                    </el-tag>
                  </span>
                </div>
              </div>
              <el-button plain style="margin-top: 14px" @click="switchTab('account')">
                修改结算账户
              </el-button>
            </section>
          </div>
        </div>

        <div v-else-if="activeTab === 'records'">
          <ConsoleStatusTabs
            :tabs="withdrawalTabs"
            :model-value="withdrawalStatus"
            @update:model-value="changeWithdrawalStatus"
          />
          <div style="display: flex; justify-content: flex-end; margin-bottom: 10px">
            <ConsoleExportButton
              filename="提现记录.csv"
              :rows="withdrawalExportRows"
              :headers="[
                { key: 'id', label: '提现单号' },
                { key: 'amount', label: '金额' },
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
            empty-text="暂无提现记录"
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
            <template #amount="{ row }">
              <ConsoleMoney :value="row.amount" symbol />
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
            <template #reason="{ row }">
              <span :class="{ 'console-amount': row.status === 'rejected' }">
                {{ row.reason || '—' }}
              </span>
            </template>
          </ConsoleDataTable>
        </div>

        <div v-else>
          <ConsoleErrorState v-if="accountError" :message="accountError" @retry="loadAccount" />
          <div v-else v-loading="accountLoading" style="max-width: 560px">
            <el-form
              ref="accountFormRef"
              :model="accountForm"
              :rules="accountRules"
              label-position="top"
              @submit.prevent="saveAccount"
            >
              <el-form-item label="开户名称" prop="accountName">
                <el-input v-model="accountForm.accountName" maxlength="40" />
              </el-form-item>
              <el-form-item label="开户银行" prop="bankName">
                <el-input v-model="accountForm.bankName" maxlength="40" />
              </el-form-item>
              <el-form-item label="银行账号" prop="accountNo">
                <el-input v-model="accountForm.accountNo" maxlength="24" show-password />
              </el-form-item>
              <el-form-item label="开户支行" prop="branch">
                <el-input v-model="accountForm.branch" maxlength="60" />
              </el-form-item>
              <el-alert
                v-if="account && !account.verified"
                type="warning"
                :closable="false"
                show-icon
                title="账户待平台认证；认证完成前提现审核可能被驳回。"
                style="margin-bottom: 14px"
              />
              <el-button type="primary" :loading="accountSaving" @click="saveAccount">
                保存结算账户
              </el-button>
            </el-form>
          </div>
        </div>
      </div>
    </template>

    <ConsoleDetailDrawer
      v-model="billVisible"
      :title="`结算账单明细 · ${billSettlement?.settlementNo || ''}`"
      :loading="billLoading"
      :error="billError"
      @retry="billSettlement && openBills(billSettlement)"
    >
      <template v-if="billSettlement">
        <div class="console-summary-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr))">
          <div class="console-summary-item">
            <span>结算周期</span>
            <strong style="font-size: 14px">
              {{ formatPeriod(billSettlement.periodStart, billSettlement.periodEnd) }}
            </strong>
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
        <p class="console-muted" style="font-size: 11px; margin-top: 10px">
          明细为演示数据；真实接口应返回结算单关联订单明细。
        </p>
      </template>
      <template #footer>
        <el-button @click="billVisible = false">关闭</el-button>
      </template>
    </ConsoleDetailDrawer>
  </div>
</template>
