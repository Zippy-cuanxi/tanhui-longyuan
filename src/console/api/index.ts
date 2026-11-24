/**
 * 页面只从这里引入 API：
 * - 当前为 mock 实现（src/console/api/*.ts）
 * - 将来替换真实接口时，保持这些函数签名与返回类型不变即可
 */
export { authApi } from './auth'
export { merchantApi } from './merchant'
export { adminApi } from './admin'
export { commonApi } from './common'
export * from './types'
export type {
  AdminAccountInput,
  AdminMerchantRow,
  AdminWithdrawalRow,
  AnnouncementInput,
  CategoryInput,
  CommissionSettings,
  MerchantDetail,
  MerchantPenalty,
  MemberDetail,
  SettlementPreview
} from './admin'
export type { MerchantFinanceOverview, ProductDraftInput } from './merchant'
export type { MockPageQuery } from './mock'
