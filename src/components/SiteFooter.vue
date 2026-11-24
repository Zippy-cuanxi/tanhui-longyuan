<script setup lang="ts">
import AppIcon from './AppIcon.vue'
</script>

<template>
  <footer class="site-footer">
    <div class="footer-main">
      <div class="footer-brand">
        <img src="/assets/brand/logo.png" alt="碳惠陇原" />
        <p>绿色生态 · 品质优选 · 助力乡村振兴</p>
      </div>
      <div class="footer-links">
        <div>
          <h3>逛陇原</h3>
          <RouterLink to="/products">全部商品</RouterLink>
          <RouterLink to="/origin">甘肃产地</RouterLink>
          <RouterLink to="/green">绿色消费专区</RouterLink>
        </div>
        <div>
          <h3>了解我们</h3>
          <RouterLink to="/brand">品牌故事</RouterLink>
          <RouterLink to="/aid">助农项目</RouterLink>
          <RouterLink to="/notices">平台公告</RouterLink>
        </div>
        <div>
          <h3>服务与帮助</h3>
          <RouterLink to="/help">帮助中心</RouterLink>
          <RouterLink to="/account/orders">我的订单</RouterLink>
          <RouterLink to="/account/addresses">收货地址</RouterLink>
        </div>
      </div>
      <div class="footer-badges">
        <div class="footer-badge">
          <span><AppIcon name="leaf" :size="20" /></span>
          <p><strong>绿色认证</strong><small>品质保障</small></p>
        </div>
        <div class="footer-badge">
          <span><AppIcon name="sparkle" :size="20" /></span>
          <p><strong>碳积分激励</strong><small>绿色消费</small></p>
        </div>
        <div class="footer-badge">
          <span><AppIcon name="heart" :size="20" /></span>
          <p><strong>助农公益</strong><small>共建美好</small></p>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <span>© 2026 碳惠陇原 · 甘肃特色农产品绿色电商平台</span>
      <span>演示环境：支付为沙箱、物流轨迹为仿真数据；商品与助农项目均为演示内容。</span>
    </div>
  </footer>
</template>
