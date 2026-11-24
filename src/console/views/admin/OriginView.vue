<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { EChartsCoreOption } from 'echarts/core'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleFilterBar from '@/console/components/ConsoleFilterBar.vue'
import ConsoleKpiCard from '@/console/components/ConsoleKpiCard.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import ConsoleChart from '@/console/components/ConsoleChart.vue'
import ConsoleDetailDrawer from '@/console/components/ConsoleDetailDrawer.vue'
import type { TableColumn } from '@/console/components/types'
import { adminApi, type Origin } from '@/console/api'
import { toErrorState } from '@/console/utils/errors'

const loading = ref(false)
const error = ref('')
const requestId = ref('')
const origins = ref<Origin[]>([])
const months = ref<string[]>([])
const keyword = ref('')

const detailVisible = ref(false)
const active = ref<Origin | null>(null)
const editVisible = ref(false)
const editForm = reactive({ tagline: '', productCount: 0 })
const editingId = ref('')
const saving = ref(false)

const rows = computed(() => {
  const word = keyword.value.trim()
  if (!word) return origins.value
  return origins.value.filter(
    (item) =>
      item.name.includes(word) || item.location.includes(word) || item.productName.includes(word)
  )
})

const totalSales = computed(() => origins.value.reduce((sum, item) => sum + item.totals.sales, 0))
const totalAid = computed(() => origins.value.reduce((sum, item) => sum + item.totals.aid, 0))
const totalCarbon = computed(() => origins.value.reduce((sum, item) => sum + item.totals.carbon, 0))

const columns: TableColumn[] = [
  { label: '产地', slot: 'origin', minWidth: 165 },
  { label: '主推产品', prop: 'productName', minWidth: 140 },
  { label: '商品数', prop: 'productCount', width: 65, align: 'right' },
  { label: '累计销量', slot: 'sales', width: 90, align: 'right' },
  { label: '助农金额', slot: 'aid', width: 100, align: 'right' },
  { label: '减碳量 (kg)', slot: 'carbon', width: 100, align: 'right' },
  { label: '标签', prop: 'tagline', minWidth: 140, showOverflowTooltip: true },
  { label: '操作', slot: 'actions', width: 100, fixed: 'right' }
]

const overviewOption = computed<EChartsCoreOption>(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 80, right: 24, top: 14, bottom: 22 },
  xAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: '#EDF3EF' } },
    axisLabel: { color: '#8A9891', fontSize: 10 }
  },
  yAxis: {
    type: 'category',
    data: origins.value
      .slice()
      .sort((a, b) => a.totals.sales - b.totals.sales)
      .map((item) => item.name),
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#66746D', fontSize: 11 }
  },
  series: [
    {
      type: 'bar',
      barWidth: 14,
      itemStyle: { color: '#1F7A4D', borderRadius: [0, 6, 6, 0] },
      data: origins.value
        .slice()
        .sort((a, b) => a.totals.sales - b.totals.sales)
        .map((item) => item.totals.sales)
    }
  ]
}))

const detailOption = computed<EChartsCoreOption>(() => {
  const origin = active.value
  return {
    tooltip: { trigger: 'axis' },
    legend: {
      right: 0,
      top: 0,
      itemWidth: 10,
      itemHeight: 8,
      textStyle: { color: '#6B7A74', fontSize: 11 }
    },
    grid: { left: 46, right: 54, top: 36, bottom: 28 },
    xAxis: {
      type: 'category',
      data: months.value,
      axisLine: { lineStyle: { color: '#D7E3DB' } },
      axisLabel: { color: '#8A9891', fontSize: 10, rotate: 30 }
    },
    yAxis: [
      {
        type: 'value',
        name: '销量',
        nameTextStyle: { color: '#96A39C', fontSize: 10 },
        splitLine: { lineStyle: { color: '#EDF3EF' } },
        axisLabel: { color: '#8A9891', fontSize: 10 }
      },
      {
        type: 'value',
        name: '助农金额',
        nameTextStyle: { color: '#96A39C', fontSize: 10 },
        splitLine: { show: false },
        axisLabel: { color: '#8A9891', fontSize: 10 }
      }
    ],
    series: [
      {
        name: '销量',
        type: 'line',
        smooth: true,
        symbolSize: 5,
        itemStyle: { color: '#1F7A4D' },
        areaStyle: { color: 'rgba(31,122,77,0.08)' },
        data: origin?.monthly.sales || []
      },
      {
        name: '助农金额',
        type: 'bar',
        yAxisIndex: 1,
        barWidth: 10,
        itemStyle: { color: '#E8B33B', borderRadius: [4, 4, 0, 0] },
        data: origin?.monthly.aid || []
      }
    ]
  }
})

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const [originResult, monthResult] = await Promise.all([
      adminApi.origins(),
      adminApi.originMonths()
    ])
    origins.value = originResult
    months.value = monthResult
  } catch (err) {
    const state = toErrorState(err)
    error.value = state.message
    requestId.value = state.requestId
  } finally {
    loading.value = false
  }
}

function openDetail(row: Record<string, unknown> | Origin): void {
  active.value = row as Origin
  detailVisible.value = true
}

function openEdit(row: Origin): void {
  editingId.value = row.id
  editForm.tagline = row.tagline
  editForm.productCount = row.productCount
  editVisible.value = true
}

