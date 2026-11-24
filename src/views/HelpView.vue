<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

const sections = [
  {
    title: '购物与下单',
    icon: 'cart',
    items: [
      {
        q: '如何加入购物车？',
        a: '在商品列表或详情页选择规格后点击“加入购物车”。登录后才能加购与下单。'
      },
      {
        q: '订单金额如何计算？',
        a: '商品价格、运费、积分抵扣与应付金额均由服务端计算。结算页会先调用订单预览接口，提交订单时会再次校验价格与库存。'
      },
      {
        q: '价格变化了怎么办？',
        a: '如果下单时价格与预览不一致，服务端会返回 PRICE_CHANGED。请返回结算页重新计价并确认。'
      }
    ]
  },
  {
    title: '支付',
    icon: 'card',
    items: [
      {
        q: '支持哪些支付方式？',
        a: '当前为 Mock 沙箱支付，未接入真实支付渠道。支付页的“沙箱支付（演示）”会由后端模拟签名回调并更新订单状态。'
      },
      {
        q: '支付成功以什么为准？',
        a: '以服务端支付单与订单状态为准，不以客户端提示为准。支付成功后可在“我的订单”查看状态。'
      }
    ]
  },
  {
    title: '配送与物流',
    icon: 'truck',
    items: [
      { q: '多久发货？', a: '商家在订单支付后安排发货；当前版本未实现自动确认收货时限。' },
      {
        q: '物流轨迹是真实的吗？',
        a: '当前物流轨迹为 Mock 演示数据，发货单与运单号可在订单物流页查看。'
      }
    ]
  },
  {
    title: '售后与退款',
    icon: 'refresh',
    items: [
      {
        q: '如何申请退款？',
        a: '在“我的订单”中选择已支付、已发货或已完成的订单，进入订单详情后点击“申请退款”。退款按店铺子单提交。'
      },
      {
        q: '退款多久到账？',
        a: '当前为 Mock 原路退回，仅做状态流转与台账记录，未发生真实资金交易。'
      },
      { q: '部分退款如何展示？', a: '退款金额与状态以退款单为准；父订单状态可能显示为部分退款。' }
    ]
  },
  {
    title: '绿色积分',
    icon: 'leaf',
    items: [
      {
        q: '绿色积分是什么？',
        a: '绿色积分是平台内部激励，不等同于碳信用或现金，不能兑换现金。'
      },
      {
        q: '积分如何获取与抵扣？',
        a: '积分规则由平台配置。当前演示环境使用仿真规则，具体比例、上限与有效期以平台配置为准。'
      },
      {
        q: '兑换权益是真实的吗？',
        a: '当前兑换权益为 Mock 演示，返回的凭证码仅用于展示，不代表真实权益。'
      }
    ]
  }
]
</script>

<template>
  <main class="page-main help-page">
    <div class="page-container narrow-container">
      <section class="page-intro">
        <span class="eyebrow">HELP CENTER</span>
        <h1>帮助中心</h1>
        <p>关于下单、支付、配送、售后与绿色积分的常见问题。</p>
      </section>

      <div class="help-grid">
        <aside class="help-nav">
          <a v-for="(section, index) in sections" :key="section.title" :href="`#help-${index}`">
            <AppIcon :name="section.icon" :size="17" />{{ section.title }}
          </a>
          <RouterLink to="/account/orders"
            ><AppIcon name="package" :size="17" />我的订单</RouterLink
          >
          <RouterLink to="/account/points"><AppIcon name="leaf" :size="17" />绿色积分</RouterLink>
        </aside>

        <div class="help-content">
          <section
            v-for="(section, index) in sections"
            :id="`help-${index}`"
            :key="section.title"
            class="help-section"
          >
            <header>
              <span><AppIcon :name="section.icon" :size="20" /></span>
              <h2>{{ section.title }}</h2>
            </header>
            <details v-for="item in section.items" :key="item.q" class="help-item">
              <summary>{{ item.q }}</summary>
              <p>{{ item.a }}</p>
            </details>
          </section>

          <section class="help-contact">
            <AppIcon name="info" :size="20" />
            <div>
              <h3>还需要帮助？</h3>
              <p>
                当前版本未提供在线客服与电话入口。请关注平台公告，或登录后在消息通知中查看平台通知。
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  </main>
</template>
