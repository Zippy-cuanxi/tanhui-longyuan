<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { pointsApi } from '@/api'
import { assetUrl } from '@/api/http'
import {
  COUPON_STORE,
  addCouponToWallet,
  ownedCouponCount,
  type CouponStoreItem
} from '@/utils/couponWallet'
import { useAuthStore } from '@/stores/auth'
import { useConfirmStore } from '@/stores/confirm'
import { useToastStore } from '@/stores/toast'
import { errorText } from '@/utils/format'
import AppIcon from '@/components/AppIcon.vue'

const router = useRouter()
const auth = useAuthStore()
const confirm = useConfirmStore()
const toast = useToastStore()

const balance = ref<number | null>(null)
const loading = ref(true)
const exchanging = ref('')
const walletVersion = ref(0)

async function loadBalance(): Promise<void> {
  if (!auth.isAuthenticated) {
    balance.value = null
    loading.value = false
    return
  }
  loading.value = true
  try {
    balance.value = (await pointsApi.account()).balance
  } catch {
    balance.value = null
  } finally {
    loading.value = false
  }
}

function walletCount(item: CouponStoreItem): number {
  void walletVersion.value
  return ownedCouponCount(item.coupon.id)
}

function affordable(item: CouponStoreItem): boolean {
  return balance.value !== null && balance.value >= item.points
}

function actionLabel(item: CouponStoreItem): string {
  if (!auth.isAuthenticated) return '登录兑换'
  if (exchanging.value === item.coupon.id) return '兑换中…'
  if (balance.value === null) return '暂不可兑换'
  return affordable(item) ? '立即兑换' : '积分不足'
}

async function exchange(item: CouponStoreItem): Promise<void> {
  if (exchanging.value) return
  if (!auth.isAuthenticated) {
    router.push({ name: 'login', query: { redirect: '/coupons' } })
    return
  }
  if (!affordable(item)) return

  const ok = await confirm.ask({
    title: '兑换优惠券',
    message: `确认使用 ${item.points} 绿色积分兑换「${item.coupon.title}」吗？兑换后将存入支付页券包。`,
    confirmText: '确认兑换'
  })
  if (!ok) return

  exchanging.value = item.coupon.id
  try {
    await pointsApi.redeem(item.reward_code)
    addCouponToWallet(item.coupon.id)
    walletVersion.value += 1
    toast.show('兑换成功，已存入支付页券包', 'success')
    await loadBalance()
    window.dispatchEvent(new CustomEvent('points:changed'))
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  } finally {
    exchanging.value = ''
  }
}

onMounted(loadBalance)
</script>

<template>
  <main class="page-main coupon-store-page">
    <div class="page-container">
      <header class="page-heading">
        <div>
          <span class="eyebrow">COUPON STORE</span>
          <h1>优惠券商店</h1>
          <p>用绿色积分兑换优惠券，支付时自动抵扣。</p>
        </div>
        <RouterLink to="/account/points" class="outline-button small">
          <AppIcon name="leaf" :size="15" />积分明细
        </RouterLink>
      </header>

      <section class="coupon-store-hero">
        <div class="coupon-store-hero-copy">
          <span class="eyebrow">MY GREEN POINTS</span>
          <p>当前可用绿色积分</p>
          <strong>{{ loading ? '—' : (balance ?? '—') }}<small> 积分</small></strong>
          <p class="muted-text">
            <template v-if="!auth.isAuthenticated"
              >登录后可兑换优惠券，兑换结果会同步到支付页券包。</template
            >
            <template v-else>兑换成功后，优惠券会存入支付页券包，可与绿色积分叠加使用。</template>
          </p>
        </div>
        <img
          class="coupon-store-hero-art"
          :src="assetUrl('/images/coupons/coupon-ticket.webp')"
          alt="优惠券"
          loading="lazy"
        />
      </section>

      <section class="coupon-store-section">
        <header class="section-heading">
          <h2>可兑换优惠券</h2>
          <span class="muted-text">共 {{ COUPON_STORE.length }} 张 · 每单限用 1 张</span>
        </header>
        <div class="coupon-store-grid">
          <article v-for="item in COUPON_STORE" :key="item.coupon.id" class="coupon-store-card">
            <div class="coupon-store-ticket">
              <span class="coupon-store-amount"> <small>¥</small>{{ item.coupon.discount }} </span>
              <div class="coupon-store-info">
                <strong>{{ item.coupon.title }}</strong>
                <span>{{ item.coupon.description }}</span>
                <em>
                  {{ item.coupon.threshold ? `满 ${item.coupon.threshold} 元可用` : '无门槛使用' }}
                  · 有效期至 {{ item.coupon.valid_until }}
                </em>
              </div>
            </div>
            <footer class="coupon-store-actions">
              <span class="coupon-store-cost">
                <AppIcon name="leaf" :size="14" />{{ item.points }} 积分
              </span>
              <span v-if="walletCount(item) > 0" class="coupon-store-owned"
                >券包中 {{ walletCount(item) }} 张</span
              >
              <button
                type="button"
                class="primary-button small"
                :disabled="
                  exchanging === item.coupon.id || (auth.isAuthenticated && !affordable(item))
                "
                @click="exchange(item)"
              >
                {{ actionLabel(item) }}
              </button>
            </footer>
          </article>
        </div>
      </section>

      <section class="coupon-store-guide">
        <h2>兑换说明</h2>
        <ol>
          <li>兑换优惠券需消耗绿色积分，成功后自动存入支付页券包。</li>
          <li>优惠券可用于待支付订单，每单限用 1 张，可与绿色积分抵扣叠加。</li>
          <li>优惠券有效期至 2026-12-31；演示环境的券与积分均为 Mock 数据。</li>
        </ol>
      </section>
    </div>
  </main>
</template>
