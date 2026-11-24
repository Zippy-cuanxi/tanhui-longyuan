<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useConsoleUi } from '@/console/install'
import { authApi, type ConsoleRole } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { MockApiError } from '@/console/api/mock'
import { MERCHANT_STATUS } from '@/console/constants/labels'

useConsoleUi()

const route = useRoute()
const router = useRouter()
const auth = useConsoleAuth()

const role = ref<ConsoleRole>('merchant')
const form = reactive({ username: '', password: '' })
const remember = ref(auth.remember)
const submitting = ref(false)
const errors = ref('')
const captchaRequired = ref(false)
const captchaCode = ref('')
const captchaInput = ref('')
const lockRemaining = ref(0)
let ticker: number | undefined

const isMerchant = computed(() => role.value === 'merchant')
const demoAccounts = computed(() => authApi.demoAccounts(role.value))
const lockText = computed(() => {
  const total = Math.max(0, lockRemaining.value)
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${minutes} 分 ${String(seconds).padStart(2, '0')} 秒`
})

interface AttemptState {
  count: number
  lockedUntil?: number
}

function attemptKey(): string {
  return `console_login_attempt_${role.value}_${form.username.trim() || '__'}`
}

function readAttempt(): AttemptState {
  try {
    const raw = localStorage.getItem(attemptKey())
    if (!raw) return { count: 0 }
    const parsed = JSON.parse(raw) as AttemptState
    if (parsed.lockedUntil && parsed.lockedUntil <= Date.now()) {
      localStorage.removeItem(attemptKey())
      return { count: 0 }
    }
    return { count: Number(parsed.count) || 0, lockedUntil: parsed.lockedUntil }
  } catch {
    return { count: 0 }
  }
}

function writeAttempt(state: AttemptState): void {
  if (!state.count && !state.lockedUntil) {
    localStorage.removeItem(attemptKey())
    return
  }
  localStorage.setItem(attemptKey(), JSON.stringify(state))
}

function updateLock(): void {
  const state = readAttempt()
  lockRemaining.value = state.lockedUntil
    ? Math.max(0, Math.ceil((state.lockedUntil - Date.now()) / 1000))
    : 0
  captchaRequired.value = state.count >= 3
  if (captchaRequired.value && !captchaCode.value) refreshCaptcha()
}

function refreshCaptcha(): void {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  captchaCode.value = Array.from(
    { length: 4 },
    () => alphabet[Math.floor(Math.random() * alphabet.length)]
  ).join('')
  captchaInput.value = ''
}

function registerFailure(message: string): void {
  const state = readAttempt()
  state.count += 1
  if (state.count >= 5) {
    state.lockedUntil = Date.now() + 15 * 60 * 1000
    errors.value = `连续登录失败 5 次，账号已锁定 15 分钟。${message}`
  } else if (state.count >= 3) {
    errors.value = `${message}，已连续失败 ${state.count} 次，请输入验证码后重试。`
  } else {
    errors.value = `账号或密码错误（连续失败 ${state.count} 次）。`
  }
  writeAttempt(state)
  updateLock()
}

function clearAttempt(): void {
  localStorage.removeItem(attemptKey())
  captchaRequired.value = false
  captchaInput.value = ''
  captchaCode.value = ''
  lockRemaining.value = 0
}

function switchRole(value: ConsoleRole): void {
  if (role.value === value) return
  role.value = value
  errors.value = ''
  form.password = ''
  captchaCode.value = ''
  captchaInput.value = ''
  updateLock()
}

function fillDemo(username: string): void {
  form.username = username
  form.password = 'Demo@123456'
  errors.value = ''
  updateLock()
}

function goAfterLogin(): void {
  const redirect = String(route.query.redirect || '')
  if (redirect.startsWith('/console/') && !redirect.startsWith('/console/login')) {
    router.replace(redirect)
    return
  }
  router.replace(auth.roleHome)
}

async function submit(): Promise<void> {
  if (submitting.value) return
  errors.value = ''
  if (!form.username.trim()) {
    errors.value = '请输入账号'
    return
  }
  if (!form.password) {
    errors.value = '请输入密码'
    return
  }
  updateLock()
  if (lockRemaining.value > 0) {
    errors.value = `连续失败次数过多，账号已锁定，剩余 ${lockText.value}`
    return
  }
  if (captchaRequired.value && captchaInput.value.trim().toUpperCase() !== captchaCode.value) {
    registerFailure('验证码不正确')
    refreshCaptcha()
    return
  }
  submitting.value = true
  try {
    await auth.login(role.value, form.username, form.password)
    auth.setRemember(remember.value)
    clearAttempt()
    ElMessage.success(isMerchant.value ? '登录成功，欢迎回来' : '登录成功')
    goAfterLogin()
  } catch (error) {
    if (error instanceof MockApiError && error.code === 'BAD_CREDENTIALS') {
      registerFailure(error.message)
      refreshCaptcha()
    } else if (error instanceof MockApiError) {
      errors.value = `${error.message}（request_id: ${error.requestId}）`
    } else {
      errors.value = '登录失败，请稍后重试'
    }
  } finally {
    submitting.value = false
  }
}

function showHelp(message: string): void {
  ElMessage.info(message)
}

watch([role, () => form.username], () => {
  errors.value = ''
  updateLock()
})

onMounted(() => {
  updateLock()
  ticker = window.setInterval(() => {
    updateLock()
  }, 1000)
})

onBeforeUnmount(() => {
  if (ticker) window.clearInterval(ticker)
})
</script>

<template>
  <div
    class="console-login"
    :style="{ backgroundImage: `url('/console-assets/images/login-bg.png')` }"
  >
    <RouterLink to="/" class="console-login-brand" aria-label="返回碳惠陇原商城">
      <img src="/images/logo/logo.png" alt="碳惠陇原" />
      <div>绿色消费 · 助农增收<br />平台运营与商家服务工作台</div>
    </RouterLink>

    <section class="console-login-card" aria-label="后台登录">
      <div class="console-login-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          class="console-login-tab"
          :class="{ active: isMerchant }"
          :aria-selected="isMerchant"
          @click="switchRole('merchant')"
        >
          商家登录
        </button>
        <button
          type="button"
          role="tab"
          class="console-login-tab"
          :class="{ active: !isMerchant }"
          :aria-selected="!isMerchant"
          @click="switchRole('admin')"
        >
          管理员登录
        </button>
      </div>

      <h1>{{ isMerchant ? '商家工作台' : '平台管理后台' }}</h1>
      <p>
        {{
          isMerchant
            ? '管理商品、订单、售后与结算，让甘肃好物走向全国'
            : '审核商家与商品，维护平台交易秩序与运营数据'
        }}
      </p>

      <p v-if="errors" class="console-login-error" role="alert">{{ errors }}</p>
      <p v-if="lockRemaining > 0" class="console-login-error">账号已锁定，剩余 {{ lockText }}</p>

      <el-form class="console-login-form" label-position="top" @submit.prevent="submit">
        <el-form-item label="账号">
          <el-input
            v-model="form.username"
            size="large"
            placeholder="请输入账号"
            autocomplete="username"
            :disabled="submitting"
            @keyup.enter="submit"
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            show-password
            placeholder="请输入密码"
            autocomplete="current-password"
            :disabled="submitting"
            @keyup.enter="submit"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item v-if="captchaRequired" label="图形验证码">
          <div class="console-login-captcha">
            <el-input
              v-model="captchaInput"
              size="large"
              maxlength="4"
              placeholder="输入右侧 4 位验证码"
              @keyup.enter="submit"
            />
            <button
              type="button"
              class="console-captcha-code"
              title="点击刷新验证码"
              @click="refreshCaptcha"
            >
              {{ captchaCode }}
            </button>
          </div>
        </el-form-item>

        <div class="console-login-actions">
          <el-checkbox v-model="remember">记住我（保持登录）</el-checkbox>
          <button
            type="button"
            class="console-link"
            @click="showHelp('演示环境暂不支持找回密码，请使用演示账号登录。')"
          >
            忘记密码？
          </button>
        </div>

        <el-button
          class="console-login-submit"
          type="primary"
          size="large"
          :loading="submitting"
          :disabled="lockRemaining > 0"
          @click="submit"
        >
          {{ lockRemaining > 0 ? `已锁定 ${lockText}` : '登 录' }}
        </el-button>
      </el-form>

      <div class="console-login-links">
        <span>还没入驻？</span>
        <RouterLink to="/join">申请商家入驻</RouterLink>
      </div>

      <div class="console-login-demo">
        <strong>演示账号 · 统一密码 Demo@123456</strong>
        <button
          v-for="account in demoAccounts"
          :key="account.username"
          type="button"
          @click="fillDemo(account.username)"
        >
          {{ account.username }}
          <template v-if="account.status && isMerchant">
            （{{ MERCHANT_STATUS[account.status]?.label || account.status }}）
          </template>
        </button>
        <span>连续失败 5 次锁定 15 分钟；失败 3 次后需验证码。</span>
      </div>
    </section>

    <footer class="console-login-foot">
      碳惠陇原 · 后台管理系统（仿真环境） · 数据仅用于前端演示
    </footer>
  </div>
</template>
