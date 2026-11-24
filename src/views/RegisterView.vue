<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorText } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import AppIcon from '@/components/AppIcon.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const nickname = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

const redirect = computed(() =>
  typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
    ? route.query.redirect
    : '/'
)

function validate(): string {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) return '请填写有效的邮箱地址'
  if (password.value.length < 8) return '密码至少 8 位'
  if (password.value !== confirmPassword.value) return '两次输入的密码不一致'
  return ''
}

async function submit(): Promise<void> {
  error.value = validate()
  if (error.value) return
  loading.value = true
  try {
    await auth.register({
      email: email.value.trim(),
      password: password.value,
      nickname: nickname.value.trim() || undefined
    })
    router.replace(redirect.value)
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page" :style="{ backgroundImage: 'url(/assets/brand/login-bg.webp)' }">
    <div class="auth-overlay" />
    <RouterLink to="/" class="auth-back">
      <AppIcon name="chevron-left" :size="16" />返回商城
    </RouterLink>

    <section class="auth-brand">
      <img src="/assets/brand/logo.png" alt="碳惠陇原" class="auth-logo" />
      <span class="eyebrow">JOIN TANHUI</span>
      <h1>把陇原好物<br />带回家</h1>
      <p>注册即可查看绿色积分、订单与助农项目。</p>
      <div class="auth-brand-badges">
        <span><AppIcon name="leaf" :size="15" />绿色产地</span>
        <span><AppIcon name="shield" :size="15" />平台审核</span>
        <span><AppIcon name="heart" :size="15" />助农公益</span>
      </div>
    </section>

    <section class="auth-card">
      <span class="eyebrow">CREATE ACCOUNT</span>
      <h2>注册消费者账号</h2>
      <p class="auth-subtitle">当前仅开放消费者注册；商家入驻请使用商家工作台。</p>

      <form class="auth-form" @submit.prevent="submit">
        <label class="field">
          <span>邮箱</span>
          <input
            v-model="email"
            type="email"
            autocomplete="email"
            maxlength="255"
            placeholder="用于登录与订单通知"
          />
        </label>
        <label class="field">
          <span>昵称（选填）</span>
          <input v-model="nickname" maxlength="64" placeholder="如何称呼你" />
        </label>
        <label class="field">
          <span>密码</span>
          <span class="password-field">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="new-password"
              maxlength="128"
              placeholder="至少 8 位"
            />
            <button
              type="button"
              class="password-toggle"
              :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              @click="showPassword = !showPassword"
            >
              <AppIcon name="eye" :size="17" />
            </button>
          </span>
        </label>
        <label class="field">
          <span>确认密码</span>
          <input
            v-model="confirmPassword"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="new-password"
            maxlength="128"
            placeholder="再次输入密码"
          />
        </label>

        <p v-if="error" class="form-error">{{ error }}</p>

        <button class="primary-button full-button auth-submit" type="submit" :disabled="loading">
          <span v-if="loading" class="mini-spinner" />
          {{ loading ? '注册中…' : '注册并登录' }}
        </button>
      </form>

      <div class="auth-links">
        <span>已有账号？<RouterLink to="/login">去登录</RouterLink></span>
        <RouterLink to="/help">查看帮助</RouterLink>
      </div>
      <p class="auth-fineprint">
        注册即表示同意平台交易与隐私规则；当前为演示环境，请勿填写真实敏感信息。
      </p>
    </section>
  </main>
</template>
