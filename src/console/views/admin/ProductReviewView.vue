<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleFilterBar from '@/console/components/ConsoleFilterBar.vue'
import ConsoleStatusTabs from '@/console/components/ConsoleStatusTabs.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleDetailDrawer from '@/console/components/ConsoleDetailDrawer.vue'
import ConsoleReasonDialog from '@/console/components/ConsoleReasonDialog.vue'
import type { TableColumn } from '@/console/components/types'
import { adminApi, type Product } from '@/console/api'
import { REJECT_REASONS } from '@/console/constants/labels'
import { formatDateTime, formatMoney } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const keyword = ref('')
const type = ref('new')
const all = ref<Product[]>([])
const loading = ref(false)
const error = ref('')
const requestId = ref('')
const drawerVisible = ref(false)
const active = ref<Product | null>(null)
const acting = ref(false)
const rejectVisible = ref(false)

const isChange = (product: Product): boolean => Boolean(product.change?.length)

const rows = computed(() => {
  const word = keyword.value.trim().toLowerCase()
  return all.value.filter((item) => {
    if (type.value === 'new' && isChange(item)) return false
    if (type.value === 'change' && !isChange(item)) return false
    if (word) {
      return item.title.toLowerCase().includes(word) || item.storeName.toLowerCase().includes(word)
    }
    return true
  })
})

const tabs = computed(() => [
  { label: '新品审核', value: 'new', count: all.value.filter((item) => !isChange(item)).length },
  { label: '修改再审', value: 'change', count: all.value.filter(isChange).length },
  { label: '全部待审', value: 'all', count: all.value.length }
])

const columns: TableColumn[] = [
  { label: '商品', slot: 'product', minWidth: 235 },
  { label: '店铺', prop: 'storeName', minWidth: 140, showOverflowTooltip: true },
  { label: '分类', prop: 'categoryName', width: 85 },
  { label: '审核类型', slot: 'type', width: 85 },
  { label: '价格', slot: 'price', width: 90, align: 'right' },
  { label: '绿色资料', slot: 'green', width: 85 },
  { label: '提交时间', slot: 'submitted', width: 145 },
  { label: '操作', slot: 'actions', width: 95, fixed: 'right' }
]

const greenLabel: Record<string, string> = {
  approved: '已通过',
  pending_review: '审核中',
  rejected: '已驳回',
  draft: '未提交'
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const result = await adminApi.products({
      status: 'pending_review',
      page: 1,
      page_size: 100
    })
    all.value = result.items
  } catch (err) {
    const state = toErrorState(err)
    error.value = state.message
    requestId.value = state.requestId
  } finally {
    loading.value = false
  }
}

function openDetail(row: Record<string, unknown> | Product): void {
  active.value = row as Product
  drawerVisible.value = true
}

