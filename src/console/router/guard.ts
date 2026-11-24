import type { RouteLocationNormalized, RouteLocationRaw } from 'vue-router'
import { useConsoleAuth } from '@/console/stores/auth'
import { canAny } from '@/console/constants/permissions'

const LOGIN = { name: 'console-login' }
const FORBIDDEN = { name: 'console-forbidden' }
const MERCHANT_STATUS = { name: 'console-merchant-status' }
const MERCHANT_HOME = { name: 'console-merchant-dashboard' }

export async function consoleGuard(
  to: RouteLocationNormalized
): Promise<boolean | RouteLocationRaw | undefined> {
  if (!to.path.startsWith('/console')) return undefined
  const auth = useConsoleAuth()
  await auth.ensureFresh()

  if (to.meta.consolePublic) {
    return auth.isAuthenticated ? auth.roleHome : true
  }

  if (!auth.isAuthenticated) {
    return { ...LOGIN, query: { redirect: to.fullPath } }
  }

  if (to.name === 'console-merchant-status') {
    if (auth.role !== 'merchant') return FORBIDDEN
    return auth.merchantStatus === 'normal' ? MERCHANT_HOME : true
  }

  if (auth.isMerchant && auth.merchantStatus !== 'normal') {
    return MERCHANT_STATUS
  }

  if (to.meta.consoleRole && to.meta.consoleRole !== auth.role) {
    return FORBIDDEN
  }

  if (to.meta.permission && !auth.can(to.meta.permission)) {
    return FORBIDDEN
  }

  if (to.meta.anyPermissions?.length && !canAny(auth.permissions, to.meta.anyPermissions)) {
    return FORBIDDEN
  }

  return true
}