async function save(): Promise<void> {
  if (!editForm.tagline.trim()) {
    ElMessage.warning('请填写产地标签')
    return
  }
  saving.value = true
  try {
    await adminApi.updateOrigin(editingId.value, {
      tagline: editForm.tagline.trim(),
      productCount: Number(editForm.productCount)
    })
    ElMessage.success('产地展示信息已更新')
    editVisible.value = false
    await load()
    if (active.value) {
      active.value = origins.value.find((item) => item.id === active.value?.id) || null
    }
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
      title="产地管理"
      description="复用于消费者端「甘肃产地热力」数据（src/mocks/mock-origin-heat.json），此处可维护展示标签与商品数。"
    >
      <template #actions>
        <el-button @click="load">刷新数据</el-button>
      </template>
    </ConsolePageHeader>

    <div
      v-loading="loading"
      class="console-kpi-grid"
      style="grid-template-columns: repeat(4, minmax(0, 1fr))"
    >
      <ConsoleKpiCard
        label="产地数"
        :value="String(origins.length)"
        hint="来自消费者端产地数据"
        tone="green"
      />
      <ConsoleKpiCard
        label="累计销量"
        :value="totalSales.toLocaleString()"
        hint="单位：件 / 单（演示）"
      />
      <ConsoleKpiCard
        label="助农金额"
        :value="`¥${totalAid.toLocaleString()}`"
        hint="演示统计口径"
        tone="gold"
      />
      <ConsoleKpiCard
        label="累计减碳量"
        :value="`${(totalCarbon / 1000).toFixed(1)} t`"
        hint="按演示系数折算"
        tone="green"
      />
    </div>

    <div v-if="error" class="console-login-error" style="margin-top: 14px">
      {{ error }}
      <button type="button" class="console-link" @click="load">重试</button>
    </div>

    <div class="console-chart-card" style="margin-top: 14px">
      <div class="console-chart-head">
        <h3>各产地累计销量</h3>
        <span class="console-muted">点击下方表格可查看月度趋势</span>
      </div>
      <ConsoleChart :option="overviewOption" height="280px" />
    </div>

    <div style="margin-top: 14px">
      <ConsoleFilterBar :loading="loading" @search="load" @reset="keyword = ''">
        <el-form-item label="产地 / 产品">
          <el-input
            v-model="keyword"
            clearable
            placeholder="搜索产地、主推产品"
            style="width: 240px"
          />
        </el-form-item>
      </ConsoleFilterBar>
    </div>

    <ConsoleDataTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :error="error"
      :error-request-id="requestId"
      :total="rows.length"
      :page="1"
      :page-size="20"
      empty-text="暂无产地数据"
      @row-click="openDetail"
      @retry="load"
    >
      <template #origin="{ row }">
        <div class="console-two-line">
          <strong>{{ row.name }}</strong>
          <span>{{ row.location }}</span>
        </div>
      </template>
      <template #sales="{ row }">{{ row.totals.sales.toLocaleString() }}</template>
      <template #aid="{ row }">¥{{ row.totals.aid.toLocaleString() }}</template>
      <template #carbon="{ row }">{{ row.totals.carbon.toLocaleString() }}</template>
      <template #actions="{ row }">
        <div class="console-inline-actions" @click.stop>
          <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
        </div>
      </template>
    </ConsoleDataTable>

    <ConsoleDetailDrawer v-model="detailVisible" :title="`产地详情 · ${active?.name || ''}`">
      <template v-if="active">
        <div class="console-summary-grid">
          <div class="console-summary-item">
            <span>产地</span><strong style="font-size: 14px">{{ active.location }}</strong>
          </div>
          <div class="console-summary-item">
            <span>主推产品</span><strong style="font-size: 14px">{{ active.productName }}</strong>
          </div>
          <div class="console-summary-item">
            <span>商品数</span><strong>{{ active.productCount }}</strong>
          </div>
          <div class="console-summary-item">
            <span>累计销量</span><strong>{{ active.totals.sales.toLocaleString() }}</strong>
          </div>
          <div class="console-summary-item">
            <span>助农金额</span
            ><strong style="font-size: 16px">¥{{ active.totals.aid.toLocaleString() }}</strong>
          </div>
          <div class="console-summary-item">
            <span>减碳量 (kg)</span
            ><strong style="font-size: 16px">{{ active.totals.carbon.toLocaleString() }}</strong>
          </div>
        </div>
        <div class="console-chart-card" style="margin-top: 14px">
          <div class="console-chart-head">
            <h3>月度销量与助农金额</h3>
            <span class="console-muted">{{ active.tagline }}</span>
          </div>
          <ConsoleChart :option="detailOption" height="280px" />
        </div>
        <p class="console-muted" style="font-size: 11px; line-height: 1.8">
          数据来源：消费者端产地热力 mock（2025-12 至 2026-11）；管理端编辑仅修改展示标签与商品数，
          不会改写消费者端 JSON。
        </p>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button v-if="active" type="primary" @click="openEdit(active)">编辑展示信息</el-button>
      </template>
    </ConsoleDetailDrawer>

    <el-dialog v-model="editVisible" title="编辑产地展示信息" width="480px">
      <el-form label-position="top">
        <el-form-item label="产地标签">
          <el-input v-model="editForm.tagline" maxlength="40" show-word-limit />
        </el-form-item>
        <el-form-item label="商品数量">
          <el-input-number
            v-model="editForm.productCount"
            :min="0"
            :max="9999"
            style="width: 100%"
          />
        </el-form-item>
        <p class="console-muted" style="font-size: 11px; margin: 0">
          该操作不会同步修改消费者端静态 JSON；真实接口接入后应由产地服务统一提供。
        </p>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
