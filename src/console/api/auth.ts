import { clone, getDb } from '@/console/mock/db'
import type { AdminSession, ConsoleRole, ConsoleSession, MerchantSession } from './types'
import { MockApiError, mockCall } from './mock'

export interface LoginPayload {
  role: ConsoleRole
  username: string
  password: string
}

const TOKEN_TTL = 12 * 60 * 60 * 1000

function isExpired(token: string): boolean {
  const stamp = Number.parseInt(token.split('-')[1] || '', 36)
  return !stamp || Date.now() - stamp > TOKEN_TTL
}

function makeToken(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

export const authApi = {
  async login(payload: LoginPayload): Promise<ConsoleSession> {
    return mockCall(() => {
      const db = getDb()
      const username = payload.username.trim()
      if (payload.role === 'merchant') {
        const merchant = db.merchants.find((item) => item.username === username)
        if (!merchant || merchant.password !== payload.password) {
          throw new MockApiError('BAD_CREDENTIALS', '商家账号或密码错误')
        }
        const session: MerchantSession = {
          token: makeToken('cm'),
          role: 'merchant',
          account: clone(merchant),
          permissions: ['merchant:*'],
          status: merchant.status
        }
        return session
      }
      const admin = db.admins.find((item) => item.username === username)
      if (!admin || admin.status !== 'active') {
        throw new MockApiError('BAD_CREDENTIALS', '管理员账号或密码错误')
      }
      // 演示密码对全部管理员账号统一为 Demo@123456
      if (payload.password !== 'Demo@123456') {
        throw new MockApiError('BAD_CREDENTIALS', '管理员账号或密码错误')
      }
      const session: AdminSession = {
        token: makeToken('ca'),
        role: 'admin',
        account: clone(admin),
        permissions: [...admin.permissions],
        isSuper: admin.roleCode === 'super_admin'
      }
      return session
    })
  },

  async me(session: ConsoleSession): Promise<ConsoleSession> {
    return mockCall(() => {
      if (isExpired(session.token)) {
        throw new MockApiError('UNAUTHENTICATED', '登录状态已过期，请重新登录')
      }
      const db = getDb()
      if (session.role === 'merchant') {
        const merchant = db.merchants.find((item) => item.id === session.account.id)
        if (!merchant) throw new MockApiError('UNAUTHENTICATED', '账号不存在')
        return {
          ...session,
          account: clone(merchant),
          status: merchant.status,
          permissions: ['merchant:*']
        }
      }
      const admin = db.admins.find((item) => item.id === session.account.id)
      if (!admin || admin.status !== 'active') {
        throw new MockApiError('UNAUTHENTICATED', '管理员账号不存在或已停用')
      }
      return {
        ...session,
        account: clone(admin),
        permissions: [...admin.permissions],
        isSuper: admin.roleCode === 'super_admin'
      }
    })
  },

  async logout(): Promise<void> {
    return mockCall(() => undefined)
  },

  demoAccounts(role: ConsoleRole) {
    const db = getDb()
    if (role === 'merchant') {
      return db.merchants
        .filter((item) =>
          ['merchant01', 'merchant_pending', 'merchant_rejected', 'merchant_frozen'].includes(
            item.username
          )
        )
        .map((item) => ({
          username: item.username,
          name: item.companyName,
          status: item.status
        }))
    }
    return db.admins.map((item) => ({
      username: item.username,
      name: item.name,
      status: item.status
    }))
  }
}
