/* 管理端/商家端独立类型。页面只依赖此文件与 src/console/api 下的 api 模块。 */

export type ConsoleRole = 'merchant' | 'admin'
export type MerchantStatus = 'normal' | 'pending' | 'rejected' | 'frozen'
export type AdminRoleCode =
  'super_admin' | 'ops_admin' | 'product_auditor' | 'finance_admin' | 'cs_admin'

export type PermissionCode =
  | 'user:read'
  | 'user:ban'
  | 'merchant:read'
  | 'merchant:review'
  | 'store:read'
  | 'store:manage'
  | 'product:read'
  | 'product:approve'
  | 'product:remove'
  | 'order:read'
  | 'refund:approve'
  | 'finance:read'
  | 'finance:manage'
  | 'points:manage'
  | 'cms:manage'
  | 'aid:manage'
  | 'green:review'
  | 'audit:read'
  | 'rbac:manage'
  | 'settings:manage'
  | 'dashboard:read'

export type MerchantPermission =
  | 'merchant:dashboard'
  | 'merchant:product'
  | 'merchant:order'
  | 'merchant:aftersale'
  | 'merchant:finance'
  | 'merchant:shop'
  | 'merchant:analytics'
  | 'merchant:message'

export interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface PageResult<T> {
  items: T[]
  pagination: Pagination
}

export interface ListQuery {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  date_from?: string
  date_to?: string
  [key: string]: string | number | undefined
}

export interface MerchantAccount {
  id: string
  username: string
  password: string
  companyName: string
  storeName: string
  ownerName: string
  phone: string
  email: string
  region: string
  licenseNo: string
  licenseImage: string
  status: MerchantStatus
  rejectReason?: string
  frozenReason?: string
  createdAt: string
  reviewedAt?: string
  avatar: string
}

export interface Store {
  id: string
  merchantId: string
  name: string
  logo: string
  region: string
  description: string
  status: 'active' | 'suspended' | 'closed'
  rating: string
  shippingTemplates: ShippingTemplate[]
  qualifications: Qualification[]
}

export interface ShippingTemplate {
  id: string
  name: string
  freeThreshold: string
  baseFee: string
  regions: string
  enabled: boolean
}

export interface Qualification {
  id: string
  name: string
  image: string
  status: 'approved' | 'pending' | 'rejected'
  reason?: string
}

export interface Sku {
  id: string
  spec: string
  price: string
  stock: number
  code: string
}

export interface ProductChange {
  field: string
  label: string
  oldValue: string
  newValue: string
}

export interface AuditRecord {
  id: string
  action: 'submit' | 'approve' | 'reject' | 'remove' | 'relist' | 'delist'
  operator: string
  reason?: string
  createdAt: string
}

export type ProductStatus = 'draft' | 'pending_review' | 'approved' | 'rejected' | 'removed'

export interface Product {
  id: string
  merchantId: string
  storeId: string
  storeName: string
  title: string
  subtitle: string
  categoryId: string
  categoryName: string
  description: string
  price: string
  minPrice: string
  stock: number
  sales: number
  status: ProductStatus
  listed: boolean
  cover: string
  images: string[]
  skus: Sku[]
  shippingTemplateId: string
  greenProfile: {
    origin: string
    plantingMode: string
    description: string
    status: 'draft' | 'pending_review' | 'approved' | 'rejected'
  }
  aidProjectId?: string
  aidProjectName?: string
  auditReason?: string
  auditedAt?: string
  auditRecords: AuditRecord[]
  change?: ProductChange[]
  /** 审核通过后消费者端同步结果（真实后端返回，演示数据为空） */
  syncStatus?: 'success' | 'failed'
  syncAttempts?: number
  syncError?: string
  syncMessage?: string
  createdAt: string
  updatedAt: string
}

export type OrderStatus =
  | 'pending_payment'
  | 'paid'
  | 'shipped'
  | 'completed'
  | 'cancelled'
  | 'refunding'
  | 'refunded'
  | 'partially_refunded'

export interface OrderItem {
  id: string
  productId: string
  title: string
  spec: string
  price: string
  quantity: number
  image: string
}

export interface Shipment {
  carrier: string
  trackingNo: string
  shippedAt: string
  status: string
  tracks: { time: string; text: string }[]
}

export interface Order {
  id: string
  orderNo: string
  merchantId: string
  storeId: string
  storeName: string
  buyerName: string
  buyerPhone: string
  buyerEmail: string
  address: string
  items: OrderItem[]
  itemsTotal: string
  shippingFee: string
  payAmount: string
  refundAmount: string
  status: OrderStatus
  createdAt: string
  paidAt?: string
  shipDeadline?: string
  shippedAt?: string
  completedAt?: string
  shipment?: Shipment
  remark?: string
  statusLogs: { time: string; action: string; status: string; operator: string; note?: string }[]
}

export type AftersaleStatus = 'requested' | 'arbitrating' | 'refunded' | 'rejected'

