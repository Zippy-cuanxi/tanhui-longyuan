<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { downloadCsv } from '@/console/utils/format'

const props = withDefaults(
  defineProps<{
    filename: string
    rows: Array<Record<string, string | number>>
    headers: Array<{ key: string; label: string }>
    label?: string
  }>(),
  { label: '导出' }
)

function exportRows(): void {
  if (!props.rows.length) {
    ElMessage.warning('当前筛选没有可导出的数据')
    return
  }
  downloadCsv(props.filename, props.rows, props.headers)
  ElMessage.success(`已导出 ${props.rows.length} 条数据（演示 CSV）`)
}
</script>

<template>
  <el-button plain @click="exportRows">
    <el-icon><Download /></el-icon>{{ label }}
  </el-button>
</template>
