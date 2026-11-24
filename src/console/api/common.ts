import { getDb } from '@/console/mock/db'
import { mockCall } from './mock'
import type { ConsoleSession } from './types'

export interface NoticeFeedItem {
  id: string
  title: string
  content: string
  createdAt: string
  read: boolean
}

export const commonApi = {
  async noticeFeed(session: ConsoleSession): Promise<{
    items: NoticeFeedItem[]
    unread: number
  }> {
    return mockCall(() => {
      const db = getDb()
      if (session.role === 'merchant') {
        const items = db.notifications.slice(0, 6).map((item) => ({
          id: item.id,
          title: item.title,
          content: item.content,
          createdAt: item.createdAt,
          read: item.read
        }))
        return {
          items,
          unread: db.notifications.filter((item) => !item.read).length
        }
      }
      const items = db.logs.slice(0, 6).map((item) => ({
        id: item.id,
        title: `${item.module} · ${item.action}`,
        content: item.detail,
        createdAt: item.createdAt,
        read: true
      }))
      return { items, unread: 0 }
    })
  }
}
