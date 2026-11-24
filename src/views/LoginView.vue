<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorText } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import AppIcon from '@/components/AppIcon.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const mfaCode = ref('')
const mfaRequired = ref(false)
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')
const emailRef = ref<HTMLInputElement | null>(null)
const passwordRef = ref<HTMLInputElement | null>(null)
const emailInvalid = ref(false)
const passwordInvalid = ref(false)

const redirect = computed(() =>
  typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
    ? route.query.redirect
    : '/'
)

function fillDemo(): void {
  email.value = 'buyer@tanhui.example.com'
  password.value = 'Passw0rd!123'
}

async function submit(): Promise<void> {
  error.value = ''
  emailInvalid.value = !email.value.trim()
  passwordInvalid.value = !password.value
  if (emailInvalid.value || passwordInvalid.value) {
    error.value = '请填写邮箱和密码'
    const target = emailInvalid.value ? emailRef.value : passwordRef.value
    target?.focus()
    return
  }
  loading.value = true
  try {
    await auth.login({
      email: email.value.trim(),
      password: password.value,
      ...(mfaRequired.value && mfaCode.value ? { mfa_code: mfaCode.value.trim() } : {})
    })
    router.replace(redirect.value)
  } catch (err) {
    emailInvalid.value = false
    passwordInvalid.value = false
    const code = (err as { code?: string }).code
    if (code === 'MFA_REQUIRED') {
      mfaRequired.value = true
      error.value = '该账号需要二次验证，请填写验证码'
    } else if (code === 'MFA_INVALID') {
      error.value = '二次验证码错误，请重新输入'
    } else {
      error.value = errorText(err)
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page" :style="{ backgroundImage: 'url(/images/backgrounds/login-bg.webp)' }">
    <div class="auth-overlay" />
    <RouterLink to="/" class="auth-back">
      <AppIcon name="chevron-left" :size="16" />返回商城
    </RouterLink>

    <section class="auth-brand">
      <img :src="assetUrl('/images/logo/logo.png')" alt="碳惠陇原" class="auth-logo" />
      <span class="eyebrow">GANSU GREEN COMMERCE</span>
      <h1>来自陇原的<br />自然好物</h1>
      <p>绿色生态 · 品质优选 · 助力乡村振兴</p>
      <div class="auth-brand-badges">
        <span><AppIcon name="leaf" :size="15" />绿色产地</span>
        <span><AppIcon name="sparkle" :size="15" />碳积分激励</span>
        <span><AppIcon name="heart" :size="15" />助农公益</span>
      </div>
    </section>

    <section class="auth-card">
      <span class="eyebrow">WELCOME BACK</span>
      <h2>登录碳惠陇原</h2>
      <p class="auth-subtitle">登录后可加入购物车、下单、查看订单与绿色积分。</p>

      <form class="auth-form" @submit.prevent="submit">
        <label class="field">
          <span>邮箱</span>
          <input
            ref="emailRef"
            v-model="email"
            type="email"
            autocomplete="username"
            maxlength="255"
            placeholder="请输入邮箱"
            :aria-invalid="emailInvalid || undefined"
            aria-describedby="login-error"
            @input="emailInvalid = false"
          />
        </label>
        <label class="field">
          <span>密码</span>
          <span class="password-field">
            <input
              ref="passwordRef"
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              maxlength="128"
              placeholder="请输入密码"
              :aria-invalid="passwordInvalid || undefined"
              aria-describedby="login-error"
              @input="passwordInvalid = false"
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
        <label v-if="mfaRequired" class="field">
          <span>二次验证码</span>
          <input
            v-model="mfaCode"
            inputmode="numeric"
            maxlength="8"
            placeholder="请输入 MFA 验证码"
          />
        </label>

        <p v-if="error" id="login-error" class="form-error" role="alert">{{ error }}</p>

        <button
          class="primary-button full-button auth-submit"
          :class="{ 'is-loading': loading }"
          type="submit"
          :disabled="loading"
        >
          <span v-if="loading" class="mini-spinner" />
          {{ loading ? '登录中…' : '登录' }}
        </button>
      </form>

      <div class="auth-links">
        <span>还没有账号？<RouterLink to="/register">立即注册</RouterLink></span>
        <RouterLink to="/help">登录遇到问题？</RouterLink>
      </div>

      <div class="demo-account">
        <div>
          <span class="eyebrow">DEMO ACCOUNT</span>
          <p>演示账号：buyer@tanhui.example.com / Passw0rd!123</p>
        </div>
        <button type="button" class="ghost-button small" @click="fillDemo">填入演示账号</button>
      </div>
    </section>
  </main>
</template>
