import type { RouteRecordRaw } from 'vue-router'

export const consoleRoutes: RouteRecordRaw[] = [
  {
    path: '/console/login',
    name: 'console-login',
    component: () => import('@/console/views/LoginView.vue'),
    meta: { consolePublic: true, bare: true, title: '后台登录' }
  },
  {
    path: '/console/merchant/status',
    name: 'console-merchant-status',
    component: () => import('@/console/views/MerchantStatusView.vue'),
    meta: { consoleAuth: true, consoleRole: 'merchant', bare: true, title: '账号状态' }
  },
  {
    path: '/console',
    component: () => import('@/console/layouts/ConsoleLayout.vue'),
    meta: { consoleAuth: true, bare: true },
    children: [
      {
        path: '',
        redirect: '/console/login'
      },
      {
        path: 'coming-soon',
        name: 'console-coming-soon',
        component: () => import('@/console/views/ComingSoonView.vue'),
        meta: { consoleAuth: true, title: '功能规划中' }
      },
      {
        path: 'forbidden',
        name: 'console-forbidden',
        component: () => import('@/console/views/ForbiddenView.vue'),
        meta: { consoleAuth: true, title: '无权限' }
      },
      {
        path: 'merchant/dashboard',
        name: 'console-merchant-dashboard',
        component: () => import('@/console/views/merchant/DashboardView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:dashboard',
          title: '工作台',
          group: '工作台'
        }
      },
      {
        path: 'merchant/products',
        name: 'console-merchant-products',
        component: () => import('@/console/views/merchant/ProductListView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:product',
          title: '商品列表',
          group: '商品'
        }
      },
      {
        path: 'merchant/products/new',
        name: 'console-merchant-product-new',
        component: () => import('@/console/views/merchant/ProductEditView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:product',
          title: '发布商品',
          group: '商品'
        }
      },
      {
        path: 'merchant/products/:id/edit',
        name: 'console-merchant-product-edit',
        component: () => import('@/console/views/merchant/ProductEditView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:product',
          title: '编辑商品',
          group: '商品'
        }
      },
      {
        path: 'merchant/orders',
        name: 'console-merchant-orders',
        component: () => import('@/console/views/merchant/OrderListView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:order',
          title: '订单管理',
          group: '交易'
        }
      },
      {
        path: 'merchant/orders/:id',
        name: 'console-merchant-order-detail',
        component: () => import('@/console/views/merchant/OrderDetailView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:order',
          title: '订单详情',
          group: '交易'
        }
      },
      {
        path: 'merchant/aftersales',
        name: 'console-merchant-aftersales',
        component: () => import('@/console/views/merchant/AftersaleListView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:aftersale',
          title: '售后处理',
          group: '交易'
        }
      },
      {
        path: 'merchant/finance',
        name: 'console-merchant-finance',
        component: () => import('@/console/views/merchant/FinanceView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:finance',
          title: '结算中心',
          group: '财务与店铺'
        }
      },
      {
        path: 'merchant/shop',
        name: 'console-merchant-shop',
        component: () => import('@/console/views/merchant/ShopView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:shop',
          title: '店铺管理',
          group: '财务与店铺'
        }
      },
      {
        path: 'merchant/analytics',
        name: 'console-merchant-analytics',
        component: () => import('@/console/views/merchant/AnalyticsView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:analytics',
          title: '数据概览',
          group: '财务与店铺'
        }
      },
      {
        path: 'merchant/notifications',
        name: 'console-merchant-notifications',
        component: () => import('@/console/views/merchant/NotificationsView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'merchant',
          permission: 'merchant:message',
          title: '消息通知',
          group: '财务与店铺'
        }
      },
      {
        path: 'admin/dashboard',
        name: 'console-admin-dashboard',
        component: () => import('@/console/views/admin/DashboardView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'dashboard:read',
          title: '数据看板',
          group: '总览'
        }
      },
      {
        path: 'admin/merchants',
        name: 'console-admin-merchants',
        component: () => import('@/console/views/admin/MerchantListView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'merchant:read',
          title: '商家列表',
          group: '商家'
        }
      },
      {
        path: 'admin/merchants/review',
        name: 'console-admin-merchant-review',
        component: () => import('@/console/views/admin/MerchantReviewView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'merchant:review',
          title: '入驻审核',
          group: '商家'
        }
      },
      {
        path: 'admin/products',
        name: 'console-admin-products',
        component: () => import('@/console/views/admin/ProductListView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'product:read',
          title: '商品列表',
          group: '商品'
        }
      },
      {
        path: 'admin/products/review',
        name: 'console-admin-product-review',
        component: () => import('@/console/views/admin/ProductReviewView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'product:approve',
          title: '商品审核',
          group: '商品'
        }
      },
      {
        path: 'admin/categories',
        name: 'console-admin-categories',
        component: () => import('@/console/views/admin/CategoryView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'product:read',
          title: '分类管理',
          group: '商品'
        }
      },
      {
        path: 'admin/orders',
        name: 'console-admin-orders',
        component: () => import('@/console/views/admin/OrderListView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'order:read',
          title: '订单管理',
          group: '交易'
        }
      },
      {
        path: 'admin/aftersales',
        name: 'console-admin-aftersales',
        component: () => import('@/console/views/admin/AftersaleView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'refund:approve',
          title: '售后仲裁',
          group: '交易'
        }
      },
      {
        path: 'admin/origins',
        name: 'console-admin-origins',
        component: () => import('@/console/views/admin/OriginView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'aid:manage',
          title: '产地管理',
          group: '平台治理'
        }
      },
      {
        path: 'admin/users',
        name: 'console-admin-users',
        component: () => import('@/console/views/admin/UserListView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'user:read',
          title: '用户管理',
          group: '平台治理'
        }
      },
      {
        path: 'admin/announcements',
        name: 'console-admin-announcements',
        component: () => import('@/console/views/admin/AnnouncementView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'cms:manage',
          title: '公告管理',
          group: '平台治理'
        }
      },
      {
        path: 'admin/finance',
        name: 'console-admin-finance',
        component: () => import('@/console/views/admin/FinanceView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          permission: 'finance:read',
          title: '财务管理',
          group: '平台治理'
        }
      },
      {
        path: 'admin/settings',
        name: 'console-admin-settings',
        component: () => import('@/console/views/admin/SettingsView.vue'),
        meta: {
          consoleAuth: true,
          consoleRole: 'admin',
          anyPermissions: ['settings:manage', 'rbac:manage', 'audit:read'],
          title: '系统设置',
          group: '系统'
        }
      },
      {
        path: ':pathMatch(.*)*',
        name: 'console-not-found',
        component: () => import('@/console/views/NotFoundView.vue'),
        meta: { consoleAuth: true, title: '页面未找到' }
      }
    ]
  }
]
