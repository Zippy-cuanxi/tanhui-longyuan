import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { consoleRoutes } from '@/console/router'
import { consoleGuard } from '@/console/router/guard'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { title: '首页' }
    },
    {
      path: '/products',
      name: 'products',
      component: () => import('@/views/CatalogView.vue'),
      meta: { title: '全部商品' }
    },
    {
      path: '/products/:id',
      name: 'product-detail',
      component: () => import('@/views/ProductDetailView.vue'),
      meta: { title: '商品详情' }
    },
    {
      path: '/cart',
      name: 'cart',
      component: () => import('@/views/CartView.vue'),
      meta: { title: '购物车', requiresAuth: true }
    },
    {
      path: '/checkout',
      name: 'checkout',
      component: () => import('@/views/CheckoutView.vue'),
      meta: { title: '确认订单', requiresAuth: true }
    },
    {
      path: '/pay/:orderId',
      name: 'payment',
      component: () => import('@/views/PaymentView.vue'),
      meta: { title: '订单支付', requiresAuth: true }
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: '登录', guestOnly: true, bare: true }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { title: '注册', guestOnly: true, bare: true }
    },
    {
      path: '/account',
      component: () => import('@/views/account/AccountView.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'account',
          component: () => import('@/views/account/AccountHomeView.vue'),
          meta: { title: '个人中心' }
        },
        {
          path: 'orders',
          name: 'orders',
          component: () => import('@/views/account/OrdersView.vue'),
          meta: { title: '我的订单' }
        },
        {
          path: 'orders/:id',
          name: 'order-detail',
          component: () => import('@/views/account/OrderDetailView.vue'),
          meta: { title: '订单详情' }
        },
        {
          path: 'orders/:id/logistics',
          name: 'order-logistics',
          component: () => import('@/views/account/LogisticsView.vue'),
          meta: { title: '物流详情' }
        },
        {
          path: 'orders/:id/refund',
          name: 'order-refund',
          component: () => import('@/views/account/RefundView.vue'),
          meta: { title: '申请退款' }
        },
        {
          path: 'addresses',
          name: 'addresses',
          component: () => import('@/views/account/AddressesView.vue'),
          meta: { title: '收货地址' }
        },
        {
          path: 'points',
          name: 'points',
          component: () => import('@/views/account/PointsView.vue'),
          meta: { title: '绿色积分' }
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/account/ProfileView.vue'),
          meta: { title: '个人资料' }
        },
        {
          path: 'notifications',
          name: 'notifications',
          component: () => import('@/views/account/NotificationsView.vue'),
          meta: { title: '消息通知' }
        }
      ]
    },
    {
      path: '/origin',
      name: 'origin',
      component: () => import('@/views/OriginView.vue'),
      meta: { title: '甘肃产地' }
    },
    {
      path: '/aid',
      name: 'aid',
      component: () => import('@/views/AidView.vue'),
      meta: { title: '助农项目' }
    },
    {
      path: '/aid/:id',
      name: 'aid-detail',
      component: () => import('@/views/AidDetailView.vue'),
      meta: { title: '助农项目详情' }
    },
    {
      path: '/join',
      name: 'merchant-join',
      component: () => import('@/views/MerchantJoinView.vue'),
      meta: { title: '商家入驻' }
    },
    {
      path: '/green',
      name: 'green',
      component: () => import('@/views/GreenView.vue'),
      meta: { title: '绿色消费专区' }
    },
    {
      path: '/coupons',
      name: 'coupon-store',
      component: () => import('@/views/CouponStoreView.vue'),
      meta: { title: '优惠券商店' }
    },
    {
      path: '/notices',
      name: 'notices',
      component: () => import('@/views/NoticesView.vue'),
      meta: { title: '平台公告' }
    },
    {
      path: '/notices/:id',
      name: 'notice-detail',
      component: () => import('@/views/NoticeDetailView.vue'),
      meta: { title: '公告详情' }
    },
    {
      path: '/help',
      name: 'help',
      component: () => import('@/views/HelpView.vue'),
      meta: { title: '帮助中心' }
    },
    ...consoleRoutes,
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { title: '页面未找到' }
    }
  ],
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth', top: 90 }
    return { top: 0 }
  }
})

router.beforeEach(async (to) => {
  const consoleResult = await consoleGuard(to)
  if (consoleResult !== undefined) return consoleResult

  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && auth.isAuthenticated) {
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : '/'
    return redirect
  }
  return true
})

router.afterEach((to) => {
  const isConsole = to.path.startsWith('/console')
  document.body.classList.toggle('console-mode', isConsole)
  const title = typeof to.meta.title === 'string' ? to.meta.title : ''
  document.title = title
    ? `${title} · ${isConsole ? '碳惠陇原后台' : '碳惠陇原'}`
    : '碳惠陇原 · 来自陇原的自然好物'
})

export default router
