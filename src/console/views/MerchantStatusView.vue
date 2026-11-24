<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useConsoleUi } from '@/console/install'
import { useConsoleAuth } from '@/console/stores/auth'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'

useConsoleUi()

const router = useRouter()
const auth = useConsoleAuth()

const status = computed(() => auth.merchantStatus || 'pending')
const account = computed(() => auth.merchantAccount)
const image = computed(() => {
  if (status.value === 'rejected') return assetUrl('/console-assets/images/state-rejected.webp')
  if (status.value === 'frozen') return assetUrl('/console-assets/images/state-frozen.webp')
  return assetUrl('/console-assets/images/state-pending.webp')
})
const title = computed(() => {
  if (status.value === 'rejected') return '入驻审核未通过'
  if (status.value === 'frozen') return '商家账号已被冻结'
  return '入驻资料审核中'
})
const description = computed(() => {
  if (status.value === 'rejected') {
    return '你提交的入驻资料未通过平台审核，请根据驳回原因修改资料后重新提交。'
  }
  if (status.value === 'frozen') {
    return '因平台规则或经营异常，当前账号已暂停使用。冻结期间无法进入商家工作台。'
  }
  return '平台正在核验你的营业执照与经营资质，预计 1–3 个工作日完成审核，请耐心等待。'
})
const reason = computed(() => account.value?.rejectReason || account.value?.frozenReason || '')

async function logout(): Promise<void> {
  await auth.logout()
  await router.replace('/console/login')
}

function retrySubmit(): void {
  ElMessage.info('演示环境：重新提交资料入口将在正式商家入驻流程中开放。')
}

onMounted(() => {
  if (!auth.session) {
    router.replace('/console/login')
    return
  }
  if (auth.merchantStatus === 'normal') {
    router.replace('/console/merchant/dashboard')
  }
})
</script>

<template>
  <div class="console-status-page">
    <section class="console-status-card">
      <img :src="image" alt="账号状态" />
      <h1>{{ title }}</h1>
      <div style="margin-bottom: 8px">
        <ConsoleStatusTag kind="merchant" :value="status" />
      </div>
      <p>{{ description }}</p>

      <div
        v-if="account"
        class="console-summary-grid"
        style="width: 100%; margin-top: 14px; grid-template-columns: repeat(2, minmax(0, 1fr))"
      >
        <div class="console-summary-item">
          <span>主体名称</span>
          <strong style="font-size: 14px">{{ account.companyName }}</strong>
        </div>
        <div class="console-summary-item">
          <span>登录账号</span>
          <strong style="font-size: 14px">{{ account.username }}</strong>
        </div>
      </div>

      <div v-if="reason" class="console-status-reason">
        <strong>{{ status === 'frozen' ? '冻结原因：' : '驳回原因：' }}</strong>
        {{ reason }}
      </div>

      <div class="console-inline-actions" style="justify-content: center; margin-top: 10px">
        <el-button v-if="status === 'rejected'" type="primary" @click="retrySubmit">
          修改资料并重新提交
        </el-button>
        <el-button v-else type="primary" @click="logout">退出登录</el-button>
        <el-button v-if="status === 'rejected'" @click="logout">退出登录</el-button>
        <RouterLink to="/">
          <el-button plain>返回消费者商城</el-button>
        </RouterLink>
      </div>

      <p style="margin-top: 16px">
        如需帮助，请联系平台客服：0931-8888888（演示环境不产生真实通话与工单）
      </p>
    </section>
  </div>
</template>
