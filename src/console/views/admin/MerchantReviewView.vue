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
import ConsoleDetailDrawer from '@/console/components/ConsoleDetailDrawer.vue'
import ConsoleReasonDialog from '@/console/components/ConsoleReasonDialog.vue'
import type { TableColumn } from '@/console/components/types'
import { adminApi, type AdminMerchantRow, type MerchantDetail } from '@/console/api'
import { formatDateTime } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const query = reactive({ keyword: '', status: 'pending', page: 1, page_size: 20 })
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
const acting = ref(false)
const rejectVisible = ref(false)
const rejectTarget = ref<AdminMerchantRow | null>(null)

const tabs = computed(() => [
  { label: '待审核', value: 'pending', count: counts.value.pending },
  { label: '已通过', value: 'normal', count: counts.value.normal },
  { label: '已驳回', value: 'rejected', count: counts.value.rejected }
])

const columns: TableColumn[] = [
  { label: '入驻主体', slot: 'company', minWidth: 200 },
  { label: '申请人', slot: 'owner', minWidth: 105 },
  { label: '营业执照号', prop: 'licenseNo', minWidth: 130 },
  { label: '所在地区', prop: 'region', minWidth: 120, showOverflowTooltip: true },
  { label: '提交时间', slot: 'created', width: 138 },
  { label: '状态', slot: 'status', width: 88 },
  { label: '操作', slot: 'actions', width: 90, fixed: 'right' }
]

const quickReasons = [
  '营业执照图片不清晰',
  '资质证件已过期',
  '经营范围与申请类目不符',
  '主体信息与证件不一致'
]

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

function retryDetail(): void {
  if (activeId.value) void openDetail({ id: activeId.value } as AdminMerchantRow)
}

