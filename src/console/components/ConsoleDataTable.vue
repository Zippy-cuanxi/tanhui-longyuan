<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { ref } from 'vue'
import type { TableColumn } from './types'
import ConsoleEmptyState from './ConsoleEmptyState.vue'
import ConsoleErrorState from './ConsoleErrorState.vue'

type TableRow = Record<string, any>

withDefaults(
  defineProps<{
    columns: TableColumn[]
    rows: TableRow[]
    loading?: boolean
    error?: string
    errorRequestId?: string
    total?: number
    page?: number
    pageSize?: number
    rowKey?: string
    selectable?: boolean
    emptyText?: string
    emptyImage?: string
    emptyDescription?: string
  }>(),
  {
    loading: false,
    error: '',
    errorRequestId: '',
    total: 0,
    page: 1,
    pageSize: 20,
    rowKey: 'id',
    selectable: false,
    emptyText: '暂无数据',
    emptyImage: assetUrl('/console-assets/images/empty-list.png'),
    emptyDescription: ''
  }
)

const emit = defineEmits<{
  'row-click': [row: TableRow]
  'selection-change': [rows: TableRow[]]
  'update:page': [page: number]
  'update:pageSize': [size: number]
  retry: []
}>()

const selected = ref<TableRow[]>([])

function display(column: TableColumn, row: TableRow): string {
  if (column.formatter) return String(column.formatter(row))
  const value = column.prop ? row[column.prop] : ''
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (Array.isArray(value)) return value.join('、')
  return String(value)
}

function onSelectionChange(rows: TableRow[]): void {
  selected.value = rows
  emit('selection-change', rows)
}

function onRowClick(row: TableRow): void {
  emit('row-click', row)
}
</script>

<template>
  <section class="console-table-card">
    <div v-if="selectable && selected.length" class="console-bulk-bar">
      <span>已选择 {{ selected.length }} 项</span>
      <slot name="bulk" :selected="selected" />
    </div>

    <ConsoleErrorState
      v-if="error"
      :message="error"
      :request-id="errorRequestId"
      @retry="emit('retry')"
    />
    <div v-else-if="loading && !rows.length" class="console-table-skeleton">
      <el-skeleton :rows="6" animated />
    </div>
    <el-table
      v-else
      v-loading="loading"
      :data="rows"
      :row-key="rowKey"
      @row-click="onRowClick"
      @selection-change="onSelectionChange"
    >
      <el-table-column v-if="selectable" type="selection" width="44" />
      <el-table-column
        v-for="column in columns"
        :key="column.label"
        :prop="column.prop"
        :label="column.label"
        :width="column.width"
        :min-width="column.minWidth"
        :align="column.align || 'left'"
        :show-overflow-tooltip="column.showOverflowTooltip"
        :fixed="column.fixed"
      >
        <template #default="scope">
          <slot
            v-if="column.slot"
            :name="column.slot"
            :row="scope.row"
            :value="column.prop ? scope.row[column.prop] : undefined"
            :index="scope.$index"
          />
          <span v-else>{{ display(column, scope.row) }}</span>
        </template>
      </el-table-column>
      <template #empty>
        <ConsoleEmptyState :image="emptyImage" :title="emptyText" :description="emptyDescription" />
      </template>
    </el-table>

    <div v-if="!error && rows.length" class="console-table-footer">
      <span>共 {{ total }} 条</span>
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[20, 50, 100]"
        :total="total"
        layout="sizes, prev, pager, next, jumper"
        @current-change="(value: number) => emit('update:page', value)"
        @size-change="(value: number) => emit('update:pageSize', value)"
      />
    </div>
  </section>
</template>
