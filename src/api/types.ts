export interface ApiResponse<T> {
  code: string
  message: string
  data: T
  request_id?: string | null
}

export interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface PageData<T> {
  items: T[]
  pagination: Pagination
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface User {
  id: string
  email: string
  phone?: string | null
  is_active: boolean
  is_email_verified: boolean
  mfa_enabled: boolean
  created_at: string
}

export interface Profile {
  id: string
  user_id: string
  nickname?: string | null
  avatar_url?: string | null
  gender?: string | null
  birthday?: string | null
  bio?: string | null
}

export interface Me {
  user: User
  profile?: Profile | null
}

export interface Category {
  id: string
  parent_id?: string | null
  name: string
  icon_url?: string | null
  sort: number
  created_at?: string
}

export interface Sku {
  id: string
  product_id: string
  spec: string
  code?: string | null
  price: string
  is_active: boolean
}

export interface ProductImage {
  id: string
  url: string
  sort: number
}

export interface Product {
  id: string
  store_id: string
  category_id?: string | null
  aid_project_id?: string | null
  title: string
  subtitle?: string | null
  is_listed: boolean
  created_at: string
  min_price?: string | null
  cover_url?: string | null
  store_name?: string | null
}

export interface ProductDetail extends Product {
  description?: string | null
  status: string
  audit_reason?: string | null
  audited_at?: string | null
  skus: Sku[]
  images: ProductImage[]
}

export interface CartItem {
  id: string
  sku_id: string
  product_id: string
  product_title: string
  spec: string
  image_url?: string | null
  current_price: string
  quantity: number
  checked: boolean
  stock_available: number
  store_id: string
  store_name: string
}

export interface Cart {
  items: CartItem[]
  total_quantity: number
  checked_subtotal: string
}

export interface Address {
  id: string
  receiver: string
  phone: string
  province: string
  city: string
  district?: string | null
  detail: string
  is_default: boolean
}

export interface AddressInput {
  receiver: string
  phone: string
  province: string
  city: string
  district?: string | null
  detail: string
  is_default: boolean
}

export interface OrderItemInput {
  sku_id: string
  quantity: number
  expected_unit_price?: string | null
}

export interface PreviewItem {
  sku_id: string
  title: string
  spec: string
  unit_price: string
  quantity: number
  subtotal: string
}

export interface PreviewStore {
  store_id: string
  store_name: string
  items_total: string
  shipping_fee: string
  items: PreviewItem[]
}

export interface Preview {
  items_total: string
  shipping_fee: string
  points_deduct: string
  points_used: number
  pay_amount: string
  stores: PreviewStore[]
}

export interface OrderItem {
  id: string
  sku_id: string
  product_id: string
  title: string
  spec: string
  image_url?: string | null
  unit_price: string
  quantity: number
  subtotal: string
}

export interface StoreOrder {
  id: string
  store_order_no: string
  store_id: string
  status: string
  items_total: string
  shipping_fee: string
  pay_amount: string
  refund_amount: string
  shipped_at?: string | null
  completed_at?: string | null
  items: OrderItem[]
}

export interface Order {
  id: string
  order_no: string
  status: string
  receiver_name: string
  receiver_phone: string
  address: string
  items_total: string
  shipping_fee: string
  points_deduct: string
  points_used: number
  pay_amount: string
  currency: string
  remark?: string | null
  cancel_reason?: string | null
  paid_at?: string | null
  completed_at?: string | null
  cancelled_at?: string | null
  created_at: string
  store_orders: StoreOrder[]
}

export interface Payment {
  id: string
  pay_no: string
  order_id: string
  amount: string
  currency: string
  status: string
  provider: string
  expires_at: string
  paid_at?: string | null
  pay_url?: string | null
}

export interface Refund {
  id: string
  refund_no: string
  order_id: string
  store_order_id: string
  amount: string
  reason: string
  status: string
  result_note?: string | null
  created_at: string
  handled_at?: string | null
}

export interface ShipmentTrack {
  status: string
  description?: string | null
  occurred_at: string
}

export interface Shipment {
  id: string
  store_order_id: string
  carrier: string
  tracking_no: string
  status: string
  shipped_at: string
  delivered_at?: string | null
  tracks: ShipmentTrack[]
  mock?: boolean
}

export interface PointAccount {
  balance: number
}

export interface PointTransaction {
  id: string
  type: string
  amount: number
  balance_after: number
  source_type?: string | null
  source_id?: string | null
  note?: string | null
  created_at: string
}

export interface Redemption {
  reward_code: string
  name: string
  points: number
  mock: boolean
}

export interface RedeemResult {
  reward_code: string
  reward_name: string
  points_spent: number
  voucher_code: string
  mock: boolean
}

export interface AidProject {
  id: string
  cooperative_id: string
  title: string
  cover_url?: string | null
  description?: string | null
  goal_amount?: string | null
  raised_amount: string
  status: string
  published_at?: string | null
}

export interface AidDonation {
  id: string
  project_id: string
  project_title?: string | null
  amount: string
  points_earned: number
  display_mode: 'anonymous' | 'named'
  display_name?: string | null
  created_at: string
  balance?: number | null
}

export interface AidDonationInput {
  amount: string
  display_mode: 'anonymous' | 'named'
  display_name?: string | null
}

export interface AidProjectDonation {
  id: string
  donor: string
  display_mode: 'anonymous' | 'named'
  amount: string
  created_at: string
}

export interface GreenProfile {
  id: string
  product_id: string
  origin: string
  planting_mode?: string | null
  certifications?: unknown[] | null
  description?: string | null
  status: string
}

export interface CarbonAssessment {
  co2e_per_unit: string
  unit: string
  methodology?: string | null
  verified: boolean
  assessed_at: string
}

export interface GreenDetail {
  profile: GreenProfile
  carbon_assessment?: CarbonAssessment | null
}

export interface Notice {
  id: string
  title: string
  content: string
  published_at?: string | null
}

export interface Banner {
  id: string
  title: string
  image_url: string
  link_type: 'internal' | 'external'
  link_url: string
}

export interface AppNotification {
  id: string
  type: string
  title: string
  content: string
  read_at?: string | null
  created_at: string
}

export interface CmsSection {
  id?: string
  section_type: string
  sort: number
  enabled: boolean
  config: Record<string, unknown>
}

export interface CmsConfig {
  page: {
    page_key: string
    title: string
    version: number
  }
  sections: CmsSection[]
}

export interface Store {
  id: string
  merchant_id: string
  name: string
  logo_url?: string | null
  description?: string | null
  region?: string | null
  status: string
  is_closed_temporarily: boolean
  created_at: string
}
