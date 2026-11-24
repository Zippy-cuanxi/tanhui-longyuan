<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useConsoleAuth } from '@/console/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useConsoleAuth()
const title = computed(() => String(route.query.title || '功能规划中'))
const moduleName = computed(() => String(route.query.module || ''))

function back(): void {
  router.push(auth.roleHome)
}
</script>

<template>
  <section class="console-coming">
    <div class="console-coming-card">
      <img :src="assetUrl('/console-assets/images/coming-soon.webp')" alt="功能建设中" />
      <h1>{{ title }}</h1>
      <p>
        该模块已列入{{
          moduleName === 'admin' ? '管理端' : moduleName === 'merchant' ? '商家端' : '平台'
        }}二期建设计划，当前版本暂不开放。
        <br />
        一期已开放商品、订单、售后、结算、店铺、商家审核、商品审核、财务与系统设置等核心能力。
      </p>
      <div class="console-inline-actions" style="margin-top: 12px">
        <el-button type="primary" @click="back"
          >返回{{ auth.isAdmin ? '数据看板' : '工作台' }}</el-button
        >
        <el-button plain @click="router.back()">返回上一页</el-button>
      </div>
    </div>
  </section>
</template>
