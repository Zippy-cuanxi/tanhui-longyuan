<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleFilterBar from '@/console/components/ConsoleFilterBar.vue'
import ConsoleStatusTabs from '@/console/components/ConsoleStatusTabs.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleDetailDrawer from '@/console/components/ConsoleDetailDrawer.vue'
import type { TableColumn } from '@/console/components/types'
import { adminApi, type Announcement } from '@/console/api'
import { formatDateTime } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const query = reactive({ keyword: '', status: 'all', page: 1, page_size: 20 })
const items = ref<Announcement[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const requestId = ref('')
const counts = ref<Record<string, number>>({})

const dialogVisible = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()
const form = reactive({ title: '', content: '' })
const saving = ref(false)
const rules: FormRules = {
  title: [
    { required: true, message: '请输入公告标题', trigger: 'blur' },
    { min: 4, max: 60, message: '标题长度为 4–60 个字符', trigger: 'blur' }
  ],
  content: [
    { required: true, message: '请输入公告内容', trigger: 'blur' },
    { min: 10, message: '内容至少 10 个字', trigger: 'blur' }
  ]
}

const previewVisible = ref(false)
const active = ref<Announcement | null>(null)
const acting = ref(false)

const tabs = computed(() => [
  { label: '全部', value: 'all', count: counts.value.all },
  { label: '草稿', value: 'draft', count: counts.value.draft },
  { label: '已发布', value: 'published', count: counts.value.published },
  { label: '已下线', value: 'offline', count: counts.value.offline }
])

const columns: TableColumn[] = [
  { label: '公告标题', prop: 'title', minWidth: 260, showOverflowTooltip: true },
  { label: '状态', slot: 'status', width: 90 },
  { label: '作者', prop: 'author', width: 110 },
  { label: '创建时间', slot: 'created', width: 145 },
  { label: '发布时间', slot: 'published', width: 145 },
  { label: '操作', slot: 'actions', width: 210, fixed: 'right' }
]

async function loadCounts(): Promise<void> {
  try {
    counts.value = await adminApi.announcementStats()
  } catch {
    counts.value = {}
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const result = await adminApi.announcements({
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

function openCreate(): void {
  editingId.value = ''
  form.title = ''
  form.content = ''
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown> | Announcement): void {
  const announcement = row as Announcement
  editingId.value = announcement.id
  form.title = announcement.title
  form.content = announcement.content
  dialogVisible.value = true
}

function openPreview(row: Record<string, unknown> | Announcement): void {
  active.value = row as Announcement
  previewVisible.value = true
}

async function save(publishAfter = false): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const announcement = await adminApi.saveAnnouncement({
      id: editingId.value || undefined,
      title: form.title,
      content: form.content
    })
    if (publishAfter) {
      await adminApi.publishAnnouncement(announcement.id)
    }
    ElMessage.success(publishAfter ? '公告已发布' : '公告已保存为草稿')
    dialogVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '保存失败').message)
  } finally {
    saving.value = false
  }
}

async function publish(row: Announcement | null): Promise<void> {
  if (!row) return
  try {
    await ElMessageBox.confirm('确认发布该公告？发布后商家端「平台公告」立即可见。', '发布公告', {
      type: 'info',
      confirmButtonText: '发布'
    })
  } catch {
    return
  }
  acting.value = true
  try {
    await adminApi.publishAnnouncement(row.id)
    ElMessage.success('公告已发布')
    previewVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '发布失败').message)
  } finally {
    acting.value = false
  }
}

async function offline(row: Announcement | null): Promise<void> {
  if (!row) return
  try {
    await ElMessageBox.confirm('确认下线该公告？下线后商家端不再展示。', '下线公告', {
      type: 'warning',
      confirmButtonText: '下线'
    })
  } catch {
    return
  }
  acting.value = true
  try {
    await adminApi.offlineAnnouncement(row.id)
    ElMessage.success('公告已下线')
    previewVisible.value = false
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
      title="公告管理"
      description="平台公告与规则发布；已发布公告同步到商家端「平台公告」列表。"
    >
      <template #actions>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>新建公告
        </el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleFilterBar :loading="loading" @search="search" @reset="reset">
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          clearable
          placeholder="公告标题 / 内容"
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
      empty-text="暂无公告"
      empty-description="创建平台公告后，商家端即可查看发布内容。"
      @row-click="openPreview"
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
      <template #status="{ row }">
        <ConsoleStatusTag kind="announcement" :value="row.status" />
      </template>
      <template #created="{ row }">{{ formatDateTime(row.createdAt) }}</template>
      <template #published="{ row }">{{ formatDateTime(row.publishedAt) }}</template>
      <template #actions="{ row }">
        <div class="console-inline-actions" style="flex-wrap: nowrap" @click.stop>
          <el-button link type="primary" size="small" @click="openPreview(row)">预览</el-button>
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button
            v-if="row.status !== 'published'"
            link
            type="success"
            size="small"
            @click="publish(row)"
          >
            发布
          </el-button>
          <el-button
            v-if="row.status === 'published'"
            link
            type="warning"
            size="small"
            @click="offline(row)"
          >
            下线
          </el-button>
        </div>
      </template>
    </ConsoleDataTable>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑公告' : '新建公告'" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="公告标题" prop="title">
          <el-input v-model="form.title" maxlength="60" show-word-limit />
        </el-form-item>
        <el-form-item label="公告内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="8"
            maxlength="1500"
            show-word-limit
            placeholder="请输入公告正文；演示环境不解析富文本"
          />
        </el-form-item>
        <p class="console-muted" style="font-size: 11px; margin: 0">
          保存草稿不会对外展示；点击「保存并发布」后，平台公告立即可见。
        </p>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button :loading="saving" @click="save(false)">保存草稿</el-button>
        <el-button type="primary" :loading="saving" @click="save(true)">保存并发布</el-button>
      </template>
    </el-dialog>

    <ConsoleDetailDrawer v-model="previewVisible" :title="`公告预览 · ${active?.title || ''}`">
      <template v-if="active">
        <div class="console-alert-row">
          <ConsoleStatusTag kind="announcement" :value="active.status" />
          <span class="console-muted"
            >{{ active.author }} · {{ formatDateTime(active.createdAt) }}</span
          >
          <span v-if="active.publishedAt" class="console-muted">
            发布于 {{ formatDateTime(active.publishedAt) }}
          </span>
        </div>
        <h2 style="font-size: 20px; margin: 8px 0 14px">{{ active.title }}</h2>
        <p style="color: #3f4d46; font-size: 13px; line-height: 2; white-space: pre-wrap">
          {{ active.content }}
        </p>
      </template>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button type="primary" plain @click="active && openEdit(active)">编辑</el-button>
        <el-button
          v-if="active?.status !== 'published'"
          type="success"
          :loading="acting"
          @click="publish(active)"
        >
          发布
        </el-button>
        <el-button v-else type="warning" :loading="acting" @click="offline(active)">
          下线
        </el-button>
      </template>
    </ConsoleDetailDrawer>
  </div>
</template>