async function approve(): Promise<void> {
  if (!active.value) return
  try {
    await ElMessageBox.confirm(
      `确认审核通过「${active.value.title}」？通过后商家可手动上架，绿色资料同步通过。`,
      '审核通过',
      { type: 'success', confirmButtonText: '审核通过' }
    )
  } catch {
    return
  }
  acting.value = true
  try {
    await adminApi.auditProduct(active.value.id, 'approve')
    ElMessage.success('商品审核通过')
    drawerVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

function openReject(): void {
  rejectVisible.value = true
}

async function confirmReject(reason: string): Promise<void> {
  if (!active.value) return
  acting.value = true
  try {
    await adminApi.auditProduct(active.value.id, 'reject', reason)
    ElMessage.success('商品已驳回，原因已同步商家')
    rejectVisible.value = false
    drawerVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  } finally {
    acting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="商品审核"
      description="审核新商品与修改后的商品；改审商品展示字段前后对比。"
    >
      <template #actions>
        <el-button @click="load">刷新待审</el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleFilterBar :loading="loading" @search="load" @reset="keyword = ''">
      <el-form-item label="关键词">
        <el-input
          v-model="keyword"
          clearable
          placeholder="商品标题 / 店铺"
          style="width: 240px"
          @keyup.enter="load"
        />
      </el-form-item>
    </ConsoleFilterBar>

    <div class="console-audit-tip" style="margin: 0 0 14px">
      审核口径：仅修改价格 /
      库存不进入审核；标题、主图、描述、分类、运费模板、绿色资料变更会进入「修改再审」。 当前待审
      {{ all.length }} 个商品，其中改审 {{ all.filter(isChange).length }} 个。
    </div>

    <ConsoleStatusTabs :tabs="tabs" :model-value="type" @update:model-value="type = $event" />

    <ConsoleDataTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :error="error"
      :error-request-id="requestId"
      :total="rows.length"
      :page="1"
      :page-size="20"
      empty-text="审核队列已清空"
      :empty-image="assetUrl('/console-assets/images/state-pending.png')"
      empty-description="当前筛选下没有待审核商品。"
      @row-click="openDetail"
      @retry="load"
    >
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

      <template #type="{ row }">
        <span
          class="console-tag-soft"
          :style="row.change?.length ? { color: '#E8892B', background: '#FFF3E4' } : {}"
        >
          {{ row.change?.length ? '修改再审' : '新品审核' }}
        </span>
      </template>

      <template #price="{ row }">¥{{ formatMoney(row.minPrice) }}</template>

      <template #green="{ row }">{{
        greenLabel[row.greenProfile.status] || row.greenProfile.status
      }}</template>

      <template #submitted="{ row }">{{ formatDateTime(row.updatedAt) }}</template>

      <template #actions="{ row }">
        <div class="console-inline-actions" @click.stop>
          <el-button link type="primary" size="small" @click="openDetail(row)">审核</el-button>
        </div>
      </template>
    </ConsoleDataTable>

    <ConsoleDetailDrawer v-model="drawerVisible" :title="`商品审核 · ${active?.title || ''}`">
      <template v-if="active">
        <div class="console-alert-row">
          <ConsoleStatusTag kind="product" :value="active.status" />
          <span
            class="console-tag-soft"
            :style="active.change?.length ? { color: '#E8892B', background: '#FFF3E4' } : {}"
          >
            {{ active.change?.length ? '修改再审' : '新品审核' }}
          </span>
          <span class="console-muted">{{ active.storeName }} · {{ active.categoryName }}</span>
        </div>

        <section v-if="active.change?.length" class="console-detail-section">
          <h4>本次修改对比</h4>
          <el-table :data="active.change" size="small">
            <el-table-column prop="label" label="字段" width="110" />
            <el-table-column label="原值" min-width="170">
              <template #default="{ row }">
                <span class="console-muted">{{ row.oldValue || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="新值" min-width="170">
              <template #default="{ row }">
                <span style="color: #1f7a4d; font-weight: 600">{{ row.newValue || '—' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section class="console-detail-section">
          <h4>商品图片</h4>
          <div class="console-detail-images">
            <el-image
              v-for="(image, index) in active.images.length ? active.images : [active.cover]"
              :key="image + index"
              :src="image"
              :preview-src-list="active.images.length ? active.images : [active.cover]"
              fit="cover"
              style="width: 96px; height: 96px; border-radius: 8px"
              preview-teleported
            />
          </div>
        </section>

        <section class="console-detail-section">
          <h4>商品信息</h4>
          <div class="console-detail-grid">
            <div class="console-detail-field">
              <label>商品标题</label><span>{{ active.title }}</span>
            </div>
            <div class="console-detail-field">
              <label>卖点</label><span>{{ active.subtitle || '—' }}</span>
            </div>
            <div class="console-detail-field">
              <label>店铺</label><span>{{ active.storeName }}</span>
            </div>
            <div class="console-detail-field">
              <label>分类</label><span>{{ active.categoryName }}</span>
            </div>
            <div class="console-detail-field">
              <label>起售价</label><span>¥{{ formatMoney(active.minPrice) }}</span>
            </div>
            <div class="console-detail-field">
              <label>库存 / 销量</label><span>{{ active.stock }} / {{ active.sales }}</span>
            </div>
            <div class="console-detail-field full">
              <label>商品描述</label><span>{{ active.description }}</span>
            </div>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>规格与绿色资料</h4>
          <el-table :data="active.skus" size="small">
            <el-table-column prop="spec" label="规格" min-width="150" />
            <el-table-column label="价格" width="100" align="right">
              <template #default="{ row }">¥{{ formatMoney(row.price) }}</template>
            </el-table-column>
            <el-table-column prop="stock" label="库存" width="80" align="right" />
          </el-table>
          <div class="console-detail-grid" style="margin-top: 12px">
            <div class="console-detail-field">
              <label>产地</label><span>{{ active.greenProfile.origin }}</span>
            </div>
            <div class="console-detail-field">
              <label>种植方式</label><span>{{ active.greenProfile.plantingMode }}</span>
            </div>
            <div class="console-detail-field">
              <label>绿色审核</label
              ><span>{{
                greenLabel[active.greenProfile.status] || active.greenProfile.status
              }}</span>
            </div>
            <div class="console-detail-field">
              <label>助农项目</label><span>{{ active.aidProjectName || '未关联' }}</span>
            </div>
            <div class="console-detail-field full">
              <label>绿色说明</label><span>{{ active.greenProfile.description || '—' }}</span>
            </div>
          </div>
        </section>

        <section class="console-detail-section">
          <h4>提交记录</h4>
          <ul v-if="active.auditRecords.length" class="console-timeline">
            <li v-for="record in active.auditRecords" :key="record.id">
              {{ record.action }} · {{ record.operator }}
              <div v-if="record.reason" class="console-amount">{{ record.reason }}</div>
              <small>{{ formatDateTime(record.createdAt) }}</small>
            </li>
          </ul>
          <p v-else class="console-muted">暂无提交记录。</p>
        </section>
      </template>

      <template #footer>
        <el-button @click="drawerVisible = false">关闭</el-button>
        <el-button type="danger" plain :disabled="acting" @click="openReject">驳回</el-button>
        <el-button type="primary" :loading="acting" @click="approve">审核通过</el-button>
      </template>
    </ConsoleDetailDrawer>

    <ConsoleReasonDialog
      v-model:visible="rejectVisible"
      title="驳回商品审核"
      label="驳回原因"
      :quick-reasons="REJECT_REASONS"
      danger
      :loading="acting"
      @confirm="confirmReject"
    />
  </div>
</template>
