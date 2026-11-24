import { canAny, hasPermission } from './permissions'

export interface ConsoleMenuItem {
  label: string
  path: string
  icon: string
  permission?: string
  anyPermissions?: string[]
  query?: Record<string, string>
  activePrefix?: string
  comingSoon?: boolean
  module?: string
}

export interface ConsoleMenuGroup {
  title: string
  items: ConsoleMenuItem[]
}

export const MERCHANT_MENU: ConsoleMenuGroup[] = [
  {
    title: '工作台',
    items: [
      {
        label: '工作台',
        path: '/console/merchant/dashboard',
        icon: 'workbench',
        permission: 'merchant:dashboard'
      }
    ]
  },
  {
    title: '商品',
    items: [
      {
        label: '商品列表',
        path: '/console/merchant/products',
        icon: 'goods',
        permission: 'merchant:product',
        activePrefix: '/console/merchant/products'
      },
      {
        label: '发布商品',
        path: '/console/merchant/products/new',
        icon: 'audit',
        permission: 'merchant:product'
      }
    ]
  },
  {
    title: '交易',
    items: [
      {
        label: '订单管理',
        path: '/console/merchant/orders',
        icon: 'orders',
        permission: 'merchant:order',
        activePrefix: '/console/merchant/orders'
      },
      {
        label: '售后处理',
        path: '/console/merchant/aftersales',
        icon: 'aftersale',
        permission: 'merchant:aftersale'
      }
    ]
  },
  {
    title: '财务与店铺',
    items: [
      {
        label: '结算中心',
        path: '/console/merchant/finance',
        icon: 'settlement',
        permission: 'merchant:finance'
      },
      {
        label: '店铺管理',
        path: '/console/merchant/shop',
        icon: 'shop',
        permission: 'merchant:shop'
      },
      {
        label: '数据概览',
        path: '/console/merchant/analytics',
        icon: 'data',
        permission: 'merchant:analytics'
      },
      {
        label: '消息通知',
        path: '/console/merchant/notifications',
        icon: 'bell',
        permission: 'merchant:message'
      }
    ]
  },
  {
    title: '二期功能',
    items: [
      {
        label: '商家子账号',
        path: '/console/coming-soon',
        icon: 'user',
        query: { title: '商家子账号', module: 'merchant' },
        comingSoon: true,
        permission: 'merchant:dashboard'
      },
      {
        label: '绿色积分',
        path: '/console/coming-soon',
        icon: 'points',
        query: { title: '绿色积分规则与流水', module: 'merchant' },
        comingSoon: true,
        permission: 'merchant:dashboard'
      },
      {
        label: '评价管理',
        path: '/console/coming-soon',
        icon: 'review',
        query: { title: '评价管理', module: 'merchant' },
        comingSoon: true,
        permission: 'merchant:dashboard'
      },
      {
        label: '批量导入发货',
        path: '/console/coming-soon',
        icon: 'export',
        query: { title: '批量导入发货', module: 'merchant' },
        comingSoon: true,
        permission: 'merchant:dashboard'
      },
      {
        label: '帮助中心',
        path: '/console/coming-soon',
        icon: 'help',
        query: { title: '帮助中心', module: 'merchant' },
        comingSoon: true,
        permission: 'merchant:dashboard'
      }
    ]
  }
]

export const ADMIN_MENU: ConsoleMenuGroup[] = [
  {
    title: '总览',
    items: [
      {
        label: '数据看板',
        path: '/console/admin/dashboard',
        icon: 'data',
        permission: 'dashboard:read'
      }
    ]
  },
  {
    title: '商家',
    items: [
      {
        label: '商家列表',
        path: '/console/admin/merchants',
        icon: 'merchant',
        permission: 'merchant:read',
        activePrefix: '/console/admin/merchants'
      },
      {
        label: '入驻审核',
        path: '/console/admin/merchants/review',
        icon: 'audit',
        permission: 'merchant:review'
      }
    ]
  },
  {
    title: '商品',
    items: [
      {
        label: '商品列表',
        path: '/console/admin/products',
        icon: 'goods',
        permission: 'product:read',
        activePrefix: '/console/admin/products'
      },
      {
        label: '商品审核',
        path: '/console/admin/products/review',
        icon: 'audit',
        permission: 'product:approve'
      },
      {
        label: '分类管理',
        path: '/console/admin/categories',
        icon: 'content',
        permission: 'product:read'
      }
    ]
  },
  {
    title: '交易',
    items: [
      {
        label: '订单管理',
        path: '/console/admin/orders',
        icon: 'orders',
        permission: 'order:read'
      },
      {
        label: '售后仲裁',
        path: '/console/admin/aftersales',
        icon: 'aftersale',
        permission: 'refund:approve'
      }
    ]
  },
  {
    title: '平台治理',
    items: [
      {
        label: '产地管理',
        path: '/console/admin/origins',
        icon: 'origin',
        permission: 'aid:manage'
      },
      {
        label: '用户管理',
        path: '/console/admin/users',
        icon: 'user',
        permission: 'user:read'
      },
      {
        label: '公告管理',
        path: '/console/admin/announcements',
        icon: 'content',
        permission: 'cms:manage'
      },
      {
        label: '财务管理',
        path: '/console/admin/finance',
        icon: 'finance',
        permission: 'finance:read'
      }
    ]
  },
  {
    title: '系统',
    items: [
      {
        label: '系统设置',
        path: '/console/admin/settings',
        icon: 'system',
        anyPermissions: ['settings:manage', 'rbac:manage']
      },
      {
        label: '操作日志',
        path: '/console/admin/settings',
        query: { tab: 'logs' },
        icon: 'log',
        permission: 'audit:read'
      }
    ]
  },
  {
    title: '二期功能',
    items: [
      {
        label: '绿色积分',
        path: '/console/coming-soon',
        icon: 'points',
        query: { title: '绿色积分规则与流水', module: 'admin' },
        comingSoon: true,
        permission: 'points:manage'
      },
      {
        label: '助农标签审核',
        path: '/console/coming-soon',
        icon: 'charity',
        query: { title: '助农标签审核', module: 'admin' },
        comingSoon: true,
        permission: 'aid:manage'
      },
      {
        label: '助农公益',
        path: '/console/coming-soon',
        icon: 'charity',
        query: { title: '助农公益', module: 'admin' },
        comingSoon: true,
        permission: 'aid:manage'
      },
      {
        label: '绿色消费专区',
        path: '/console/coming-soon',
        icon: 'points',
        query: { title: '绿色消费专区', module: 'admin' },
        comingSoon: true,
        permission: 'green:review'
      },
      {
        label: '评价管理',
        path: '/console/coming-soon',
        icon: 'review',
        query: { title: '评价管理', module: 'admin' },
        comingSoon: true,
        permission: 'product:read'
      },
      {
        label: 'Banner 管理',
        path: '/console/coming-soon',
        icon: 'content',
        query: { title: 'Banner 管理', module: 'admin' },
        comingSoon: true,
        permission: 'cms:manage'
      },
      {
        label: '帮助中心',
        path: '/console/coming-soon',
        icon: 'help',
        query: { title: '帮助中心', module: 'admin' },
        comingSoon: true
      }
    ]
  }
]

export function menuForRole(role: 'merchant' | 'admin', permissions: string[]): ConsoleMenuGroup[] {
  const source = role === 'admin' ? ADMIN_MENU : MERCHANT_MENU
  return source
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => {
        if (item.anyPermissions?.length) return canAny(permissions, item.anyPermissions)
        return hasPermission(permissions, item.permission)
      })
    }))
    .filter((group) => group.items.length > 0)
}
