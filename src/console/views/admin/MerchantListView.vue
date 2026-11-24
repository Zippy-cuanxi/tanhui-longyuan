<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
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
import {
  adminApi,
  type AdminMerchantRow,
  type MerchantDetail,
  type MerchantPenalty
} from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { useConsoleUi } from '@/console/install'
import { formatDateTime, maskPhone } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

useConsoleUi()

const auth = useConsoleAuth()
const router = useRouter()
const canReview = computed(() => auth.can('merchant:review') || auth.can('*'))

const query = reactive({ keyword: '', status: 'all', page: 1, page_size: 20 })
const items = ref<AdminMerchantRow[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const requestId = ref('')
const counts = ref<Record<string, number>>({})
const selected = ref<AdminMerchantRow[]>([])

const drawerVisible = ref(false)
const detail = ref<MerchantDetail | null>(null)
const detailLoading = ref(false)
const detailError = ref('')
const detailRequestId = ref('')
const activeId = ref('')
const freezeVisible = ref(false)
const freezeTarget = ref<AdminMerchantRow | null>(null)
const acting = ref(false)

const tabs = computed(() => [
  { label: '全部商家', value: 'all', count: counts.value.all },
  { label: '正常', value: 'normal', count: counts.value.normal },
  { label: '审核中', value: 'pending', count: counts.value.pending },
  { label: '审核驳回', value: 'rejected', count: counts.value.rejected },
  { label: '已冻结', value: 'frozen', count: counts.value.frozen }
])

const columns: TableColumn[] = [
  { label: '商家 / 店铺', slot: 'merchant', minWidth: 200 },
  { label: '负责人', slot: 'owner', minWidth: 105 },
  { label: '所在地区', prop: 'region', minWidth: 120, showOverflowTooltip: true },
  { label: '经营状态', slot: 'status', width: 90 },
  { label: '店铺状态', slot: 'store', width: 80 },
  { label: '处罚记录', slot: 'penalties', width: 75, align: 'center' },
  { label: '入驻时间', slot: 'created', width: 140 },
  { label: '操作', slot: 'actions', width: 105, fixed: 'right' }
]

const quickReasons = ['经营异常', '多次发货超时', '商品质量投诉', '违规宣传']

const qualificationMeta = {
  approved: { label: '通过', color: '#2E9E5B', bg: '#E8F6ED' },
  pending: { label: '审核中', color: '#E8892B', bg: '#FFF3E4' },
  rejected: { label: '驳回', color: '#D64545', bg: '#FDECEC' }
} as const

const exportRows = computed(() =>
  items.value.map((item) => ({
    companyName: item.companyName,
    storeName: item.storeName,
    username: item.username,
    ownerName: item.ownerName,
    phone: maskPhone(item.phone),
    region: item.region,
    status: item.status,
    storeStatus: item.storeStatus,
    createdAt: formatDateTime(item.createdAt)
  }))
)

async function loadCounts(): Promise<void> {
  try {
    counts.value = await adminApi.merchantStats()
  } catch {
    counts.value = {}
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const result = await adminApi.merchants({
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

async function openDetail(row: Record<string, unknown> | AdminMerchantRow): Promise<void> {
  const merchant = row as AdminMerchantRow
  activeId.value = merchant.id
  drawerVisible.value = true
  await loadDetail()
}

async function loadDetail(): Promise<void> {
  if (!activeId.value) return
  detailLoading.value = true
  detailError.value = ''
  detailRequestId.value = ''
  try {
    detail.value = await adminApi.merchantDetail(activeId.value)
  } catch (err) {
    const state = toErrorState(err)
    detailError.value = state.message
    detailRequestId.value = state.requestId
  } finally {
    detailLoading.value = false
  }
}

function openFreeze(row: AdminMerchantRow | null): void {
  if (!row) return
  freezeTarget.value = row
  freezeVisible.value = true
}

async function confirmFreeze(reason: string): Promise<void> {
  if (!freezeTarget.value) return
  acting.value = true
  try {
    await adminApi.reviewMerchant(freezeTarget.value.id, 'freeze', reason)
    ElMessage.success('商家已冻结，高风险操作已写入操作日志')
    freezeVisible.value = false
    await Promise.all([load(), drawerVisible.value ? loadDetail() : Promise.resolve()])
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

async function unfreeze(row: AdminMerchantRow | MerchantDetail['merchant']): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '确认解除该商家的冻结状态？解冻后商家可重新进入后台经营。',
      '解除冻结',
      { type: 'warning', confirmButtonText: '解除冻结' }
    )
  } catch {
    return
  }
  acting.value = true
  try {
    await adminApi.reviewMerchant(row.id, 'unfreeze')
    ElMessage.success('已解除冻结，操作已记录日志')
    await Promise.all([load(), drawerVisible.value ? loadDetail() : Promise.resolve()])
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

function goReview(): void {
  drawerVisible.value = false
  router.push('/console/admin/merchants/review')
}

function onSelectionChange(rows: Record<string, any>[]): void {
  selected.value = rows as AdminMerchantRow[]
}

function penaltyTypeLabel(type: MerchantPenalty['type']): string {
  return type === 'freeze' ? '冻结' : type === 'reject' ? '审核驳回' : '警告'
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="商家列表"
      description="查看入驻主体、店铺状态与处罚记录；冻结 / 解冻属于高风险操作。"
    >
      <template #actions>
        <ConsoleExportButton
          filename="平台商家.csv"
          :rows="exportRows"
          :headers="[
            { key: 'companyName', label: '主体名称' },
            { key: 'storeName', label: '店铺名称' },
            { key: 'username', label: '账号' },
            { key: 'ownerName', label: '负责人' },
            { key: 'phone', label: '手机号' },
            { key: 'region', label: '地区' },
            { key: 'status', label: '商家状态' },
            { key: 'storeStatus', label: '店铺状态' },
            { key: 'createdAt', label: '入驻时间' }
          ]"
        />
        <el-button
          v-if="canReview"
          type="primary"
          @click="router.push('/console/admin/merchants/review')"
        >
          入驻审核
        </el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleFilterBar :loading="loading" @search="search" @reset="reset">
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          clearable
          placeholder="主体 / 店铺 / 账号 / 负责人"
          style="width: 260px"
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
      empty-text="暂无商家"
      empty-description="商家提交入驻申请后会出现在这里。"
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
        <span class="console-muted">已选择 {{ selected.length }} 个商家</span>
      </template>

      <template #merchant="{ row }">
        <div class="console-two-line">
          <strong>{{ row.companyName }}</strong>
          <span>{{ row.storeName }} · {{ row.username }}</span>
        </div>
      </template>

      <template #owner="{ row }">
        <div class="console-two-line">
          <strong>{{ row.ownerName }}</strong>
          <span><ConsoleMasked :value="row.phone" /></span>
        </div>
      </template>

      <template #status="{ row }">
        <ConsoleStatusTag kind="merchant" :value="row.status" />
      </template>

      <template #store="{ row }">
        <ConsoleStatusTag kind="store" :value="row.storeStatus" />
      </template>

      <template #penalties="{ row }">
        <span v-if="row.penaltyCount" class="console-amount">{{ row.penaltyCount }} 条</span>
        <span v-else class="console-muted">—</span>
      </template>

      <template #created="{ row }">{{ formatDateTime(row.createdAt) }}</template>

      <template #actions="{ row }">
        <div class="console-inline-actions" @click.stop>
          <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
          <template v-if="canReview">
            <el-button
              v-if="row.status === 'normal'"
              link
              type="danger"
              size="small"
              @click="openFreeze(row)"
            >
              冻结
            </el-button>
            <el-button
              v-if="row.status === 'frozen'"
              link
              type="success"
              size="small"
              @click="unfreeze(row)"
            >
              解冻
            </el-button>
          </template>
        </div>
      </template>
    </ConsoleDataTable>

    <ConsoleDetailDrawer
      v-model="drawerVisible"
      :title="`商家详情 · ${detail?.merchant.companyName || ''}`"
      :loading="detailLoading"
      :error="detailError"
      :error-request-id="detailRequestId"
      @retry="loadDetail"
    >
      <template v-if="detail">
        <div class="console-alert-row">
          <ConsoleStatusTag kind="merchant" :value="detail.merchant.status" />
          <span class="console-muted">账号 {{ detail.merchant.username }}</span>
          <span v-if="detail.merchant.rejectReason" class="console-amount">
            驳回：{{ detail.merchant.rejectReason }}
          </span>
          <span v-if="detail.merchant.frozenReason" class="console-amount">
            冻结：{{ detail.merchant.frozenReason }}
          </span>
        </div>

        <section class="console-detail-section">
          <h4>主体信息</h4>
          <div class="console-detail-grid">
            <div class="console-detail-field">
              <label>主体名称</label><span>{{ detail.merchant.companyName }}</span>
            </div>
            <div class="console-detail-field">
              <label>店铺名称</label><span>{{ detail.merchant.storeName }}</span>
            </div>
            <div class="console-detail-field">
              <label>负责人</label><span>{{ detail.merchant.ownerName }}</span>
            </div>
            <div class="console-detail-field">
              <label>手机号</label><span><ConsoleMasked :value="detail.merchant.phone" /></span>
            </div>
            <div class="console-detail-field">
              <label>邮箱</label
              ><span><ConsoleMasked :value="detail.merchant.email" kind="email" /></span>
            </div>
            <div class="console-detail-field">
              <label>所在地区</label><span>{{ detail.merchant.region }}</span>
            </div>
            <div class="console-detail-field">
              <label>营业执照号</label
              ><span class="console-mono">{{ detail.merchant.licenseNo }}</span>
            </div>
            <div class="console-detail-field">
              <label>入驻时间</label><span>{{ formatDateTime(detail.merchant.createdAt) }}</span>
            </div>
          </div>
          <div class="console-detail-images" style="margin-top: 12px">
            <el-image
              :src="detail.merchant.licenseImage"
              :preview-src-list="[detail.merchant.licenseImage]"
              fit="cover"
              style="width: 82px; height: 82px; border-radius: 8px"
              preview-teleported
            />
            <span class="console-image-placeholder">营业执照</span>
          </div>
        </section>

        <section v-if="detail.store" class="console-detail-section">
          <h4>店铺概况</h4>
          <div class="console-detail-grid">
            <div class="console-detail-field">
              <label>店铺状态</label>
              <span><ConsoleStatusTag kind="store" :value="detail.store.status" /></span>
            </div>
            <div class="console-detail-field">
              <label>店铺评分</label><span>{{ detail.store.rating }}</span>
            </div>
            <div class="console-detail-field full">
              <label>店铺简介</label><span>{{ detail.store.description }}</span>
            </div>
          </div>
          <div class="console-detail-images" style="margin-top: 10px">
            <el-image
              v-for="item in detail.store.qualifications"
              :key="item.id"
              :src="item.image"
              :preview-src-list="detail.store.qualifications.map((q) => q.image)"
              fit="cover"
              style="width: 82px; height: 82px; border-radius: 8px"
              preview-teleported
            />
          </div>
          <div class="console-inline-actions" style="margin-top: 10px">
            <span
              v-for="item in detail.store.qualifications"
              :key="item.id"
              class="console-status"
              :style="{
                color: qualificationMeta[item.status].color,
                background: qualificationMeta[item.status].bg
              }"
            >
              <i />{{ item.name }} · {{ qualificationMeta[item.status].label }}
            </span>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>处罚与风险记录</h4>
          <ul v-if="detail.penalties.length" class="console-timeline">
            <li v-for="item in detail.penalties" :key="item.id">
              <strong>{{ penaltyTypeLabel(item.type) }}</strong> · {{ item.reason }}
              <small>{{ formatDateTime(item.createdAt) }} · {{ item.operator }}</small>
            </li>
          </ul>
          <p v-else class="console-muted">暂无处罚记录。</p>
        </section>

        <section class="console-detail-section">
          <h4>备注</h4>
          <p class="console-muted" style="line-height: 1.8; margin: 0">
            高风险操作（冻结 / 解冻）会写入平台操作日志；冻结后商家无法进入后台，店铺同步暂停。
            本页数据为 mock，真实接口需补充处罚记录查询。
          </p>
        </section>
      </template>

      <template #footer>
        <el-button @click="drawerVisible = false">关闭</el-button>
        <template v-if="detail && canReview">
          <el-button
            v-if="detail.merchant.status === 'frozen'"
            type="success"
            :loading="acting"
            @click="unfreeze(detail.merchant)"
          >
            解除冻结
          </el-button>
          <el-button
            v-else-if="
              detail.merchant.status === 'pending' || detail.merchant.status === 'rejected'
            "
            type="primary"
            @click="goReview"
          >
            前往入驻审核
          </el-button>
          <el-button
            v-else
            type="danger"
            @click="
              openFreeze({
                ...detail.merchant,
                storeId: detail.store?.id || '',
                storeStatus: detail.store?.status || 'suspended',
                penaltyCount: detail.penalties.length
              })
            "
          >
            冻结商家
          </el-button>
        </template>
      </template>
    </ConsoleDetailDrawer>

    <ConsoleReasonDialog
      v-model:visible="freezeVisible"
      title="冻结商家"
      label="冻结原因"
      :quick-reasons="quickReasons"
      :min-length="4"
      danger
      :loading="acting"
      @confirm="confirmFreeze"
    />
  </div>
</template>
