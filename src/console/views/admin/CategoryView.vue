<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleFilterBar from '@/console/components/ConsoleFilterBar.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import type { TableColumn } from '@/console/components/types'
import { adminApi, type Category } from '@/console/api'
import { toErrorState } from '@/console/utils/errors'

const loading = ref(false)
const error = ref('')
const requestId = ref('')
const categories = ref<Category[]>([])
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()
const form = reactive({ name: '', sort: 1, enabled: true })
const saving = ref(false)
const rules: FormRules = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { min: 2, max: 12, message: '分类名称为 2–12 个字符', trigger: 'blur' }
  ],
  sort: [{ required: true, message: '请输入排序值', trigger: 'blur' }]
}

const rows = computed(() => {
  const word = keyword.value.trim()
  if (!word) return categories.value
  return categories.value.filter((item) => item.name.includes(word))
})

const columns: TableColumn[] = [
  { label: '分类名称', prop: 'name', minWidth: 180 },
  { label: '商品数量', prop: 'productCount', width: 100, align: 'right' },
  { label: '排序', prop: 'sort', width: 80, align: 'right' },
  { label: '启用状态', slot: 'enabled', width: 110 },
  { label: '分类 ID', slot: 'id', minWidth: 130 },
  { label: '操作', slot: 'actions', width: 100, fixed: 'right' }
]

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    categories.value = await adminApi.categories()
  } catch (err) {
    const state = toErrorState(err)
    error.value = state.message
    requestId.value = state.requestId
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editingId.value = ''
  form.name = ''
  form.sort = categories.value.length + 1
  form.enabled = true
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown> | Category): void {
  const category = row as Category
  editingId.value = category.id
  form.name = category.name
  form.sort = category.sort
  form.enabled = category.enabled
  dialogVisible.value = true
}

async function save(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await adminApi.saveCategory({
      id: editingId.value || undefined,
      name: form.name,
      sort: Number(form.sort),
      enabled: form.enabled
    })
    ElMessage.success(editingId.value ? '分类已更新' : '分类已创建')
    dialogVisible.value = false
    await load()
  } catch (err) {
    ElMessage.error(toErrorState(err, '保存失败').message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="分类管理"
      description="维护商品分类与展示排序；分类被商品引用后不建议停用。"
    >
      <template #actions>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>新增分类
        </el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleFilterBar :loading="loading" @search="load" @reset="keyword = ''">
      <el-form-item label="分类名称">
        <el-input v-model="keyword" clearable placeholder="搜索分类" style="width: 220px" />
      </el-form-item>
    </ConsoleFilterBar>

    <ConsoleDataTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :error="error"
      :error-request-id="requestId"
      :total="rows.length"
      :page="1"
      :page-size="20"
      empty-text="暂无分类"
      @retry="load"
    >
      <template #enabled="{ row }">
        <span
          class="console-status"
          :style="
            row.enabled
              ? { color: '#2E9E5B', background: '#E8F6ED' }
              : { color: '#6B7A74', background: '#EFF3F1' }
          "
        >
          <i />{{ row.enabled ? '启用中' : '已停用' }}
        </span>
      </template>

      <template #id="{ row }"
        ><span class="console-code">{{ row.id }}</span></template
      >

      <template #actions="{ row }">
        <div class="console-inline-actions" @click.stop>
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
        </div>
      </template>
    </ConsoleDataTable>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑分类' : '新增分类'" width="460px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="form.name" maxlength="12" show-word-limit />
        </el-form-item>
        <el-form-item label="排序值（越小越靠前）" prop="sort">
          <el-input-number v-model="form.sort" :min="1" :max="99" style="width: 100%" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <p class="console-muted" style="font-size: 11px; margin: 0">
          当前为演示数据；分类停用后不影响已发布商品，但新增商品将无法选择该分类。
        </p>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
