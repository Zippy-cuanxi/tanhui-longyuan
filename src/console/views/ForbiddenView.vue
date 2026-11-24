<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { useRouter } from 'vue-router'
import { useConsoleAuth } from '@/console/stores/auth'

const router = useRouter()
const auth = useConsoleAuth()

async function switchAccount(): Promise<void> {
  await auth.logout()
  await router.replace('/console/login')
}
</script>

<template>
  <section class="console-forbidden-page" style="min-height: calc(100vh - 150px)">
    <div class="console-forbidden-card">
      <img :src="assetUrl('/console-assets/images/no-permission.png')" alt="无权限" />
      <h1 style="margin: 8px 0 6px; font-size: 22px">当前账号无此权限</h1>
      <p style="color: #7b8881; font-size: 12px; line-height: 1.8">
        你的角色为「{{ auth.adminRoleName || '商家账号' }}」，无权访问该页面或执行该操作。
        <br />
        如有业务需要，请联系平台超级管理员调整角色权限。
      </p>
      <div class="console-inline-actions" style="justify-content: center; margin-top: 14px">
        <el-button type="primary" @click="router.push(auth.roleHome)">返回首页</el-button>
        <el-button @click="switchAccount">切换账号</el-button>
      </div>
    </div>
  </section>
</template>