async function approve(row: AdminMerchantRow | MerchantDetail['merchant']): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '确认通过该商家的入驻审核？通过后商家可登录后台经营，店铺同步启用。',
      '审核通过',
      { type: 'success', confirmButtonText: '审核通过' }
    )
  } catch {
    return
  }
  acting.value = true
  try {
    await adminApi.reviewMerchant(row.id, 'approve')
    ElMessage.success('审核通过，已记录操作日志')
    drawerVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

function openReject(row: AdminMerchantRow | MerchantDetail['merchant']): void {
  rejectTarget.value = row as AdminMerchantRow
  rejectVisible.value = true
}

async function confirmReject(reason: string): Promise<void> {
  if (!rejectTarget.value) return
  acting.value = true
  try {
    await adminApi.reviewMerchant(rejectTarget.value.id, 'reject', reason)
    ElMessage.success('已驳回入驻申请，原因已记录')
    rejectVisible.value = false
    drawerVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

function onSelectionChange(rows: Record<string, any>[]): void {
  selected.value = rows as AdminMerchantRow[]
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="入驻审核"
      description="核验营业执照、经营资质与主体信息；驳回必须填写原因，结果同步商家登录状态页。"
    />

    <ConsoleFilterBar :loading="loading" @search="search" @reset="reset">
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          clearable
          placeholder="主体 / 账号 / 负责人"
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
      empty-text="暂无待审核商家"
      :empty-image="assetUrl('/console-assets/images/state-pending.png')"
      empty-description="商家提交入驻资料后会进入审核队列。"
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
        <span class="console-muted">已选择 {{ selected.length }} 个入驻申请</span>
      </template>

      <template #company="{ row }">
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

      <template #created="{ row }">{{ formatDateTime(row.createdAt) }}</template>

      <template #status="{ row }">
        <ConsoleStatusTag kind="merchant" :value="row.status" />
      </template>

      <template #actions="{ row }">
        <div class="console-inline-actions" @click.stop>
          <el-button link type="primary" size="small" @click="openDetail(row)">审核</el-button>
        </div>
      </template>
    </ConsoleDataTable>

    <ConsoleDetailDrawer
      v-model="drawerVisible"
      :title="`入驻审核 · ${detail?.merchant.companyName || ''}`"
      :loading="detailLoading"
      :error="detailError"
      :error-request-id="detailRequestId"
      @retry="retryDetail"
    >
      <template v-if="detail">
        <div class="console-alert-row">
          <ConsoleStatusTag kind="merchant" :value="detail.merchant.status" />
          <span class="console-muted">提交：{{ formatDateTime(detail.merchant.createdAt) }}</span>
          <span v-if="detail.merchant.reviewedAt" class="console-muted">
            审核：{{ formatDateTime(detail.merchant.reviewedAt) }}
          </span>
        </div>

        <section class="console-detail-section">
          <h4>主体资料</h4>
          <div class="console-detail-grid">
            <div class="console-detail-field">
              <label>主体名称</label><span>{{ detail.merchant.companyName }}</span>
            </div>
            <div class="console-detail-field">
              <label>店铺名称</label><span>{{ detail.merchant.storeName }}</span>
            </div>
            <div class="console-detail-field">
              <label>统一社会信用代码</label>
              <span class="console-mono">{{ detail.merchant.licenseNo }}</span>
            </div>
            <div class="console-detail-field">
              <label>申请人</label><span>{{ detail.merchant.ownerName }}</span>
            </div>
            <div class="console-detail-field">
              <label>手机号</label><span><ConsoleMasked :value="detail.merchant.phone" /></span>
            </div>
            <div class="console-detail-field">
              <label>邮箱</label>
              <span><ConsoleMasked :value="detail.merchant.email" kind="email" /></span>
            </div>
            <div class="console-detail-field full">
              <label>经营地区</label><span>{{ detail.merchant.region }}</span>
            </div>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>资质材料</h4>
          <div class="console-detail-images">
            <el-image
              :src="detail.merchant.licenseImage"
              :preview-src-list="[
                detail.merchant.licenseImage,
                ...(detail.store?.qualifications.map((item) => item.image) || [])
              ]"
              fit="cover"
              style="width: 96px; height: 96px; border-radius: 8px"
              preview-teleported
            />
            <el-image
              v-for="item in detail.store?.qualifications || []"
              :key="item.id"
              :src="item.image"
              :preview-src-list="detail.store?.qualifications.map((q) => q.image) || []"
              fit="cover"
              style="width: 96px; height: 96px; border-radius: 8px"
              preview-teleported
            />
          </div>
          <p class="console-muted" style="font-size: 11px; margin-top: 8px">
            营业执照：{{ detail.merchant.companyName }}；以上图片为本地演示素材。
          </p>
        </section>

        <section class="console-detail-section">
          <h4>审核检查项</h4>
          <ul class="console-check-list">
            <li>营业执照信息与主体名称一致</li>
            <li>经营范围覆盖拟售商品类目</li>
            <li>资质证件在有效期内且图片清晰</li>
            <li>联系人手机号、邮箱可正常联系</li>
            <li>同意《平台商家服务协议》与绿色商品规范</li>
          </ul>
        </section>

        <section v-if="detail.penalties.length" class="console-detail-section">
          <h4>历史记录</h4>
          <ul class="console-timeline">
            <li v-for="item in detail.penalties" :key="item.id">
              {{ item.reason }}
              <small>{{ formatDateTime(item.createdAt) }} · {{ item.operator }}</small>
            </li>
          </ul>
        </section>
      </template>

      <template #footer>
        <el-button @click="drawerVisible = false">关闭</el-button>
        <template
          v-if="
            detail &&
            (detail.merchant.status === 'pending' || detail.merchant.status === 'rejected')
          "
        >
          <el-button type="danger" plain :disabled="acting" @click="openReject(detail.merchant)">
            驳回
          </el-button>
          <el-button type="primary" :loading="acting" @click="approve(detail.merchant)">
            审核通过
          </el-button>
        </template>
      </template>
    </ConsoleDetailDrawer>

    <ConsoleReasonDialog
      v-model:visible="rejectVisible"
      title="驳回入驻申请"
      label="驳回原因"
      :quick-reasons="quickReasons"
      :min-length="4"
      danger
      :loading="acting"
      @confirm="confirmReject"
    />
  </div>
</template>
