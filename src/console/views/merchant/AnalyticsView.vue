<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { EChartsCoreOption } from 'echarts/core'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleKpiCard from '@/console/components/ConsoleKpiCard.vue'
import ConsoleChart from '@/console/components/ConsoleChart.vue'
import ConsoleErrorState from '@/console/components/ConsoleErrorState.vue'
import { merchantApi, type AnalyticsData } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const merchantId = computed(() => auth.merchantAccount?.id || '')
const range = ref<'7' | '30'>('7')
const data = ref<AnalyticsData | null>(null)
const loading = ref(true)
const error = ref('')
const requestId = ref('')

const trendOption = computed<EChartsCoreOption>(() => {
  const trend = data.value?.trend || []
  return {
    tooltip: { trigger: 'axis' },
    legend: {
      right: 0,
      top: 0,
      itemWidth: 10,
      itemHeight: 8,
      textStyle: { color: '#6B7A74', fontSize: 11 }
    },
    grid: { left: 42, right: 54, top: 38, bottom: 28 },
    xAxis: {
      type: 'category',
      data: trend.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: '#D7E3DB' } },
      axisLabel: { color: '#8A9891', fontSize: 10 }
    },
    yAxis: [
      {
        type: 'value',
        name: '订单',
        nameTextStyle: { color: '#96A39C', fontSize: 10 },
        splitLine: { lineStyle: { color: '#EDF3EF' } },
        axisLabel: { color: '#8A9891', fontSize: 10 }
      },
      {
        type: 'value',
        name: '销售额',
        nameTextStyle: { color: '#96A39C', fontSize: 10 },
        splitLine: { show: false },
        axisLabel: { color: '#8A9891', fontSize: 10 }
      }
    ],
    series: [
      {
        name: '订单数',
        type: 'bar',
        barWidth: 13,
        itemStyle: { color: '#CDE8D7', borderRadius: [4, 4, 0, 0] },
        data: trend.map((item) => item.orders)
      },
      {
        name: '销售额',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 5,
        itemStyle: { color: '#1F7A4D' },
        areaStyle: { color: 'rgba(31,122,77,0.07)' },
        data: trend.map((item) => Number(item.sales))
      }
    ]
  }
})

const categoryOption = computed<EChartsCoreOption>(() => {
  const list = data.value?.categoryShare || []
  return {
    color: ['#1F7A4D', '#E8B33B', '#3B82C4', '#E8892B', '#8A6D3B', '#D64545'],
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 0,
      top: 'middle',
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: '#66746D', fontSize: 11 }
    },
    series: [
      {
        name: '品类占比',
        type: 'pie',
        radius: ['46%', '70%'],
        center: ['38%', '50%'],
        avoidLabelOverlap: true,
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 12, fontWeight: 700, color: '#1F2026' }
        },
        data: list
      }
    ]
  }
})

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    data.value = await merchantApi.analytics(merchantId.value, range.value)
  } catch (err) {
    const state = toErrorState(err)
    error.value = state.message
    requestId.value = state.requestId
  } finally {
    loading.value = false
  }
}

function changeRange(value: '7' | '30'): void {
  range.value = value
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="数据概览"
      description="商家经营数据为 mock 聚合结果；真实接口接入后按同一指标口径替换。"
    >
      <template #actions>
        <el-radio-group :model-value="range" @update:model-value="changeRange">
          <el-radio-button value="7">近 7 天</el-radio-button>
          <el-radio-button value="30">近 30 天</el-radio-button>
        </el-radio-group>
      </template>
    </ConsolePageHeader>

    <ConsoleErrorState v-if="error" :message="error" :request-id="requestId" @retry="load" />
    <template v-else>
      <div
        v-loading="loading"
        class="console-kpi-grid"
        style="grid-template-columns: repeat(4, minmax(0, 1fr))"
      >
        <ConsoleKpiCard
          v-for="item in data?.kpis || []"
          :key="item.label"
          :label="item.label"
          :value="item.value"
          :hint="item.hint"
          tone="green"
        />
      </div>
      <div class="console-chart-grid">
        <div class="console-chart-card">
          <div class="console-chart-head">
            <h3>订单与销售额趋势</h3>
            <span class="console-muted">{{ data?.range || '' }}</span>
          </div>
          <ConsoleChart :option="trendOption" height="320px" />
        </div>
        <div class="console-chart-card">
          <div class="console-chart-head">
            <h3>品类销售占比</h3>
            <span class="console-muted">按销售额</span>
          </div>
          <ConsoleChart v-if="data?.categoryShare.length" :option="categoryOption" height="320px" />
          <div v-else class="console-chart-empty">暂无品类数据</div>
        </div>
      </div>
      <div class="console-card" style="margin-top: 14px">
        <div class="console-card-title">指标说明</div>
        <p class="console-card-note">
          支付订单数、销售额、在售商品数来自本地 mock
          数据；好评率因评价接口未纳入一期，显示为「—」。
          销售额按服务端订单实付金额口径；绿色消费与助农贡献金额为演示数据，不作为财务凭证。
        </p>
        <p class="console-muted" style="font-size: 11px">
          最后更新：{{ new Date().toLocaleString('zh-CN') }}
        </p>
      </div>
    </template>
  </div>
</template>
