<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { EChartsCoreOption } from 'echarts/core'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleKpiCard from '@/console/components/ConsoleKpiCard.vue'
import ConsoleChart from '@/console/components/ConsoleChart.vue'
import ConsoleErrorState from '@/console/components/ConsoleErrorState.vue'
import { adminApi, type AdminDashboard } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { ORDER_STATUS } from '@/console/constants/labels'
import { formatDateTime, formatMoney } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const router = useRouter()
const auth = useConsoleAuth()
const canProduct = computed(() => auth.can('product:read') || auth.can('*'))
const canApprove = computed(() => auth.can('product:approve') || auth.can('*'))
const canReviewMerchant = computed(() => auth.can('merchant:review') || auth.can('*'))
const canReadMerchant = computed(() => auth.can('merchant:read') || auth.can('*'))
const canRefund = computed(() => auth.can('refund:approve') || auth.can('*'))
const canFinance = computed(() => auth.can('finance:read') || auth.can('*'))
const canAid = computed(() => auth.can('aid:manage') || auth.can('*'))
const canUser = computed(() => auth.can('user:read') || auth.can('*'))
const canPoints = computed(() => auth.can('points:manage') || auth.can('*'))
const loading = ref(true)
const error = ref('')
const requestId = ref('')
const data = ref<AdminDashboard | null>(null)

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
    grid: { left: 48, right: 58, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      data: trend.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: '#D7E3DB' } },
      axisLabel: { color: '#8A9891', fontSize: 10 }
    },
    yAxis: [
      {
        type: 'value',
        name: 'GMV',
        nameTextStyle: { color: '#96A39C', fontSize: 10 },
        splitLine: { lineStyle: { color: '#EDF3EF' } },
        axisLabel: { color: '#8A9891', fontSize: 10 }
      },
      {
        type: 'value',
        name: '订单',
        nameTextStyle: { color: '#96A39C', fontSize: 10 },
        splitLine: { show: false },
        axisLabel: { color: '#8A9891', fontSize: 10 }
      }
    ],
    series: [
      {
        name: 'GMV',
        type: 'line',
        smooth: true,
        symbolSize: 5,
        itemStyle: { color: '#1F7A4D' },
        areaStyle: { color: 'rgba(31,122,77,0.08)' },
        data: trend.map((item) => Number(item.gmv))
      },
      {
        name: '订单数',
        type: 'bar',
        yAxisIndex: 1,
        barWidth: 11,
        itemStyle: { color: '#CDE8D7', borderRadius: [4, 4, 0, 0] },
        data: trend.map((item) => item.orders)
      }
    ]
  }
})

const orderStatusOption = computed<EChartsCoreOption>(() => {
  const rows = data.value?.orderStatus || []
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 单 ({d}%)' },
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
        name: '订单状态',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['36%', '50%'],
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 12, fontWeight: 700 } },
        data: rows.map((item) => ({
          name: ORDER_STATUS[item.status]?.label || item.status,
          value: item.count,
          itemStyle: { color: ORDER_STATUS[item.status]?.color || '#96A39C' }
        }))
      }
    ]
  }
})

