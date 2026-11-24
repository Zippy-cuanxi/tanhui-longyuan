import type { AdminRoleCode, MerchantPermission, PermissionCode } from '@/console/api/types'

export const ADMIN_ROLE_PERMISSIONS: Record<AdminRoleCode, string[]> = {
  super_admin: ['*'],
  ops_admin: [
    'dashboard:read',
    'user:read',
    'user:ban',
    'merchant:read',
    'store:read',
    'order:read',
    'cms:manage',
    'aid:manage',
    'audit:read'
  ],
  product_auditor: [
    'dashboard:read',
    'product:read',
    'product:approve',
    'product:remove',
    'merchant:read',
    'store:read',
    'green:review'
  ],
  finance_admin: [
    'dashboard:read',
    'finance:read',
    'finance:manage',
    'order:read',
    'merchant:read',
    'refund:approve'
  ],
  cs_admin: ['dashboard:read', 'order:read', 'refund:approve', 'user:read', 'product:read']
}

export const ADMIN_ROLE_NAMES: Record<AdminRoleCode, string> = {
  super_admin: '超级管理员',
  ops_admin: '运营管理员',
  product_auditor: '商品审核员',
  finance_admin: '财务管理员',
  cs_admin: '客服管理员'
}

export const ALL_ADMIN_PERMISSIONS: PermissionCode[] = [
  'dashboard:read',
  'user:read',
  'user:ban',
  'merchant:read',
  'merchant:review',
  'store:read',
  'store:manage',
  'product:read',
  'product:approve',
  'product:remove',
  'order:read',
  'refund:approve',
  'finance:read',
  'finance:manage',
  'points:manage',
  'cms:manage',
  'aid:manage',
  'green:review',
  'audit:read',
  'rbac:manage',
  'settings:manage'
]

export const MERCHANT_PERMISSIONS: MerchantPermission[] = [
  'merchant:dashboard',
  'merchant:product',
  'merchant:order',
  'merchant:aftersale',
  'merchant:finance',
  'merchant:shop',
  'merchant:analytics',
  'merchant:message'
]

export const PERMISSION_LABELS: Record<string, string> = {
  'dashboard:read': '查看数据看板',
  'user:read': '查看用户',
  'user:ban': '封禁/解封用户',
  'merchant:read': '查看商家',
  'merchant:review': '商家入驻审核/冻结',
  'store:read': '查看店铺',
  'store:manage': '店铺状态管理',
  'product:read': '查看商品',
  'product:approve': '商品审核',
  'product:remove': '平台下架商品',
  'order:read': '查看订单',
  'refund:approve': '退款/售后裁决',
  'finance:read': '查看财务',
  'finance:manage': '财务结算/提现审核',
  'points:manage': '绿色积分管理',
  'cms:manage': '内容运营',
  'aid:manage': '助农/产地管理',
  'green:review': '绿色资料审核',
  'audit:read': '查看审计日志',
  'rbac:manage': '角色权限管理',
  'settings:manage': '系统设置'
}

export function hasPermission(permissions: string[], code?: string | null): boolean {
  if (!code) return true
  if (permissions.includes('*') || permissions.includes(code)) return true
  return permissions.some((item) => {
    if (!item.endsWith(':*')) return false
    return code.startsWith(item.slice(0, -1))
  })
}

export function canAny(permissions: string[], codes: Array<string | undefined>): boolean {
  return codes.some((code) => hasPermission(permissions, code))
}
