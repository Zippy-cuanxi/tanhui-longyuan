<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { aidApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { AidProject } from '@/api/types'
import { errorText, percent } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'
import BannerSection from '@/components/sections/BannerSection.vue'
import StateBlock from '@/components/StateBlock.vue'

const projects = ref<AidProject[]>([])
const loading = ref(true)
const error = ref('')

const amountFormatter = new Intl.NumberFormat('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

const totalRaised = computed(() =>
  projects.value.reduce((total, project) => total + Number(project.raised_amount || 0), 0)
)

const averageProgress = computed(() => {
  if (!projects.value.length) return 0
  const total = projects.value.reduce(
    (sum, project) => sum + percent(project.raised_amount, project.goal_amount),
    0
  )
  return Math.round(total / projects.value.length)
})

function amount(value?: string | number | null): string {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? amountFormatter.format(parsed) : '0.00'
}

function statusLabel(status: string): string {
  return status === 'published' ? '公示中' : status
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const data = await aidApi.list({ page: 1, page_size: 12 })
    projects.value = data.items
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-main aid-page aid-page-v2">
    <div class="page-container">
      <BannerSection
        :config="{
          title: '助农项目',
          image_url: assetUrl('/images/banners/aid.webp'),
          link_url: '/aid#aid-projects'
        }"
        variant="page"
        :fallback-image="assetUrl('/images/banners/aid.webp')"
      />

      <section class="aid-stats" aria-label="助农项目数据概览">
        <div class="aid-stat">
          <span>累计助农金额（演示）</span>
          <strong>¥{{ amount(totalRaised) }}</strong>
          <small>四个项目累计已筹金额</small>
        </div>
        <div class="aid-stat">
          <span>在公示助农项目</span>
          <strong>{{ projects.length }} <em>个</em></strong>
          <small>已通过平台审核</small>
        </div>
        <div class="aid-stat">
          <span>覆盖甘肃产区</span>
          <strong>{{ projects.length }} <em>区</em></strong>
          <small>涉及省内多个县域</small>
        </div>
        <div class="aid-stat">
          <span>平均筹资进度</span>
          <strong>{{ averageProgress }}%</strong>
          <small>当前项目平均完成度</small>
        </div>
      </section>

      <section id="aid-projects" class="section-block">
        <header class="aid-section-head">
          <div>
            <span class="eyebrow">AID PROJECTS</span>
            <h2>助农项目</h2>
          </div>
          <RouterLink to="/aid#aid-disclosure" class="more-link">
            查看全部项目 <AppIcon name="arrow-right" :size="13" />
          </RouterLink>
        </header>

        <StateBlock
          :loading="loading"
          :error="error"
          :empty="!loading && !error && !projects.length"
          empty-text="暂无已发布的助农项目"
          @retry="load"
        >
          <div class="aid-grid aid-grid-v2">
            <article v-for="project in projects" :key="project.id" class="aid-card aid-card-v2">
              <RouterLink :to="`/aid/${project.id}`" class="aid-card-image">
                <img
                  :src="assetUrl(project.cover_url, '/images/banners/aid-card-farm.webp')"
                  :alt="project.title"
                  loading="lazy"
                  decoding="async"
                />
                <span class="aid-card-badge"><AppIcon name="heart" :size="13" />助农项目</span>
              </RouterLink>
              <div class="aid-card-body">
                <div class="aid-card-tags">
                  <span class="aid-card-tag">助农项目</span>
                  <span class="aid-card-tag gold">{{ statusLabel(project.status) }}</span>
                </div>
                <h2>
                  <RouterLink :to="`/aid/${project.id}`">{{ project.title }}</RouterLink>
                </h2>
                <p>{{ project.description || '项目说明待补充。' }}</p>
                <div class="aid-progress">
                  <div class="aid-progress-bar">
                    <span
                      :style="{ width: `${percent(project.raised_amount, project.goal_amount)}%` }"
                    />
                  </div>
                  <div class="aid-progress-meta">
                    <strong>已筹 ¥{{ amount(project.raised_amount) }}</strong>
                    <span v-if="project.goal_amount">
                      目标 ¥{{ amount(project.goal_amount) }} ·
                      {{ percent(project.raised_amount, project.goal_amount) }}%
                    </span>
                  </div>
                </div>
                <RouterLink :to="`/aid/${project.id}`" class="aid-view-link">
                  查看项目 <AppIcon name="arrow-right" :size="13" />
                </RouterLink>
              </div>
            </article>
          </div>
        </StateBlock>
      </section>

      <section id="aid-disclosure" class="section-block">
        <header class="aid-section-head">
          <div>
            <span class="eyebrow">DISCLOSURE</span>
            <h2>资金与进展公示</h2>
          </div>
          <RouterLink to="/notices" class="more-link">
            公示规则说明 <AppIcon name="arrow-right" :size="13" />
          </RouterLink>
        </header>

        <div class="aid-table-wrap">
          <table class="aid-table">
            <thead>
              <tr>
                <th>项目名称</th>
                <th>已筹金额</th>
                <th>目标金额</th>
                <th>筹资进度</th>
                <th>公示状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="project in projects" :key="project.id">
                <td>
                  <RouterLink :to="`/aid/${project.id}`">{{ project.title }}</RouterLink>
                </td>
                <td class="aid-table-amount">¥{{ amount(project.raised_amount) }}</td>
                <td class="aid-table-amount muted">¥{{ amount(project.goal_amount) }}</td>
                <td>
                  <div class="aid-table-progress">
                    <span class="aid-table-bar">
                      <em
                        :style="{
                          width: `${percent(project.raised_amount, project.goal_amount)}%`
                        }"
                      />
                    </span>
                    <small>{{ percent(project.raised_amount, project.goal_amount) }}%</small>
                  </div>
                </td>
                <td>
                  <span class="aid-status-tag">{{ statusLabel(project.status) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="!projects.length && !loading && !error" class="aid-table-empty">暂无公示数据</p>
        </div>
        <p class="aid-disclosure-note">
          金额说明：数据为演示内容，不构成真实募捐或资金承诺；真实资金流与公示规则待业务确认。
        </p>
      </section>

      <section class="section-block">
        <header class="aid-section-head">
          <div>
            <span class="eyebrow">HOW IT WORKS</span>
            <h2>参与方式</h2>
          </div>
        </header>
        <div class="aid-steps">
          <article class="aid-step">
            <span class="aid-step-no">01</span>
            <h3>选购助农商品</h3>
            <p>在商品列表选择带有“助农好物”标记的商品，下单即参与助农。</p>
          </article>
          <article class="aid-step">
            <span class="aid-step-no">02</span>
            <h3>直接资助项目</h3>
            <p>进入项目详情选择资助金额，匿名或实名均可，并获得仿真绿色积分。</p>
          </article>
          <article class="aid-step">
            <span class="aid-step-no">03</span>
            <h3>关注进展公示</h3>
            <p>项目筹资金额与进展在本页公示，接受用户监督。</p>
          </article>
        </div>
      </section>

      <p class="page-note">
        <AppIcon name="info" :size="15" />
        助农项目与金额为演示数据，不构成真实募捐或资金承诺；真实资金流与公示规则待业务确认。
      </p>
    </div>
  </main>
</template>