export interface Aftersale {
  id: string
  refundNo: string
  orderId: string
  orderNo: string
  merchantId: string
  storeId: string
  storeName: string
  buyerName: string
  buyerPhone: string
  amount: string
  reason: string
  evidence: string[]
  status: AftersaleStatus
  merchantReason?: string
  adminReason?: string
  createdAt: string
  handledAt?: string
  orderPayAmount: string
  orderRefundAmount: string
}

export type SettlementStatus = 'pending' | 'confirmed' | 'paid'

export interface Settlement {
  id: string
  settlementNo: string
  merchantId: string
  storeId: string
  storeName: string
  periodStart: string
  periodEnd: string
  orderCount: number
  ordersTotal: string
  commission: string
  payable: string
  refundDeduct: string
  status: SettlementStatus
  createdAt: string
  confirmedAt?: string
  paidAt?: string
}

export interface SettlementBill {
  id: string
  orderNo: string
  storeOrderNo: string
  paidAt: string
  amount: string
  commission: string
  payable: string
}

export type WithdrawalStatus = 'pending' | 'approved' | 'rejected'

export interface Withdrawal {
  id: string
  merchantId: string
  amount: string
  accountName: string
  bankName: string
  accountNo: string
  status: WithdrawalStatus
  createdAt: string
  handledAt?: string
  reason?: string
}

export interface SettlementAccount {
  merchantId: string
  accountName: string
  bankName: string
  accountNo: string
  branch: string
  verified: boolean
}

export interface MerchantBalance {
  total: string
  available: string
  frozen: string
  withdrawn: string
  pendingSettlement: string
}

export interface Member {
  id: string
  nickname: string
  email: string
  phone: string
  status: 'active' | 'banned'
  roles: string[]
  orderCount: number
  totalPaid: string
  points: number
  createdAt: string
  lastLoginAt: string
  banReason?: string
}

export interface Category {
  id: string
  name: string
  parentId?: string
  productCount: number
  sort: number
  enabled: boolean
}

export interface OriginMetric {
  sales: number
  aid: number
  carbon: number
}

export interface Origin {
  id: string
  adcode: string
  name: string
  location: string
  productName: string
  tagline: string
  productCount: number
  totals: OriginMetric
  monthly: { sales: number[]; aid: number[]; carbon: number[] }
}

export type AnnouncementStatus = 'draft' | 'published' | 'offline'

export interface Announcement {
  id: string
  title: string
  content: string
  status: AnnouncementStatus
  author: string
  createdAt: string
  publishedAt?: string
}

export interface AdminAccount {
  id: string
  username: string
  /** mock 环境用于重置密码，真实接口不会返回 */
  password?: string
  name: string
  roleCode: AdminRoleCode
  roleName: string
  permissions: string[]
  status: 'active' | 'disabled'
  avatar: string
  lastLoginAt: string
  createdAt: string
}

export interface AdminRole {
  code: AdminRoleCode
  name: string
  description: string
  permissions: string[]
  builtIn: boolean
}

export interface OperationLog {
  id: string
  actor: string
  actorName: string
  action: string
  module: string
  target: string
  detail: string
  ip: string
  risk: 'high' | 'normal'
  createdAt: string
}

export interface Notification {
  id: string
  type: 'order' | 'system' | 'notice' | 'aftersale' | 'finance'
  title: string
  content: string
  read: boolean
  createdAt: string
  source?: string
}

export interface AdminSession {
  token: string
  role: 'admin'
  account: AdminAccount
  permissions: string[]
  isSuper: boolean
}

export interface MerchantSession {
  token: string
  role: 'merchant'
  account: MerchantAccount
  permissions: string[]
  status: MerchantStatus
}

export type ConsoleSession = AdminSession | MerchantSession

export interface AdminDashboard {
  kpis: {
    gmvPay: string
    paidOrders: number
    aov: string
    payRate: number
    refundRate: number
    newUsers: number
  }
  todos: {
    productAudits: number
    merchantReviews: number
    refunds: number
    greenReviews: number
    settlementPending: number
    stockAlerts: number
  }
  trend: { date: string; gmv: string; orders: number }[]
  orderStatus: { status: string; count: number }[]
  categoryTop: { name: string; amount: string; quantity: number }[]
  storeTop: { name: string; amount: string; orders: number }[]
  originTop: { name: string; location: string; sales: number; aid: number }[]
  aid: { projects: number; raised: string; goal: string }
  green: { greenProducts: number; listedProducts: number; ratio: number }
  points: { balanceTotal: number; earned: number; spent: number }
  updatedAt: string
}

export interface MerchantDashboard {
  kpis: {
    todayOrders: number
    todaySales: string
    pendingShip: number
    pendingAftersale: number
    availableBalance: string
    productOnline: number
  }
  trend: { date: string; orders: number; sales: string }[]
  topProducts: { title: string; sales: number; amount: string }[]
  recentOrders: Order[]
  updatedAt: string
}

export interface AnalyticsData {
  range: string
  kpis: { label: string; value: string; hint: string }[]
  trend: { date: string; orders: number; sales: string }[]
  categoryShare: { name: string; value: number }[]
}
