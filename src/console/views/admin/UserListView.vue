<script setup lang="ts">
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
import { adminApi, type Member, type MemberDetail } from '@/console/api'
import {
  downloadCsv,
  formatDateTime,
  formatMoney,
  maskEmail,
  maskPhone
} from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const query = reactive({ keyword: '', status: 'all', page: 1, page_size: 20 })
const items = ref<Member[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const requestId = ref('')
const counts = ref<Record<string, number>>({})
const selected = ref<Member[]>([])

const drawerVisible = ref(false)
const detail = ref<MemberDetail | null>(null)
const detailLoading = ref(false)
const detailError = ref('')
const detailRequestId = ref('')
const activeId = ref('')

const tabs = computed(() => [
  { label: '全部用户', value: 'all', count: counts.value.all },
  { label: '正常', value: 'active', count: counts.value.active },
  { label: '已封禁', value: 'banned', count: counts.value.banned }
])

const columns: TableColumn[] = [
  { label: '用户', slot: 'member', minWidth: 130 },
  { label: '手机号', slot: 'phone', width: 95 },
  { label: '邮箱', slot: 'email', minWidth: 105 },
  { label: '状态', slot: 'status', width: 75 },
  { label: '订单数', prop: 'orderCount', width: 55, align: 'right' },
  { label: '累计消费', slot: 'paid', width: 85, align: 'right' },
  { label: '积分', prop: 'points', width: 55, align: 'right' },
  { label: '注册时间', slot: 'created', width: 138 },
  { label: '最近登录', slot: 'login', width: 138 },
  { label: '操作', slot: 'actions', width: 60, fixed: 'right' }
]

const exportRows = computed(() =>
  items.value.map((item) => ({
    nickname: item.nickname,
    phone: maskPhone(item.phone),
    email: maskEmail(item.email),
    status: item.status,
    orderCount: item.orderCount,
    totalPaid: item.totalPaid,
    points: item.points,
    createdAt: formatDateTime(item.createdAt)
  }))
)

async function loadCounts(): Promise<void> {
  try {
    counts.value = await adminApi.memberStats()
  } catch {
    counts.value = {}
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const result = await adminApi.members({
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

async function openDetail(row: Record<string, unknown> | Member): Promise<void> {
  const member = row as Member
  activeId.value = member.id
  drawerVisible.value = true
  detailLoading.value = true
  detailError.value = ''
  detailRequestId.value = ''
  try {
    detail.value = await adminApi.memberDetail(activeId.value)
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
  selected.value = rows as Member[]
}

function exportSelected(): void {
  if (!selected.value.length) return
  downloadCsv(
    '平台用户-所选.csv',
    selected.value.map((item) => ({
      nickname: item.nickname,
      phone: maskPhone(item.phone),
      email: maskEmail(item.email),
      status: item.status,
      orderCount: item.orderCount,
      totalPaid: item.totalPaid
    })),
    [
      { key: 'nickname', label: '昵称' },
      { key: 'phone', label: '手机号' },
      { key: 'email', label: '邮箱' },
      { key: 'status', label: '状态' },
      { key: 'orderCount', label: '订单数' },
      { key: 'totalPaid', label: '累计消费' }
    ]
  )
  ElMessage.success(`已导出 ${selected.value.length} 位用户`)
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="用户管理"
      description="消费者账号只读列表与详情；敏感信息脱敏展示，一期不提供封禁操作。"
    >
      <template #actions>
        <ConsoleExportButton
          filename="平台用户.csv"
          :rows="exportRows"
          :headers="[
            { key: 'nickname', label: '昵称' },
            { key: 'phone', label: '手机号' },
            { key: 'email', label: '邮箱' },
            { key: 'status', label: '状态' },
            { key: 'orderCount', label: '订单数' },
            { key: 'totalPaid', label: '累计消费' },
            { key: 'points', label: '积分' },
            { key: 'createdAt', label: '注册时间' }
          ]"
        />
      </template>
    </ConsolePageHeader>

    <ConsoleFilterBar :loading="loading" @search="search" @reset="reset">
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          clearable
          placeholder="昵称 / 手机号 / 邮箱"
          style="width: 250px"
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
      empty-text="暂无用户"
      empty-description="消费者注册后会出现在这里。"
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
        <el-button size="small" plain @click="exportSelected">导出所选用户</el-button>
      </template>

      <template #member="{ row }">
        <div class="console-two-line">
          <strong>{{ row.nickname }}</strong>
          <span>{{ row.id }} · {{ row.roles.join(' / ') }}</span>
        </div>
      </template>

      <template #phone="{ row }">
        <ConsoleMasked :value="row.phone" />
      </template>

      <template #email="{ row }">
        <ConsoleMasked :value="row.email" kind="email" />
      </template>

      <template #status="{ row }">
        <ConsoleStatusTag kind="member" :value="row.status" />
      </template>

      <template #paid="{ row }">
        <span class="console-mono">¥{{ formatMoney(row.totalPaid) }}</span>
      </template>

      <template #created="{ row }">{{ formatDateTime(row.createdAt) }}</template>

      <template #login="{ row }">{{ formatDateTime(row.lastLoginAt) }}</template>

      <template #actions="{ row }">
        <el-button link type="primary" size="small" @click.stop="openDetail(row)">详情</el-button>
      </template>
    </ConsoleDataTable>

    <ConsoleDetailDrawer
      v-model="drawerVisible"
      :title="`用户详情 · ${detail?.member.nickname || ''}`"
      :loading="detailLoading"
      :error="detailError"
      :error-request-id="detailRequestId"
      @retry="retryDetail"
    >
      <template v-if="detail">
        <div class="console-alert-row">
          <ConsoleStatusTag kind="member" :value="detail.member.status" />
          <span class="console-muted">注册于 {{ formatDateTime(detail.member.createdAt) }}</span>
          <span v-if="detail.member.banReason" class="console-amount">
            封禁原因：{{ detail.member.banReason }}
          </span>
        </div>

        <section class="console-detail-section">
          <h4>账号信息</h4>
          <div class="console-detail-grid">
            <div class="console-detail-field">
              <label>用户 ID</label><span class="console-mono">{{ detail.member.id }}</span>
            </div>
            <div class="console-detail-field">
              <label>昵称</label><span>{{ detail.member.nickname }}</span>
            </div>
            <div class="console-detail-field">
              <label>手机号</label><span><ConsoleMasked :value="detail.member.phone" /></span>
            </div>
            <div class="console-detail-field">
              <label>邮箱</label>
              <span><ConsoleMasked :value="detail.member.email" kind="email" /></span>
            </div>
            <div class="console-detail-field">
              <label>角色</label><span>{{ detail.member.roles.join(' / ') }}</span>
            </div>
            <div class="console-detail-field">
              <label>最近登录</label><span>{{ formatDateTime(detail.member.lastLoginAt) }}</span>
            </div>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>消费与积分</h4>
          <div class="console-summary-grid">
            <div class="console-summary-item">
              <span>累计订单</span><strong>{{ detail.member.orderCount }}</strong>
            </div>
            <div class="console-summary-item">
              <span>累计消费</span>
              <strong style="font-size: 18px">¥{{ formatMoney(detail.member.totalPaid) }}</strong>
            </div>
            <div class="console-summary-item">
              <span>绿豆积分余额</span><strong>{{ detail.member.points }}</strong>
            </div>
            <div class="console-summary-item">
              <span>售后记录</span><strong>{{ detail.aftersales.length }}</strong>
            </div>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>最近订单</h4>
          <el-table :data="detail.orders" size="small" empty-text="暂无订单">
            <el-table-column prop="orderNo" label="订单号" min-width="150" />
            <el-table-column prop="storeName" label="店铺" min-width="150" />
            <el-table-column label="金额" width="100" align="right">
              <template #default="{ row }">¥{{ formatMoney(row.payAmount) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <ConsoleStatusTag kind="order" :value="row.status" />
              </template>
            </el-table-column>
            <el-table-column label="下单时间" width="140">
              <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
            </el-table-column>
          </el-table>
        </section>

        <section class="console-detail-section">
          <h4>售后记录</h4>
          <el-table :data="detail.aftersales" size="small" empty-text="暂无售后">
            <el-table-column prop="refundNo" label="退款单号" min-width="150" />
            <el-table-column prop="reason" label="原因" min-width="130" />
            <el-table-column label="金额" width="100" align="right">
              <template #default="{ row }">¥{{ formatMoney(row.amount) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <ConsoleStatusTag kind="aftersale" :value="row.status" />
              </template>
            </el-table-column>
          </el-table>
        </section>
      </template>

      <template #footer>
        <el-button @click="drawerVisible = false">关闭</el-button>
      </template>
    </ConsoleDetailDrawer>
  </div>
</template>
