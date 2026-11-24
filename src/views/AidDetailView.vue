<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { aidApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { AidProject, AidProjectDonation } from '@/api/types'
import { errorText, formatDate, formatDateTime, percent } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import { usePointsStore } from '@/stores/points'
import { useToastStore } from '@/stores/toast'
import AppIcon from '@/components/AppIcon.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const points = usePointsStore()
const toast = useToastStore()
const projectId = computed(() => String(route.params.id))
const project = ref<AidProject | null>(null)
const donations = ref<AidProjectDonation[]>([])
const loading = ref(true)
const error = ref('')
const donateOpen = ref(false)
const donating = ref(false)
const donateError = ref('')
const lastDonation = ref<{ amount: string; points_earned: number } | null>(null)
const donateForm = reactive({
  amount: 50,
  mode: 'anonymous' as 'anonymous' | 'named',
  name: ''
})
const presetAmounts = [20, 50, 100, 200]
const now = ref(Date.now())
let clockTimer = 0
const amountFormatter = new Intl.NumberFormat('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

function amount(value?: string | number | null): string {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? amountFormatter.format(parsed) : '0.00'
}

function pointsFor(value: number): number {
  return Math.max(0, Math.floor(value * 3))
}

function relativeTime(iso: string): string {
  const time = new Date(iso).getTime()
  if (!Number.isFinite(time)) return iso
  const diff = Math.max(0, now.value - time)
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const month = 30 * day
  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  if (diff < month) return `${Math.floor(diff / day)} 天前`
  return `${Math.floor(diff / month)} 个月前`
}

const displayRaised = computed(() => Number(project.value?.raised_amount || 0))
const displayPercent = computed(() =>
  project.value ? percent(String(displayRaised.value), project.value.goal_amount) : 0
)
const estimatedPoints = computed(() => pointsFor(Number(donateForm.amount) || 0))

function openDonate(): void {
  if (!auth.isAuthenticated) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  donateForm.amount = 50
  donateForm.mode = 'anonymous'
  donateForm.name = auth.displayName
  donateError.value = ''
  donateOpen.value = true
}

function closeDonate(): void {
  donateOpen.value = false
}

function setNamedMode(): void {
  donateForm.mode = 'named'
  if (!donateForm.name.trim()) donateForm.name = auth.displayName
}

function setAmount(value: number): void {
  donateForm.amount = value
}

async function submitDonation(): Promise<void> {
  const amountValue = Number(donateForm.amount)
  if (!Number.isFinite(amountValue) || amountValue <= 0) {
    donateError.value = '请输入有效的资助金额'
    return
  }
  if (donateForm.mode === 'named' && !donateForm.name.trim()) {
    donateError.value = '请填写展示称呼'
    return
  }
  donating.value = true
  donateError.value = ''
  try {
    const result = await aidApi.donate(projectId.value, {
      amount: (Math.round(amountValue * 100) / 100).toFixed(2),
      display_mode: donateForm.mode,
      display_name: donateForm.mode === 'named' ? donateForm.name.trim() : null
    })
    donateOpen.value = false
    now.value = Date.now()
    lastDonation.value = {
      amount: result.amount,
      points_earned: result.points_earned
    }
    if (result.balance != null) points.setBalance(result.balance)
    toast.show(`感谢您的资助，获得 ${result.points_earned} 绿色积分`, 'success')
    await points.fetchBalance()
    window.dispatchEvent(new CustomEvent('points:changed'))
    await Promise.all([loadProject(), loadDonations()])
  } catch (err) {
    donateError.value = errorText(err)
  } finally {
    donating.value = false
  }
}

async function loadProject(): Promise<void> {
  const detail = await aidApi.detail(projectId.value)
  // 接口异常时可能返回空值/空数组，这里统一按“项目不存在”处理，避免白屏
  project.value = detail && !Array.isArray(detail) && detail.id ? detail : null
  if (!project.value) throw new Error('助农项目不存在或已下线')
}

async function loadDonations(): Promise<void> {
  donations.value = await aidApi.projectDonations(projectId.value)
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([loadProject(), loadDonations()])
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  clockTimer = window.setInterval(() => {
    now.value = Date.now()
  }, 60000)
})

onBeforeUnmount(() => window.clearInterval(clockTimer))
</script>

<template>
  <main class="page-main aid-detail-page">
    <div class="page-container narrow-container">
      <StateBlock v-if="loading" :loading="true" />
      <StateBlock v-else-if="error" :error="error" @retry="load" />

      <template v-else-if="project">
        <RouterLink to="/aid" class="back-link">
          <AppIcon name="chevron-left" :size="15" />返回助农项目
        </RouterLink>

        <section class="aid-detail-hero">
          <img
            :src="assetUrl(project.cover_url, '/images/banners/aid-card-farmer.webp')"
            :alt="project.title"
            loading="lazy"
            decoding="async"
          />
          <div class="aid-detail-copy">
            <span class="eyebrow">AID PROJECT</span>
            <h1>{{ project.title }}</h1>
            <p>{{ project.description || '项目说明待补充。' }}</p>
            <div class="aid-progress">
              <div class="aid-progress-bar">
                <span :style="{ width: `${displayPercent}%` }" />
              </div>
              <div class="aid-progress-meta">
                <strong>已筹 ¥{{ amount(displayRaised) }}</strong>
                <span v-if="project.goal_amount"
                  >目标 ¥{{ amount(project.goal_amount) }} · {{ displayPercent }}%</span
                >
              </div>
            </div>
            <dl class="aid-detail-meta">
              <div>
                <dt>项目状态</dt>
                <dd>{{ project.status === 'published' ? '已发布' : project.status }}</dd>
              </div>
              <div>
                <dt>发布时间</dt>
                <dd>{{ formatDate(project.published_at) }}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section class="aid-support-panel">
          <div>
            <span class="eyebrow">SUPPORT THIS PROJECT</span>
            <h2>为项目添一份力</h2>
            <p>选择资助金额与展示方式，匿名或实名均可；资助成功后积分实时到账。</p>
            <p class="aid-point-rule">
              <AppIcon name="leaf" :size="14" />
              资助每 1 元可获得 3 绿色积分（仿真展示）。
            </p>
            <p v-if="points.balance !== null" class="aid-point-rule">
              <AppIcon name="leaf" :size="14" />
              当前绿色积分：{{ points.balance }}
            </p>
          </div>
          <div class="aid-support-side">
            <div>
              <strong>¥{{ amount(displayRaised) }}</strong>
              <small>已筹金额 · 演示数据</small>
            </div>
            <button type="button" class="primary-button" @click="openDonate">
              <AppIcon name="heart" :size="15" />我要资助
            </button>
          </div>
        </section>

        <section v-if="lastDonation" class="aid-support-panel">
          <div>
            <span class="eyebrow">THANK YOU</span>
            <h2>资助成功，绿色积分已到账</h2>
            <p>
              本次资助 ¥{{ amount(lastDonation.amount) }}，获得
              <strong>+{{ lastDonation.points_earned }}</strong> 绿色积分。
            </p>
            <p v-if="points.balance !== null" class="aid-point-rule">
              <AppIcon name="leaf" :size="14" />
              当前绿色积分：{{ points.balance }}
            </p>
          </div>
          <div class="aid-support-side">
            <RouterLink to="/account/points" class="primary-button"> 查看积分明细 </RouterLink>
          </div>
        </section>

        <section v-if="donations.length" class="aid-donor-panel">
          <header class="aid-donor-head">
            <div>
              <span class="eyebrow">SUPPORTERS</span>
              <h2>爱心资助名单</h2>
            </div>
            <span>共 {{ donations.length }} 笔 · 匿名/实名公示</span>
          </header>
          <ul class="aid-donor-list">
            <li v-for="donation in donations.slice(0, 8)" :key="donation.id">
              <span
                class="aid-donor-avatar"
                :class="{ anonymous: donation.display_mode === 'anonymous' }"
              >
                <AppIcon v-if="donation.display_mode === 'anonymous'" name="heart" :size="15" />
                <template v-else>{{ donation.donor.slice(0, 1) }}</template>
              </span>
              <div>
                <strong>{{ donation.donor }}</strong>
                <small :title="formatDateTime(donation.created_at)">
                  {{ donation.display_mode === 'anonymous' ? '匿名资助' : '实名资助' }} ·
                  {{ relativeTime(donation.created_at) }}
                </small>
              </div>
              <div class="aid-donor-value">
                <em>¥{{ amount(donation.amount) }}</em>
              </div>
            </li>
          </ul>
        </section>

        <section class="aid-detail-body">
          <h2>项目说明</h2>
          <p>{{ project.description || '项目说明待补充。' }}</p>
          <h2>参与方式</h2>
          <p>
            可通过购买助农商品或直接资助项目参与。资助时可选择匿名或实名展示，成功后会按 1 元 = 3
            绿色积分发放至账户。
          </p>
          <div class="aid-detail-actions">
            <RouterLink to="/products" class="primary-button">选购助农商品</RouterLink>
            <RouterLink to="/aid" class="outline-button">查看其他项目</RouterLink>
          </div>
          <p class="page-note">
            <AppIcon name="info" :size="15" />
            项目与金额为演示数据，不构成真实募捐或资金承诺。
          </p>
        </section>
      </template>
    </div>

    <Teleport to="body">
      <Transition name="modal">
        <div v-if="donateOpen" class="modal-mask" @click.self="closeDonate">
          <div
            class="modal-card aid-donate-modal"
            role="dialog"
            aria-modal="true"
            aria-label="资助助农项目"
          >
            <header class="modal-card-head">
              <div>
                <span class="eyebrow">SUPPORT PROJECT</span>
                <h2>资助「{{ project?.title }}」</h2>
              </div>
              <button type="button" class="icon-button" aria-label="关闭" @click="closeDonate">
                <AppIcon name="close" :size="18" />
              </button>
            </header>

            <form @submit.prevent="submitDonation">
              <div class="aid-amount-chips">
                <button
                  v-for="value in presetAmounts"
                  :key="value"
                  type="button"
                  :class="{ active: Number(donateForm.amount) === value }"
                  @click="setAmount(value)"
                >
                  ¥{{ value }}
                </button>
              </div>

              <label class="field">
                <span>资助金额</span>
                <input
                  v-model.number="donateForm.amount"
                  type="number"
                  min="1"
                  step="1"
                  placeholder="请输入资助金额"
                />
              </label>

              <div class="aid-mode-options" role="radiogroup" aria-label="资助展示方式">
                <button
                  type="button"
                  :class="{ active: donateForm.mode === 'anonymous' }"
                  @click="donateForm.mode = 'anonymous'"
                >
                  <strong>匿名资助</strong>
                  <small>展示为“匿名爱心人士”</small>
                </button>
                <button
                  type="button"
                  :class="{ active: donateForm.mode === 'named' }"
                  @click="setNamedMode"
                >
                  <strong>实名资助</strong>
                  <small>展示您的称呼</small>
                </button>
              </div>

              <label v-if="donateForm.mode === 'named'" class="field">
                <span>展示称呼</span>
                <input v-model="donateForm.name" maxlength="24" placeholder="请输入展示称呼" />
              </label>

              <p class="aid-donate-points">
                预计获得 <strong>+{{ estimatedPoints }}</strong> 绿色积分（实时到账）
              </p>

              <p v-if="donateError" class="form-error">{{ donateError }}</p>
              <p class="aid-donate-note">
                <AppIcon name="info" :size="14" />资助为演示数据，不会产生真实支付。
              </p>

              <div class="modal-actions">
                <button type="button" class="ghost-button" @click="closeDonate">取消</button>
                <button type="submit" class="primary-button" :disabled="donating">
                  <span v-if="donating" class="mini-spinner" />
                  <AppIcon v-else name="heart" :size="15" />
                  {{ donating ? '提交中…' : '确认资助' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </main>
</template>
