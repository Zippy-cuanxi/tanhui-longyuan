<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assetUrl } from '@/api/http'
import { useConsoleAuth } from '@/console/stores/auth'
import ConsoleMockPanel from './ConsoleMockPanel.vue'
import ConsoleNoticeBell from './ConsoleNoticeBell.vue'

defineProps<{ collapsed: boolean }>()
const emit = defineEmits<{ toggle: [] }>()

const route = useRoute()
const router = useRouter()
const auth = useConsoleAuth()

const roleLabel = computed(() => (auth.isMerchant ? '商家后台' : '管理后台'))
const group = computed(() => String(route.meta.group || ''))
const title = computed(() => String(route.meta.title || ''))

/** 头像兜底：登录态里存的地址可能为空、带旧部署前缀或已失效，统一回落到内置头像。 */
const defaultAvatar = computed(() =>
  assetUrl(
    auth.isMerchant
      ? '/console-assets/images/avatar-merchant.png'
      : '/console-assets/images/avatar-admin.png'
  )
)
const avatarFailed = ref(false)
watch(
  () => auth.avatar,
  () => {
    avatarFailed.value = false
  }
)
const avatarSrc = computed(() => {
  if (avatarFailed.value) return defaultAvatar.value
  return assetUrl(auth.avatar) || defaultAvatar.value
})
function onAvatarError(): void {
  avatarFailed.value = true
}

async function onCommand(command: string): Promise<void> {
  if (command === 'home') {
    router.push('/')
    return
  }
  if (command === 'logout') {
    await auth.logout()
    ElMessage.success('已退出登录')
    router.replace('/console/login')
  }
}

function refresh(): void {
  window.location.reload()
}
</script>

<template>
  <header class="console-topbar">
    <div class="console-topbar-left">
      <button type="button" class="console-collapse" title="折叠/展开侧栏" @click="emit('toggle')">
        <el-icon><Fold /></el-icon>
      </button>
      <div class="console-breadcrumb">
        <span>{{ roleLabel }}</span>
        <el-icon><ArrowRight /></el-icon>
        <span v-if="group">{{ group }}</span>
        <el-icon v-if="group"><ArrowRight /></el-icon>
        <strong>{{ title }}</strong>
      </div>
      <span class="console-env-tag">仿真环境</span>
    </div>

    <div class="console-topbar-right">
      <button type="button" class="console-icon-button" title="刷新当前页" @click="refresh">
        <el-icon><Refresh /></el-icon>
      </button>
      <ConsoleMockPanel />
      <ConsoleNoticeBell />
      <el-dropdown trigger="click" @command="onCommand">
        <button type="button" class="console-topbar-user">
          <img :src="avatarSrc" :alt="auth.accountName" @error="onAvatarError" />
          <span>{{ auth.displayName }}</span>
          <el-icon><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              {{ auth.isMerchant ? auth.accountName : auth.adminRoleName }}
            </el-dropdown-item>
            <el-dropdown-item command="home">返回消费者商城</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>
