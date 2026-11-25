import { getCmsConfig, queryString, request, requestRaw } from './http'
import type {
  Address,
  AddressInput,
  AidDonation,
  AidDonationInput,
  AidProject,
  AidProjectDonation,
  AppNotification,
  Banner,
  Cart,
  CartItem,
  Category,
  CmsConfig,
  GreenDetail,
  Me,
  Notice,
  Order,
  OrderItemInput,
  PageData,
  Payment,
  PointAccount,
  PointTransaction,
  Preview,
  Product,
  ProductDetail,
  Profile,
  Redemption,
  RedeemResult,
  Refund,
  Shipment,
  TokenPair,
  User
} from './types'

export interface ProfileUpdateInput {
  nickname?: string | null
  avatar_url?: string | null
  gender?: string | null
  birthday?: string | null
  bio?: string | null
}

export const authApi = {
  register: (payload: { email: string; password: string; nickname?: string }) =>
    registerRequest('/auth/register', payload),
  login: (payload: { email: string; password: string; mfa_code?: string }) =>
    request<TokenPair>('/auth/login', { method: 'POST', body: payload, skipAuthRefresh: true }),
  logout: () => request<null>('/auth/logout', { method: 'POST' }),
  me: () => request<Me>('/users/me'),
  updateMe: (payload: ProfileUpdateInput) =>
    request<Profile>('/users/me', { method: 'PATCH', body: payload }),
  uploadAvatar: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Profile>('/users/me/avatar', { method: 'POST', body: form })
  },
  sessions: () => request<unknown[]>('/auth/sessions'),
  revokeAll: () => request<null>('/auth/sessions/revoke-all', { method: 'POST' })
}

// 注册接口不自动刷新令牌
function registerRequest(path: string, body: unknown): Promise<User> {
  return request<User>(path, { method: 'POST', body, skipAuthRefresh: true })
}

export interface MerchantApplyInput {
  company_name: string
  license_no: string
  license_url?: string | null
  legal_person: string
  contact_phone: string
  region?: string | null
  store_name: string
}

export interface MerchantApplyResult {
  id: string
  status: string
  company_name: string
  store_name?: string
}

export const merchantApi = {
  apply: (payload: MerchantApplyInput) =>
    request<MerchantApplyResult>('/merchant/apply', { method: 'POST', body: payload }),
  myMerchants: () => request<MerchantApplyResult[]>('/merchant/merchants/me')
}

export const catalogApi = {
  products: (params: {
    category_id?: string
    store_id?: string
    keyword?: string
    sort?: 'created_desc' | 'price_asc'
    page?: number
    page_size?: number
  }) => request<PageData<Product>>(`/products${queryString(params)}`),
  product: (id: string) => request<ProductDetail>(`/products/${encodeURIComponent(id)}`),
  categories: () => request<Category[]>('/categories'),
  /** 可见商品目录指纹：用于消费者端感知管理端审核/下架变更。 */
  version: () =>
    request<{ version: string; count: number; updated_at: string | null }>('/catalog/version').then(
      (data) => data.version
    )
}

export const cartApi = {
  get: () => request<Cart>('/cart'),
  add: (payload: { sku_id: string; quantity: number }) =>
    request<CartItem>('/cart/items', { method: 'POST', body: payload }),
  update: (itemId: string, payload: { quantity?: number; checked?: boolean }) =>
    request<CartItem>(`/cart/items/${encodeURIComponent(itemId)}`, {
      method: 'PATCH',
      body: payload
    }),
  remove: (itemId: string) =>
    request<null>(`/cart/items/${encodeURIComponent(itemId)}`, { method: 'DELETE' })
}

export const addressApi = {
  list: () => request<Address[]>('/users/me/addresses'),
  create: (payload: AddressInput) =>
    request<Address>('/users/me/addresses', { method: 'POST', body: payload }),
  update: (addressId: string, payload: AddressInput) =>
    request<Address>(`/users/me/addresses/${encodeURIComponent(addressId)}`, {
      method: 'PUT',
      body: payload
    }),
  remove: (addressId: string) =>
    request<null>(`/users/me/addresses/${encodeURIComponent(addressId)}`, {
      method: 'DELETE'
    })
}

