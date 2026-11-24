import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    consoleAuth?: boolean
    consolePublic?: boolean
    consoleRole?: 'merchant' | 'admin'
    permission?: string
    anyPermissions?: string[]
    title?: string
    group?: string
    bare?: boolean
    requiresAuth?: boolean
    guestOnly?: boolean
  }
}
