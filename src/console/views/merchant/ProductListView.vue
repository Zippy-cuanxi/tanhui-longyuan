<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleFilterBar from '@/console/components/ConsoleFilterBar.vue'
import ConsoleStatusTabs from '@/console/components/ConsoleStatusTabs.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleExportButton from '@/console/components/ConsoleExportButton.vue'
import type { TableColumn } from '@/console/components/types'
import { merchantApi, type Category, type Product } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { formatDateTime, formatMoney } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const router = useRouter()
const merchantId = computed(() => auth.merchantAccount?.id || '')

const query = reactive({
  keyword: '',
  categoryId: '',
  status: 'all',
  page: 1,
  page_size: 20
})
const items = ref<Product[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const requestId = ref('')
const categories = ref<Category[]>([])
const counts = ref<Record<string, number>>({})
const selected = ref<Product[]>([])

const tabs = computed(() => [
  { label: '全部', value: 'all', count: counts.value.all },
  { label: '草稿', value: 'draft', count: counts.value.draft },
  { label: '审核中', value: 'pending_review', count: counts.value.pending_review },
  { label: '已通过', value: 'approved', count: counts.value.approved },
  { label: '已驳回', value: 'rejected', count: counts.value.rejected },
  { label: '平台下架', value: 'removed', count: counts.value.removed }
])

const columns: TableColumn[] = [
  { label: '商品', slot: 'product', minWidth: 200 },
  { label: '分类', slot: 'category', width: 75 },
  { label: '价格 / 库存', slot: 'price', width: 90 },
  { label: '销量', prop: 'sales', width: 50, align: 'right' },
  { label: '状态', slot: 'status', width: 132 },
  { label: '审核说明', slot: 'audit', minWidth: 80 },
  { label: '更新时间', slot: 'updated', width: 138 },
  { label: '操作', slot: 'actions', width: 120, fixed: 'right' }
]

const exportRows = computed(() =>
  items.value.map((item) => ({
    title: item.title,
    category: item.categoryName,
    price: item.minPrice,
    stock: item.stock,
    sales: item.sales,
    status: item.status,
    listed: item.listed ? '已上架' : '未上架',
    updatedAt: formatDateTime(item.updatedAt)
  }))
)

async function loadCounts(): Promise<void> {
  try {
    counts.value = await merchantApi.productStats(merchantId.value)
  } catch {
    counts.value = {}
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const result = await merchantApi.products(merchantId.value, {
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword,
      categoryId: query.categoryId,
      status: query.status
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
  query.categoryId = ''
  query.status = 'all'
  query.page = 1
  load()
}

async function loadCategories(): Promise<void> {
  try {
    categories.value = await merchantApi.categories()
  } catch {
    categories.value = []
  }
}

function edit(row: Product): void {
  router.push(`/console/merchant/products/${row.id}/edit`)
}

async function submitAudit(row: Product): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认将「${row.title}」提交平台审核？审核期间商品不可上架。`,
      '提交审核',
      { type: 'warning', confirmButtonText: '提交审核' }
    )
  } catch {
    return
  }
  try {
    await merchantApi.submitProduct(merchantId.value, row.id)
    ElMessage.success('已提交审核')
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '提交失败').message)
  }
}

async function toggleListing(row: Product): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认${row.listed ? '下架' : '上架'}「${row.title}」？`,
      row.listed ? '商品下架' : '商品上架',
      { type: row.listed ? 'warning' : 'info' }
    )
  } catch {
    return
  }
  try {
    await merchantApi.toggleListing(merchantId.value, row.id, !row.listed)
    ElMessage.success(row.listed ? '商品已下架' : '商品已上架')
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  }
}

async function bulkSubmit(): Promise<void> {
  const targets = selected.value.filter((item) => ['draft', 'rejected'].includes(item.status))
  if (!targets.length) {
    ElMessage.warning('所选商品中没有可提交审核的草稿或已驳回商品')
    return
  }
  try {
    await ElMessageBox.confirm(
      `已选择 ${targets.length} 个可提交商品，确认批量提交审核？`,
      '批量提交审核',
      { type: 'warning' }
    )
  } catch {
    return
  }
  let success = 0
  for (const item of targets) {
    try {
      await merchantApi.submitProduct(merchantId.value, item.id)
      success += 1
    } catch {
      // 单个失败不阻断其它商品
    }
  }
  ElMessage.success(`已提交 ${success} 个商品审核`)
  await load()
}

function onSelectionChange(rows: Record<string, unknown>[]): void {
  selected.value = rows as unknown as Product[]
}

onMounted(() => {
  void loadCategories()
  void load()
})
</script>

<template>
  <div>
    <ConsolePageHeader
      title="商品列表"
      description="商品发布、审核状态与上下架管理；价格与库存调整无需重新审核。"
    >
      <template #actions>
        <ConsoleExportButton
          filename="商家商品.csv"
          :rows="exportRows"
          :headers="[
            { key: 'title', label: '商品标题' },
            { key: 'category', label: '分类' },
            { key: 'price', label: '起售价' },
            { key: 'stock', label: '库存' },
            { key: 'sales', label: '销量' },
            { key: 'status', label: '状态' },
            { key: 'listed', label: '上架状态' },
            { key: 'updatedAt', label: '更新时间' }
          ]"
        />
        <el-button type="primary" @click="router.push('/console/merchant/products/new')">
          <el-icon><Plus /></el-icon>发布商品
        </el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleFilterBar :loading="loading" @search="search" @reset="reset">
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          clearable
          placeholder="商品标题 / 卖点"
          style="width: 220px"
          @keyup.enter="search"
        />
      </el-form-item>
      <el-form-item label="商品分类">
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

    <ConsoleStatusTabs
      :tabs="tabs"
      :model-value="query.status"
      @update:model-value="
        (value: string) => {
          query.status = value
          query.page = 1
          load()
        }
      "
    />

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
      empty-text="还没有商品"
      :empty-image="assetUrl('/console-assets/images/empty-goods.png')"
      empty-description="提交第一个甘肃特色商品，审核通过后即可上架销售。"
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
      @selection-change="onSelectionChange"
      @retry="load"
    >
      <template #bulk>
        <el-button size="small" type="primary" plain @click="bulkSubmit"> 批量提交审核 </el-button>
        <span class="console-muted">仅草稿 / 已驳回商品可提交</span>
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

      <template #category="{ row }">{{ row.categoryName }}</template>

      <template #price="{ row }">
        <div class="console-mono">¥{{ formatMoney(row.minPrice) }}</div>
        <small :class="{ 'console-amount': row.stock < 10 }">库存 {{ row.stock }}</small>
      </template>

      <template #status="{ row }">
        <div class="console-inline-actions" style="flex-wrap: nowrap">
          <ConsoleStatusTag kind="product" :value="row.status" />
          <span
            v-if="row.status === 'approved'"
            class="console-status"
            :style="
              row.listed
                ? { color: '#1F7A4D', background: '#E7F4EC' }
                : { color: '#6B7A74', background: '#EFF3F1' }
            "
          >
            <i />{{ row.listed ? '已上架' : '未上架' }}
          </span>
        </div>
      </template>

      <template #audit="{ row }">
        <span v-if="row.auditReason" class="console-ellipsis" :title="row.auditReason">
          {{ row.auditReason }}
        </span>
        <span v-else class="console-muted">—</span>
      </template>

      <template #updated="{ row }"
        ><span class="console-nowrap">{{ formatDateTime(row.updatedAt) }}</span></template
      >

      <template #actions="{ row }">
        <div class="console-inline-actions" style="flex-wrap: nowrap" @click.stop>
          <el-button link type="primary" size="small" @click="edit(row)">编辑</el-button>
          <el-button
            v-if="['draft', 'rejected'].includes(row.status)"
            link
            type="primary"
            size="small"
            @click="submitAudit(row)"
          >
            提交审核
          </el-button>
          <el-button
            v-if="row.status === 'approved'"
            link
            :type="row.listed ? 'warning' : 'success'"
            size="small"
            @click="toggleListing(row)"
          >
            {{ row.listed ? '下架' : '上架' }}
          </el-button>
        </div>
      </template>
    </ConsoleDataTable>
  </div>
</template>