export const orderApi = {
  preview: (payload: {
    items: OrderItemInput[]
    use_points: boolean
    address_id?: string | null
  }) => request<Preview>('/orders/preview', { method: 'POST', body: payload }),
  create: (payload: {
    address_id: string
    items: OrderItemInput[]
    use_points: boolean
    remark?: string | null
    idempotency_key?: string
  }) => request<Order>('/orders', { method: 'POST', body: payload }),
  list: (params: { status?: string; page?: number; page_size?: number }) =>
    request<PageData<Order>>(`/orders${queryString(params)}`),
  detail: (orderId: string) => request<Order>(`/orders/${encodeURIComponent(orderId)}`),
  cancel: (orderId: string, reason?: string) =>
    request<Order>(`/orders/${encodeURIComponent(orderId)}/cancel`, {
      method: 'POST',
      body: reason ? { reason } : {}
    }),
  confirmReceipt: (orderId: string) =>
    request<Order>(`/orders/${encodeURIComponent(orderId)}/confirm-receipt`, { method: 'POST' }),
  refunds: (orderId: string) => request<Refund[]>(`/orders/${encodeURIComponent(orderId)}/refunds`),
  requestRefund: (
    orderId: string,
    payload: { reason: string; amount?: string | null; store_order_id?: string | null }
  ) =>
    request<Refund>(`/orders/${encodeURIComponent(orderId)}/refunds`, {
      method: 'POST',
      body: payload
    })
}

export const paymentApi = {
  init: (orderId: string) =>
    request<Payment>(`/payments/${encodeURIComponent(orderId)}/init`, { method: 'POST' }),
  get: (payNo: string) => request<Payment>(`/payments/${encodeURIComponent(payNo)}`),
  mockPay: (payNo: string) =>
    request<Record<string, unknown>>('/payments/mock/pay', {
      method: 'POST',
      body: { pay_no: payNo }
    })
}

export const logisticsApi = {
  forOrder: (orderId: string) => request<Shipment[]>(`/logistics/${encodeURIComponent(orderId)}`)
}

export const pointsApi = {
  account: () => request<PointAccount>('/points/account'),
  transactions: (params: { type_?: string; page?: number; page_size?: number }) =>
    request<PageData<PointTransaction>>(`/points/transactions${queryString(params)}`),
  catalog: () => request<Redemption[]>('/points/redemption-catalog'),
  redeem: (rewardCode: string) =>
    request<RedeemResult>('/points/redemptions', {
      method: 'POST',
      body: { reward_code: rewardCode }
    })
}

export const aidApi = {
  list: (params: { page?: number; page_size?: number }) =>
    request<PageData<AidProject>>(`/aid/projects${queryString(params)}`),
  detail: (projectId: string) =>
    request<AidProject>(`/aid/projects/${encodeURIComponent(projectId)}`),
  projectDonations: (projectId: string) =>
    request<AidProjectDonation[]>(`/aid/projects/${encodeURIComponent(projectId)}/donations`),
  myDonations: () => request<AidDonation[]>('/aid/donations/me'),
  donate: (projectId: string, payload: AidDonationInput) =>
    request<AidDonation>(`/aid/projects/${encodeURIComponent(projectId)}/donations`, {
      method: 'POST',
      body: payload
    })
}

export const greenApi = {
  detail: (productId: string) =>
    request<GreenDetail>(`/green/products/${encodeURIComponent(productId)}`)
}

export const notificationApi = {
  list: (unreadOnly = false) =>
    request<AppNotification[]>(`/notifications${queryString({ unread_only: unreadOnly })}`),
  markRead: (id: string) =>
    request<null>(`/notifications/${encodeURIComponent(id)}/read`, { method: 'POST' }),
  markAllRead: () => request<null>('/notifications/read-all', { method: 'POST' })
}

export const cmsApi = {
  config: (pageKey: string): Promise<CmsConfig> => getCmsConfig(pageKey),
  notices: async (): Promise<Notice[]> => {
    const result = await requestRaw<Notice[]>('/client/notices')
    return result.data || []
  },
  banners: async (): Promise<Banner[]> => {
    const result = await requestRaw<Banner[]>('/client/banners')
    return result.data || []
  }
}
