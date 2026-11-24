<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'
</script>

<template>
  <main class="page-main not-found-page">
    <div class="page-container narrow-container not-found-inner">
      <span class="not-found-code">404</span>
      <span class="eyebrow">PAGE NOT FOUND</span>
      <h1>这片陇原田地还没有内容</h1>
      <p>你访问的页面不存在或已移动。可以返回首页，或去看看产地好物。</p>
      <div class="not-found-actions">
        <RouterLink to="/" class="primary-button">返回首页</RouterLink>
        <RouterLink to="/products" class="outline-button">全部商品</RouterLink>
      </div>
      <div class="not-found-links">
        <RouterLink to="/origin"><AppIcon name="map" :size="16" />甘肃产地</RouterLink>
        <RouterLink to="/aid"><AppIcon name="heart" :size="16" />助农项目</RouterLink>
        <RouterLink to="/help"><AppIcon name="info" :size="16" />帮助中心</RouterLink>
      </div>
    </div>
  </main>
</template>
