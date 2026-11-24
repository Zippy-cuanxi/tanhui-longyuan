<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { useRouter } from 'vue-router'
import { useConsoleAuth } from '@/console/stores/auth'

const router = useRouter()
const auth = useConsoleAuth()
</script>

<template>
  <section class="console-coming">
    <div class="console-coming-card">
      <img :src="assetUrl('/console-assets/images/error-404.webp')" alt="页面不存在" />
      <h1>页面不存在</h1>
      <p>你访问的后台页面不存在，可能已被移除或链接有误。</p>
      <div class="console-inline-actions" style="margin-top: 12px">
        <el-button type="primary" @click="router.push(auth.roleHome)">返回首页</el-button>
        <el-button plain @click="router.back()">返回上一页</el-button>
      </div>
    </div>
  </section>
</template>
