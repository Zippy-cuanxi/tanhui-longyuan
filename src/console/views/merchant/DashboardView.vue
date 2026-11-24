<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { EChartsCoreOption } from 'echarts/core'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleKpiCard from '@/console/components/ConsoleKpiCard.vue'
import ConsoleChart from '@/console/components/ConsoleChart.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleErrorState from '@/console/components/ConsoleErrorState.vue'
import { merchantApi, type MerchantDashboard } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { formatDateTime, formatMoney } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const router = useRouter()
const loading = ref(true)
const error = ref('')
const requestId = ref('')
const data = ref<MerchantDashboard | null>(null)

const merchantId = computed(() => auth.merchantAccount?.id || '')

const trendOption = computed<EChartsCoreOption>(() => {
  const trend = data.value?.trend || []
  return {
    color: ['#CDE8D7', '#1F7A4D'],
    tooltip: { trigger: 'axis' },
    legend: {
      right: 0,
      top: 0,
      itemWidth: 10,
      itemHeight: 8,
      textStyle: { color: '#6B7A74', fontSize: 11 }
    },
    grid: { left: 42, right: 56, top: 40, bottom: 28 },
    xAxis: {
      type: 'category',
      data: trend.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: '#D7E3DB' } },
      axisLabel: { color: '#8A9891', fontSize: 10 }
    },
    yAxis: [
      {
        type: 'value',
        name: '订单数',
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
        barWidth: 14,
        itemStyle: { color: '#CDE8D7', borderRadius: [4, 4, 0, 0] },
        data: trend.map((item) => item.orders)
      },
      {
        name: '销售额',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 6,
        itemStyle: { color: '#1F7A4D' },
        areaStyle: { color: 'rgba(31,122,77,0.07)' },
        data: trend.map((item) => Number(item.sales))
      }
    ]
  }
})

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    data.value = await merchantApi.dashboard(merchantId.value)
  } catch (err) {
    const state = toErrorState(err)
    error.value = state.message
    requestId.value = state.requestId
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="商家工作台"
      :description="`${auth.merchantAccount?.companyName || ''} · 今日经营概览`"
    >
      <template #actions>
        <el-button @click="router.push('/console/merchant/analytics')">
          <el-icon><TrendCharts /></el-icon>数据概览
        </el-button>
        <el-button type="primary" @click="router.push('/console/merchant/products/new')">
          <el-icon><Plus /></el-icon>发布商品
        </el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleErrorState v-if="error" :message="error" :request-id="requestId" @retry="load" />

    <template v-else>
      <div v-loading="loading" class="console-kpi-grid">
        <ConsoleKpiCard
          label="今日订单"
          :value="String(data?.kpis.todayOrders ?? '—')"
          hint="今日新建订单"
          to="/console/merchant/orders"
        />
        <ConsoleKpiCard
          label="今日销售额"
          :value="`¥${formatMoney(data?.kpis.todaySales)}`"
          hint="以支付金额计"
          tone="green"
          to="/console/merchant/analytics"
        />
        <ConsoleKpiCard
          label="待发货"
          :value="String(data?.kpis.pendingShip ?? '—')"
          hint="需在 48 小时内发货"
          tone="gold"
          to="/console/merchant/orders?status=paid"
        />
        <ConsoleKpiCard
          label="待处理售后"
          :value="String(data?.kpis.pendingAftersale ?? '—')"
          hint="需尽快响应买家"
          to="/console/merchant/aftersales"
        />
        <ConsoleKpiCard
          label="可提现余额"
          :value="`¥${formatMoney(data?.kpis.availableBalance)}`"
          hint="结算后可提现"
          tone="green"
          to="/console/merchant/finance"
        />
        <ConsoleKpiCard
          label="在售商品"
          :value="String(data?.kpis.productOnline ?? '—')"
          hint="审核通过且已上架"
          to="/console/merchant/products?status=approved"
        />
      </div>

      <div class="console-todo-row">
        <strong>待办提醒</strong>
        <button class="console-todo" @click="router.push('/console/merchant/orders?status=paid')">
          待发货 <b>{{ data?.kpis.pendingShip ?? 0 }}</b>
        </button>
        <button class="console-todo" @click="router.push('/console/merchant/aftersales')">
          待处理售后 <b>{{ data?.kpis.pendingAftersale ?? 0 }}</b>
        </button>
        <button
          class="console-todo"
          @click="router.push('/console/merchant/products?status=pending_review')"
        >
          审核中商品
        </button>
        <span style="margin-left: auto; color: #96a39c; font-size: 10px">
          数据更新：{{ formatDateTime(data?.updatedAt) }}
        </span>
      </div>

      <div class="console-chart-grid">
        <div class="console-chart-card">
          <div class="console-chart-head">
            <h3>近 7 天订单与销售额</h3>
            <span class="console-muted">仿真数据</span>
          </div>
          <ConsoleChart :option="trendOption" height="280px" />
        </div>
        <div class="console-chart-card">
          <div class="console-chart-head">
            <h3>热销商品 TOP 5</h3>
            <RouterLink class="console-link" to="/console/merchant/products">全部商品</RouterLink>
          </div>
          <div v-if="!data?.topProducts.length" class="console-chart-empty">暂无商品数据</div>
          <ul v-else class="console-rank-list">
            <li v-for="(item, index) in data.topProducts" :key="item.title">
              <b :class="{ top: index < 3 }">{{ index + 1 }}</b>
              <span>{{ item.title }}</span>
              <em>{{ item.sales }} 件</em>
              <strong>¥{{ formatMoney(item.amount) }}</strong>
            </li>
          </ul>
        </div>
      </div>

      <div class="console-card" style="margin-top: 14px">
        <div class="console-card-title">
          <span>最近订单</span>
          <RouterLink class="console-link" to="/console/merchant/orders">查看全部</RouterLink>
        </div>
        <el-table
          v-loading="loading"
          :data="data?.recentOrders || []"
          @row-click="(row: any) => router.push(`/console/merchant/orders/${row.id}`)"
        >
          <el-table-column prop="orderNo" label="订单号" min-width="150" />
          <el-table-column label="买家" min-width="120">
            <template #default="{ row }">{{ row.buyerName }}</template>
          </el-table-column>
          <el-table-column label="金额" width="120">
            <template #default="{ row }">
              <span class="console-amount">¥{{ formatMoney(row.payAmount) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <ConsoleStatusTag kind="order" :value="row.status" />
            </template>
          </el-table-column>
          <el-table-column label="下单时间" min-width="150">
            <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </template>
  </div>
</template>