const categoryOption = computed<EChartsCoreOption>(() => {
  const rows = (data.value?.categoryTop || []).slice().reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 78, right: 20, top: 12, bottom: 20 },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#EDF3EF' } },
      axisLabel: { color: '#8A9891', fontSize: 10 }
    },
    yAxis: {
      type: 'category',
      data: rows.map((item) => item.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#66746D', fontSize: 11 }
    },
    series: [
      {
        type: 'bar',
        barWidth: 14,
        itemStyle: { color: '#1F7A4D', borderRadius: [0, 6, 6, 0] },
        data: rows.map((item) => Number(item.amount))
      }
    ]
  }
})

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    data.value = await adminApi.dashboard()
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
      title="数据看板"
      description="平台经营总览（仿真数据）。所有待办均可下钻到对应处理页面。"
    >
      <template #actions>
        <el-button v-if="canReviewMerchant" @click="router.push('/console/admin/merchants/review')">
          <el-icon><Stamp /></el-icon>入驻审核
        </el-button>
        <el-button
          v-if="canApprove"
          type="primary"
          @click="router.push('/console/admin/products/review')"
        >
          <el-icon><DocumentChecked /></el-icon>商品审核
        </el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleErrorState v-if="error" :message="error" :request-id="requestId" @retry="load" />
    <template v-else>
      <div v-loading="loading" class="console-kpi-grid">
        <ConsoleKpiCard
          label="支付 GMV"
          :value="`¥${formatMoney(data?.kpis.gmvPay)}`"
          hint="扣除已退款金额"
          tone="green"
          :to="canFinance ? '/console/admin/finance' : ''"
        />
        <ConsoleKpiCard
          label="支付订单"
          :value="String(data?.kpis.paidOrders ?? '—')"
          hint="非待付款 / 已取消"
          to="/console/admin/orders"
        />
        <ConsoleKpiCard
          label="客单价"
          :value="`¥${formatMoney(data?.kpis.aov)}`"
          hint="GMV / 支付订单"
        />
        <ConsoleKpiCard
          label="支付率"
          :value="`${data?.kpis.payRate ?? '—'}%`"
          hint="支付订单 / 全部订单"
          tone="gold"
        />
        <ConsoleKpiCard
          label="退款率"
          :value="`${data?.kpis.refundRate ?? '—'}%`"
          hint="退款中 / 已退款订单占比"
          tone="gold"
        />
        <ConsoleKpiCard
          label="近 30 天新增用户"
          :value="String(data?.kpis.newUsers ?? '—')"
          hint="演示口径"
          :to="canUser ? '/console/admin/users' : ''"
        />
      </div>

      <div class="console-todo-row">
        <strong>平台待办</strong>
        <button
          v-if="canApprove"
          class="console-todo"
          @click="router.push('/console/admin/products/review')"
        >
          商品审核 <b>{{ data?.todos.productAudits ?? 0 }}</b>
        </button>
        <button
          v-if="canReviewMerchant"
          class="console-todo"
          @click="router.push('/console/admin/merchants/review')"
        >
          入驻审核 <b>{{ data?.todos.merchantReviews ?? 0 }}</b>
        </button>
        <button
          v-if="canRefund"
          class="console-todo"
          @click="router.push('/console/admin/aftersales')"
        >
          退款 / 仲裁 <b>{{ data?.todos.refunds ?? 0 }}</b>
        </button>
        <button
          v-if="canApprove"
          class="console-todo"
          @click="router.push('/console/admin/products/review')"
        >
          绿色资料 <b>{{ data?.todos.greenReviews ?? 0 }}</b>
        </button>
        <button
          v-if="canFinance"
          class="console-todo"
          @click="router.push('/console/admin/finance')"
        >
          待确认结算 <b>{{ data?.todos.settlementPending ?? 0 }}</b>
        </button>
        <button
          v-if="canProduct"
          class="console-todo"
          @click="router.push('/console/admin/products')"
        >
          库存预警 <b>{{ data?.todos.stockAlerts ?? 0 }}</b>
        </button>
        <span style="margin-left: auto; color: #96a39c; font-size: 10px">
          更新：{{ formatDateTime(data?.updatedAt) }}
        </span>
      </div>

      <div class="console-chart-grid">
        <div class="console-chart-card">
          <div class="console-chart-head">
            <h3>近 30 天 GMV 与订单趋势</h3>
            <span class="console-muted">仿真时间序列</span>
          </div>
          <ConsoleChart :option="trendOption" height="300px" />
        </div>
        <div class="console-chart-card">
          <div class="console-chart-head">
            <h3>订单状态分布</h3>
            <span class="console-muted">全部订单</span>
          </div>
          <ConsoleChart :option="orderStatusOption" height="300px" />
        </div>
      </div>

      <div class="console-chart-grid">
        <div class="console-chart-card">
          <div class="console-chart-head">
            <h3>品类销售 TOP 6</h3>
            <span class="console-muted">按销售额</span>
          </div>
          <ConsoleChart :option="categoryOption" height="260px" />
        </div>
        <div class="console-chart-card">
          <div class="console-chart-head">
            <h3>店铺销售 TOP 10</h3>
            <RouterLink v-if="canReadMerchant" class="console-link" to="/console/admin/merchants">
              全部商家
            </RouterLink>
          </div>
          <ul class="console-rank-list">
            <li v-for="(item, index) in data?.storeTop || []" :key="item.name">
              <b :class="{ top: index < 3 }">{{ index + 1 }}</b>
              <span>{{ item.name }}</span>
              <em>{{ item.orders }} 单</em>
              <strong>¥{{ formatMoney(item.amount) }}</strong>
            </li>
          </ul>
        </div>
      </div>

      <div class="console-admin-summary-grid">
        <section class="console-card">
          <div class="console-card-title">
            <span>助农项目</span>
            <RouterLink v-if="canAid" class="console-link" to="/console/admin/origins">
              产地管理
            </RouterLink>
          </div>
          <div
            class="console-summary-grid"
            style="grid-template-columns: repeat(3, minmax(0, 1fr))"
          >
            <div class="console-summary-item">
              <span>项目数</span><strong>{{ data?.aid.projects ?? '—' }}</strong>
            </div>
            <div class="console-summary-item">
              <span>已筹金额</span>
              <strong style="font-size: 16px">¥{{ formatMoney(data?.aid.raised) }}</strong>
            </div>
            <div class="console-summary-item">
              <span>目标金额</span>
              <strong style="font-size: 16px">¥{{ formatMoney(data?.aid.goal) }}</strong>
            </div>
          </div>
          <ul class="console-rank-list" style="margin-top: 12px">
            <li v-for="(item, index) in (data?.originTop || []).slice(0, 4)" :key="item.name">
              <b :class="{ top: index < 3 }">{{ index + 1 }}</b>
              <span>{{ item.name }}</span>
              <em>{{ item.location }}</em>
              <strong>销量 {{ item.sales }}</strong>
            </li>
          </ul>
        </section>
        <section class="console-card">
          <div class="console-card-title">
            <span>绿色消费</span>
            <span class="console-muted">绿色商品占比</span>
          </div>
          <div class="console-big-number">{{ data?.green.ratio ?? '—' }}<small>%</small></div>
          <el-progress
            :percentage="Math.min(100, Number(data?.green.ratio || 0))"
            :stroke-width="8"
            color="#1F7A4D"
            :show-text="false"
          />
          <p class="console-card-note" style="margin-top: 10px">
            绿色资料已通过商品 {{ data?.green.greenProducts ?? 0 }} 个，在售商品
            {{ data?.green.listedProducts ?? 0 }} 个。
          </p>
        </section>
        <section class="console-card">
          <div class="console-card-title">
            <span>绿豆积分</span>
            <RouterLink
              v-if="canPoints"
              class="console-link"
              to="/console/coming-soon?title=绿色积分规则与流水&module=admin"
            >
              规则（二期）
            </RouterLink>
          </div>
          <div class="console-summary-grid" style="grid-template-columns: 1fr">
            <div class="console-summary-item">
              <span>用户积分余额合计</span>
              <strong>{{ data?.points.balanceTotal ?? '—' }}</strong>
            </div>
          </div>
          <p class="console-card-note" style="margin-top: 10px">
            累计获得 {{ data?.points.earned ?? 0 }}，累计消耗 {{ data?.points.spent ?? 0 }}。
            积分运营工具为二期功能。
          </p>
        </section>
      </div>
    </template>
  </div>
</template>
