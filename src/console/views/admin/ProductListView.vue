<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleFilterBar from '@/console/components/ConsoleFilterBar.vue'
import ConsoleStatusTabs from '@/console/components/ConsoleStatusTabs.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleExportButton from '@/console/components/ConsoleExportButton.vue'
import ConsoleDetailDrawer from '@/console/components/ConsoleDetailDrawer.vue'
import ConsoleReasonDialog from '@/console/components/ConsoleReasonDialog.vue'
import type { TableColumn } from '@/console/components/types'
import { adminApi, type Category, type Product } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { useConsoleUi } from '@/console/install'
import { formatDateTime, formatMoney } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

useConsoleUi()

const auth = useConsoleAuth()
const router = useRouter()
const canRemove = computed(() => auth.can('product:remove') || auth.can('*'))
const canApprove = computed(() => auth.can('product:approve') || auth.can('*'))

const query = reactive({
  keyword: '',
  status: 'all',
  storeId: '',
  categoryId: '',
  page: 1,
  page_size: 20
})
const items = ref<Product[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const requestId = ref('')
const counts = ref<Record<string, number>>({})
const categories = ref<Category[]>([])
const stores = ref<Array<{ id: string; name: string; merchantId: string }>>([])
const selected = ref<Product[]>([])

const drawerVisible = ref(false)
const detail = ref<Product | null>(null)
const detailLoading = ref(false)
const detailError = ref('')
const detailRequestId = ref('')
const activeId = ref('')
const removeVisible = ref(false)
const removeTarget = ref<Product | null>(null)
const acting = ref(false)

const tabs = computed(() => [
  { label: '全部', value: 'all', count: counts.value.all },
  { label: '草稿', value: 'draft', count: counts.value.draft },
  { label: '审核中', value: 'pending_review', count: counts.value.pending_review },
  { label: '已通过', value: 'approved', count: counts.value.approved },
  { label: '已驳回', value: 'rejected', count: counts.value.rejected },
  { label: '平台下架', value: 'removed', count: counts.value.removed }
])

const columns: TableColumn[] = [
  { label: '商品', slot: 'product', minWidth: 195 },
  { label: '店铺', prop: 'storeName', minWidth: 95, showOverflowTooltip: true },
  { label: '分类', prop: 'categoryName', width: 75 },
  { label: '价格 / 库存', slot: 'price', width: 90 },
  { label: '销量', prop: 'sales', width: 50, align: 'right' },
  { label: '状态', slot: 'status', width: 95 },
  { label: '绿色资料', slot: 'green', width: 80 },
  { label: '更新时间', slot: 'updated', width: 140 },
  { label: '操作', slot: 'actions', width: 125, fixed: 'right' }
]

const greenMeta: Record<string, { label: string; color: string; bg: string }> = {
  approved: { label: '已通过', color: '#2E9E5B', bg: '#E8F6ED' },
  pending_review: { label: '审核中', color: '#E8892B', bg: '#FFF3E4' },
  rejected: { label: '已驳回', color: '#D64545', bg: '#FDECEC' },
  draft: { label: '未提交', color: '#6B7A74', bg: '#EFF3F1' }
}

const quickReasons = ['商品信息违规', '假冒伪劣商品', '价格欺诈', '侵犯知识产权', '其他违规原因']

const exportRows = computed(() =>
  items.value.map((item) => ({
    title: item.title,
    storeName: item.storeName,
    category: item.categoryName,
    price: item.minPrice,
    stock: item.stock,
    sales: item.sales,
    status: item.status,
    green: greenMeta[item.greenProfile.status]?.label || item.greenProfile.status,
    updatedAt: formatDateTime(item.updatedAt)
  }))
)

async function loadCounts(): Promise<void> {
  try {
    counts.value = await adminApi.productStats()
  } catch {
    counts.value = {}
  }
}

async function loadOptions(): Promise<void> {
  try {
    const [categoryResult, storeResult] = await Promise.all([
      adminApi.categories(),
      adminApi.storeOptions()
    ])
    categories.value = categoryResult
    stores.value = storeResult
  } catch {
    categories.value = []
    stores.value = []
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const result = await adminApi.products({
      page: query.page,
      page_size: query.page_size,
      status: query.status,
      keyword: query.keyword,
      storeId: query.storeId,
      categoryId: query.categoryId
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
  query.categoryId = ''
  query.page = 1
  load()
}

function changeTab(value: string): void {
  query.status = value
  query.page = 1
  load()
}

function retryDetail(): void {
  if (activeId.value) void openDetail({ id: activeId.value })
}

async function openDetail(row: Record<string, unknown> | Product): Promise<void> {
  const product = row as Product
  activeId.value = product.id
  drawerVisible.value = true
  await loadDetail()
}

async function loadDetail(): Promise<void> {
  if (!activeId.value) return
  detailLoading.value = true
  detailError.value = ''
  detailRequestId.value = ''
  try {
    detail.value = await adminApi.product(activeId.value)
  } catch (err) {
    const state = toErrorState(err)
    detailError.value = state.message
    detailRequestId.value = state.requestId
  } finally {
    detailLoading.value = false
  }
}

function openRemove(row: Product): void {
  removeTarget.value = row
  removeVisible.value = true
}

async function confirmRemove(reason: string): Promise<void> {
  if (!removeTarget.value) return
  acting.value = true
  try {
    await adminApi.removeProduct(removeTarget.value.id, reason)
    ElMessage.success('商品已强制下架，操作已写入日志')
    removeVisible.value = false
    drawerVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

function onSelectionChange(rows: Record<string, any>[]): void {
  selected.value = rows as Product[]
}

onMounted(() => {
  void loadOptions()
  void load()
})
</script>

<template>
  <div>
    <ConsolePageHeader
      title="商品列表"
      description="全平台商品检索、绿色资料状态与强制下架；高风险下架操作需填写原因。"
    >
      <template #actions>
        <ConsoleExportButton
          filename="平台商品.csv"
          :rows="exportRows"
          :headers="[
            { key: 'title', label: '商品标题' },
            { key: 'storeName', label: '店铺' },
            { key: 'category', label: '分类' },
            { key: 'price', label: '起售价' },
            { key: 'stock', label: '库存' },
            { key: 'sales', label: '销量' },
            { key: 'status', label: '状态' },
            { key: 'green', label: '绿色资料' },
            { key: 'updatedAt', label: '更新时间' }
          ]"
        />
        <el-button
          v-if="canApprove"
          type="primary"
          @click="router.push('/console/admin/products/review')"
        >
          商品审核
        </el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleFilterBar :loading="loading" @search="search" @reset="reset">
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          clearable
          placeholder="商品标题 / 店铺"
          style="width: 210px"
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
      <el-form-item label="分类">
        <el-select v-model="query.categoryId" clearable placeholder="全部分类" style="width: 150px">
          <el-option
            v-for="item in categories"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
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
      empty-text="暂无商品"
      :empty-image="assetUrl('/console-assets/images/empty-goods.png')"
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
        <span class="console-muted">已选择 {{ selected.length }} 个商品</span>
      </template>

      <template #product="{ row }">
        <div class="console-product-cell">
          <img
            :src="row.cover || assetUrl('/console-assets/images/image-empty.png')"
            :alt="row.title"
          />
          <div>
            <strong>{{ row.title }}</strong>
            <span>{{ row.subtitle || '—' }}</span>
          </div>
        </div>
      </template>

      <template #price="{ row }">
        <div class="console-mono">¥{{ formatMoney(row.minPrice) }}</div>
        <small :class="{ 'console-amount': row.stock < 10 }">库存 {{ row.stock }}</small>
      </template>

      <template #status="{ row }">
        <ConsoleStatusTag kind="product" :value="row.status" />
      </template>

      <template #green="{ row }">
        <span
          class="console-status"
          :style="{
            color: greenMeta[row.greenProfile.status]?.color,
            background: greenMeta[row.greenProfile.status]?.bg
          }"
        >
          <i />{{ greenMeta[row.greenProfile.status]?.label || row.greenProfile.status }}
        </span>
      </template>

      <template #updated="{ row }">{{ formatDateTime(row.updatedAt) }}</template>

      <template #actions="{ row }">
        <div class="console-inline-actions" style="flex-wrap: nowrap" @click.stop>
          <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
          <el-button
            v-if="canRemove && row.status !== 'removed'"
            link
            type="danger"
            size="small"
            @click="openRemove(row)"
          >
            强制下架
          </el-button>
        </div>
      </template>
    </ConsoleDataTable>

    <ConsoleDetailDrawer
      v-model="drawerVisible"
      :title="`商品详情 · ${detail?.title || ''}`"
      :loading="detailLoading"
      :error="detailError"
      :error-request-id="detailRequestId"
      @retry="retryDetail"
    >
      <template v-if="detail">
        <div class="console-alert-row">
          <ConsoleStatusTag kind="product" :value="detail.status" />
          <span class="console-muted">{{ detail.storeName }}</span>
          <span
            v-if="detail.listed"
            class="console-status"
            style="color: #1f7a4d; background: #e7f4ec"
          >
            <i />已上架
          </span>
          <span v-if="detail.auditReason" class="console-amount">{{ detail.auditReason }}</span>
        </div>

        <section class="console-detail-section">
          <h4>商品信息</h4>
          <div class="console-detail-images">
            <el-image
              v-for="(image, index) in detail.images.length ? detail.images : [detail.cover]"
              :key="image + index"
              :src="image"
              :preview-src-list="detail.images.length ? detail.images : [detail.cover]"
              fit="cover"
              style="width: 96px; height: 96px; border-radius: 8px"
              preview-teleported
            />
          </div>
          <h3 style="margin: 12px 0 4px; font-size: 16px">{{ detail.title }}</h3>
          <p class="console-muted" style="margin: 0">{{ detail.subtitle || '—' }}</p>
          <div class="console-detail-grid" style="margin-top: 12px">
            <div class="console-detail-field">
              <label>店铺</label><span>{{ detail.storeName }}</span>
            </div>
            <div class="console-detail-field">
              <label>分类</label><span>{{ detail.categoryName }}</span>
            </div>
            <div class="console-detail-field">
              <label>价格</label><span>¥{{ formatMoney(detail.minPrice) }}</span>
            </div>
            <div class="console-detail-field">
              <label>库存 / 销量</label><span>{{ detail.stock }} / {{ detail.sales }}</span>
            </div>
            <div class="console-detail-field full">
              <label>商品描述</label><span>{{ detail.description }}</span>
            </div>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>规格与绿色资料</h4>
          <el-table :data="detail.skus" size="small">
            <el-table-column prop="spec" label="规格" min-width="150" />
            <el-table-column label="价格" width="100" align="right">
              <template #default="{ row }">¥{{ formatMoney(row.price) }}</template>
            </el-table-column>
            <el-table-column prop="stock" label="库存" width="80" align="right" />
          </el-table>
          <div class="console-detail-grid" style="margin-top: 12px">
            <div class="console-detail-field">
              <label>产地</label><span>{{ detail.greenProfile.origin }}</span>
            </div>
            <div class="console-detail-field">
              <label>种植方式</label><span>{{ detail.greenProfile.plantingMode }}</span>
            </div>
            <div class="console-detail-field">
              <label>绿色审核</label>
              <span>{{
                greenMeta[detail.greenProfile.status]?.label || detail.greenProfile.status
              }}</span>
            </div>
            <div class="console-detail-field">
              <label>助农项目</label><span>{{ detail.aidProjectName || '未关联' }}</span>
            </div>
            <div class="console-detail-field full">
              <label>绿色说明</label><span>{{ detail.greenProfile.description || '—' }}</span>
            </div>
          </div>
        </section>

        <section v-if="detail.change?.length" class="console-detail-section">
          <h4>变更对比（待审核）</h4>
          <el-table :data="detail.change" size="small">
            <el-table-column prop="label" label="字段" width="110" />
            <el-table-column prop="oldValue" label="原值" min-width="160" />
            <el-table-column prop="newValue" label="新值" min-width="160" />
          </el-table>
        </section>

        <section class="console-detail-section">
          <h4>审核记录</h4>
          <ul v-if="detail.auditRecords.length" class="console-timeline">
            <li v-for="record in detail.auditRecords" :key="record.id">
              {{ record.action }} · {{ record.operator }}
              <div v-if="record.reason" class="console-amount">{{ record.reason }}</div>
              <small>{{ formatDateTime(record.createdAt) }}</small>
            </li>
          </ul>
          <p v-else class="console-muted">暂无审核记录。</p>
        </section>
      </template>

      <template #footer>
        <el-button @click="drawerVisible = false">关闭</el-button>
        <el-button
          v-if="detail && canApprove && detail.status === 'pending_review'"
          type="primary"
          @click="router.push('/console/admin/products/review')"
        >
          前往审核
        </el-button>
        <el-button
          v-if="detail && canRemove && detail.status !== 'removed'"
          type="danger"
          :loading="acting"
          @click="openRemove(detail)"
        >
          强制下架
        </el-button>
      </template>
    </ConsoleDetailDrawer>

    <ConsoleReasonDialog
      v-model:visible="removeVisible"
      title="强制下架商品"
      label="下架原因"
      :quick-reasons="quickReasons"
      :min-length="4"
      danger
      :loading="acting"
      @confirm="confirmRemove"
    />
  </div>
</template>
