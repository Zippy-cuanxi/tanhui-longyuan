/* 【MOCK 数据】管理端/商家端内存数据库种子。
 * 所有列表 ≥ 20 条（特殊账号/角色/分类除外），覆盖主要状态。
 * 后续替换真实接口时，只需替换 src/console/api 下的实现，页面与类型不变。
 */
import { assetUrl } from '@/api/http'
import originHeat from '@/mocks/mock-origin-heat.json'
import { ADMIN_ROLE_NAMES, ADMIN_ROLE_PERMISSIONS } from '@/console/constants/permissions'
import { REFUND_REASONS, REJECT_REASONS } from '@/console/constants/labels'
import type {
  AdminAccount,
  AdminRole,
  AdminRoleCode,
  Aftersale,
  Announcement,
  Category,
  Member,
  MerchantAccount,
  MerchantBalance,
  Notification,
  OperationLog,
  Order,
  OrderStatus,
  Origin,
  Product,
  Settlement,
  SettlementAccount,
  Sku,
  Store,
  Withdrawal
} from '@/console/api/types'

export interface ConsoleDb {
  version: number
  seededAt: string
  merchants: MerchantAccount[]
  stores: Store[]
  products: Product[]
  orders: Order[]
  aftersales: Aftersale[]
  settlements: Settlement[]
  withdrawals: Withdrawal[]
  members: Member[]
  categories: Category[]
  origins: Origin[]
  originMonths: string[]
  announcements: Announcement[]
  admins: AdminAccount[]
  roles: AdminRole[]
  logs: OperationLog[]
  notifications: Notification[]
  settlementAccounts: Record<string, SettlementAccount>
  balances: Record<string, MerchantBalance>
  settings: Record<string, string>
  commissionRate: string
}

const DB_VERSION = 3
const DAY = 24 * 60 * 60 * 1000
const NOW = Date.now()
const IMG = {
  apple: assetUrl('/console-assets/images/apple.png'),
  potato: assetUrl('/console-assets/images/potato.png'),
  melon: assetUrl('/console-assets/images/melon.png'),
  goji: assetUrl('/console-assets/images/goji.png'),
  jujube: assetUrl('/console-assets/images/jujube.png'),
  lily: assetUrl('/console-assets/images/lily.png'),
  danggui: assetUrl('/console-assets/images/danggui.png'),
  merchant: assetUrl('/console-assets/images/avatar-merchant.png'),
  admin: assetUrl('/console-assets/images/avatar-admin.png')
}
const SHOP_LOGOS = [
  assetUrl('/console-assets/images/shop-logo-1.png'),
  assetUrl('/console-assets/images/shop-logo-2.png'),
  assetUrl('/console-assets/images/shop-logo-3.png')
]

function iso(daysAgo = 0, hour = 10, minute = 0): string {
  const date = new Date(NOW - daysAgo * DAY)
  date.setHours(hour, minute, 0, 0)
  return date.toISOString()
}
function money(value: number): string {
  return value.toFixed(2)
}
function pick<T>(items: T[], index: number): T {
  return items[index % items.length]
}
function pad(value: number, length = 3): string {
  return String(value).padStart(length, '0')
}

const CATEGORY_DEFS = [
  ['cat-fruit', '水果生鲜', 1],
  ['cat-grain', '粮油杂粮', 2],
  ['cat-food', '特色食品', 3],
  ['cat-herb', '中药材', 4],
  ['cat-special', '甘肃特产', 5],
  ['cat-culture', '甘味文创', 6],
  ['cat-dairy', '乳品烘焙', 7],
  ['cat-meat', '牛羊肉禽', 8]
] as const

const BASE_PRODUCTS = [
  {
    title: '静宁红富士苹果',
    subtitle: '高原红富士 · 脆甜多汁',
    categoryId: 'cat-fruit',
    categoryName: '水果生鲜',
    image: IMG.apple,
    price: 59.9,
    skus: [
      { spec: '5kg 精选装', price: 59.9, stock: 1280 },
      { spec: '10kg 家庭装', price: 108, stock: 520 }
    ],
    origin: '甘肃省平凉市静宁县',
    mode: '高原梯田果园种植',
    aid: '静宁苹果产业提质计划'
  },
  {
    title: '定西马铃薯',
    subtitle: '沙壤土豆 · 粉糯香甜',
    categoryId: 'cat-grain',
    categoryName: '粮油杂粮',
    image: IMG.potato,
    price: 29.9,
    skus: [
      { spec: '10kg 装', price: 29.9, stock: 3200 },
      { spec: '20kg 家庭装', price: 49.9, stock: 900 }
    ],
    origin: '甘肃省定西市',
    mode: '旱作梯田种植',
    aid: '定西马铃薯助农增收计划'
  },
  {
    title: '民勤蜜瓜',
    subtitle: '绿洲沙地 · 清甜多汁',
    categoryId: 'cat-fruit',
    categoryName: '水果生鲜',
    image: IMG.melon,
    price: 39.9,
    skus: [
      { spec: '5kg 装（2-3 个）', price: 39.9, stock: 760 },
      { spec: '10kg 装（4-6 个）', price: 69.9, stock: 260 }
    ],
    origin: '甘肃省武威市民勤县',
    mode: '绿洲沙地种植',
    aid: '民勤蜜瓜节水种植帮扶'
  },
  {
    title: '甘肃枸杞',
    subtitle: '果粒饱满 · 色泽自然',
    categoryId: 'cat-herb',
    categoryName: '中药材',
    image: IMG.goji,
    price: 89.9,
    skus: [
      { spec: '500g 装', price: 89.9, stock: 980 },
      { spec: '1kg 装', price: 169, stock: 420 }
    ],
    origin: '甘肃省白银市景泰县',
    mode: '盐碱地生态种植'
  },
  {
    title: '临泽小枣',
    subtitle: '绿洲枣园 · 枣香浓郁',
    categoryId: 'cat-special',
    categoryName: '甘肃特产',
    image: IMG.jujube,
    price: 49.9,
    skus: [
      { spec: '1kg 装', price: 49.9, stock: 86 },
      { spec: '2kg 装', price: 89.9, stock: 180 }
    ],
    origin: '甘肃省张掖市临泽县',
    mode: '绿洲枣园种植'
  },
  {
    title: '兰州百合',
    subtitle: '瓣大肉厚 · 清甜粉糯',
    categoryId: 'cat-food',
    categoryName: '特色食品',
    image: IMG.lily,
    price: 69.9,
    skus: [
      { spec: '500g 特级', price: 69.9, stock: 540 },
      { spec: '1kg 特级', price: 129, stock: 210 }
    ],
    origin: '甘肃省兰州市七里河区',
    mode: '山地百合种植'
  },
  {
    title: '岷县当归',
    subtitle: '根条完整 · 香气浓郁',
    categoryId: 'cat-herb',
    categoryName: '中药材',
    image: IMG.danggui,
    price: 79.9,
    skus: [
      { spec: '500g 装', price: 79.9, stock: 620 },
      { spec: '1kg 装', price: 149, stock: 180 }
    ],
    origin: '甘肃省定西市岷县',
    mode: '高寒阴湿区种植'
  }
]

const SPECIAL_MERCHANTS: Array<Partial<MerchantAccount> & { username: string }> = [
  {
    username: 'merchant01',
    companyName: '静宁县红果种植专业合作社',
    storeName: '静宁县红果种植专业合作社',
    ownerName: '张红果',
    region: '甘肃省平凉市静宁县',
    status: 'normal'
  },
  {
    username: 'merchant_pending',
    companyName: '定西金薯种植专业合作社',
    storeName: '定西金薯种植专业合作社',
    ownerName: '李金薯',
    region: '甘肃省定西市安定区',
    status: 'pending'
  },
  {
    username: 'merchant_rejected',
    companyName: '兰州百合源生态农业合作社',
    storeName: '兰州百合源生态农业合作社',
    ownerName: '王百合',
    region: '甘肃省兰州市七里河区',
    status: 'rejected',
    rejectReason: '营业执照图片不清晰'
  },
  {
    username: 'merchant_frozen',
    companyName: '民勤绿洲蜜瓜合作社',
    storeName: '民勤绿洲蜜瓜合作社',
    ownerName: '马绿洲',
    region: '甘肃省武威市民勤县',
    status: 'frozen',
    frozenReason: '多次发货超时'
  }
]

const OTHER_MERCHANT_NAMES = [
  '临泽枣园种植合作社',
  '岷县当归中药材合作社',
  '甘肃枸杞产业合作社',
  '陇南橄榄油合作社',
  '天水花牛苹果合作社',
  '张掖玉米制种合作社',
  '酒泉戈壁农业合作社',
  '武威葡萄酒庄',
  '庆阳苹果合作社',
  '平凉红牛养殖合作社',
  '甘南牦牛乳业合作社',
  '白银文冠果合作社',
  '金昌藜麦合作社',
  '嘉峪关果蔬合作社',
  '定西中药材合作社',
  '兰州高原夏菜合作社',
  '临夏花椒合作社',
  '陇南核桃合作社',
  '敦煌葡萄合作社',
  '山丹羊肉合作社'
]

const MEMBER_NAMES = [
  '王小明',
  '李静',
  '张雪',
  '刘洋',
  '陈晨',
  '杨帆',
  '赵磊',
  '黄丽',
  '周强',
  '吴敏',
  '徐涛',
  '孙悦',
  '马超',
  '朱琳',
  '胡军',
  '郭佳',
  '何平',
  '高洁',
  '林峰',
  '罗娜',
  '梁宇',
  '宋雨',
  '郑浩',
  '谢婷',
  '韩冰',
  '唐宁',
  '冯雪',
  '董凯',
  '萧然',
  '程璐'
]

const ORDER_STATUSES: OrderStatus[] = [
  'pending_payment',
  'paid',
  'paid',
  'shipped',
  'completed',
  'completed',
  'refunding',
  'refunded',
  'cancelled',
  'paid',
  'shipped',
  'completed',
  'partially_refunded',
  'paid',
  'pending_payment',
  'shipped',
  'completed',
  'paid',
  'refunding',
  'completed',
  'paid',
  'cancelled',
  'shipped',
  'completed',
  'paid',
  'refunded',
  'paid',
  'shipped',
  'completed',
  'paid',
  'refunding',
  'completed',
  'paid',
  'shipped',
  'completed',
  'pending_payment'
]

const AFTERSALE_STATUSES: Aftersale['status'][] = [
  'requested',
  'arbitrating',
  'rejected',
  'refunded',
  'requested',
  'arbitrating',
  'refunded',
  'rejected'
]

function buildMerchants(): MerchantAccount[] {
  const merchants: MerchantAccount[] = []
  for (let index = 0; index < 24; index += 1) {
    const special = SPECIAL_MERCHANTS[index]
    const username = special?.username || `merchant${pad(index + 1, 2)}`
    const company = special?.companyName || OTHER_MERCHANT_NAMES[index - 4]
    const status =
      special?.status || (index % 7 === 0 ? 'pending' : index % 11 === 0 ? 'frozen' : 'normal')
    const regions = [
      '甘肃省张掖市临泽县',
      '甘肃省定西市岷县',
      '甘肃省白银市景泰县',
      '甘肃省陇南市武都区',
      '甘肃省天水市麦积区',
      '甘肃省张掖市甘州区',
      '甘肃省酒泉市肃州区',
      '甘肃省武威市凉州区',
      '甘肃省庆阳市西峰区',
      '甘肃省平凉市崆峒区',
      '甘肃省甘南州合作市',
      '甘肃省白银市白银区',
      '甘肃省金昌市金川区',
      '甘肃省嘉峪关市',
      '甘肃省定西市陇西县',
      '甘肃省兰州市榆中县',
      '甘肃省临夏州临夏市',
      '甘肃省陇南市成县',
      '甘肃省敦煌市',
      '甘肃省张掖市山丹县'
    ]
    merchants.push({
      id: `m${pad(index + 1, 2)}`,
      username,
      password: 'Demo@123456',
      companyName: company,
      storeName: special?.storeName || company,
      ownerName: special?.ownerName || `${pick(MEMBER_NAMES, index)}（负责人）`,
      phone: `1380000${pad(index + 1, 4)}`,
      email: `${username}@tanhui.example.com`,
      region: special?.region || pick(regions, index),
      licenseNo: `91620000MA${pad(1000 + index, 6)}`,
      licenseImage: pick(SHOP_LOGOS, index),
      status,
      rejectReason:
        special?.rejectReason || (status === 'rejected' ? '资质材料不清晰，请重新提交' : undefined),
      frozenReason: special?.frozenReason || (status === 'frozen' ? '多次发货超时' : undefined),
      createdAt: iso(180 - index * 5, 9 + (index % 8)),
      reviewedAt: status === 'pending' ? undefined : iso(150 - index * 4),
      avatar: IMG.merchant
    })
  }
  return merchants
}

function buildStores(merchants: MerchantAccount[]): Store[] {
  return merchants.map((merchant, index) => {
    const status =
      merchant.status === 'normal'
        ? 'active'
        : merchant.status === 'frozen'
          ? 'suspended'
          : 'suspended'
    return {
      id: `store-${merchant.id}`,
      merchantId: merchant.id,
      name: merchant.storeName,
      logo: pick(SHOP_LOGOS, index),
      region: merchant.region,
      description: `${merchant.companyName}，甘肃产地直供，绿色资料可查。`,
      status,
      rating: (4.7 + (index % 4) * 0.1).toFixed(1),
      shippingTemplates: [
        {
          id: `ship-${merchant.id}-1`,
          name: '全国满 99 包邮',
          freeThreshold: '99.00',
          baseFee: '8.00',
          regions: '全国（除港澳台）',
          enabled: true
        },
        {
          id: `ship-${merchant.id}-2`,
          name: '偏远地区加价',
          freeThreshold: '199.00',
          baseFee: '15.00',
          regions: '新疆、西藏、青海、宁夏',
          enabled: true
        },
        {
          id: `ship-${merchant.id}-3`,
          name: '同城自提',
          freeThreshold: '0.00',
          baseFee: '0.00',
          regions: '兰州市区',
          enabled: false
        }
      ],
      qualifications: [
        {
          id: `q-${merchant.id}-1`,
          name: '营业执照',
          image: merchant.licenseImage,
          status:
            merchant.status === 'pending' || merchant.status === 'rejected'
              ? 'pending'
              : 'approved',
          reason: merchant.status === 'rejected' ? merchant.rejectReason : undefined
        },
        {
          id: `q-${merchant.id}-2`,
          name: '食品经营许可证',
          image: pick(SHOP_LOGOS, index + 1),
          status: 'approved'
        },
        {
          id: `q-${merchant.id}-3`,
          name: '产地合作证明',
          image: pick(SHOP_LOGOS, index + 2),
          status: 'approved'
        }
      ]
    }
  })
}

const PRODUCT_STATUSES: Product['status'][] = [
  'approved',
  'approved',
  'pending_review',
  'rejected',
  'draft',
  'pending_review',
  'approved',
  'removed',
  'approved',
  'pending_review',
  'approved',
  'rejected',
  'approved',
  'draft',
  'approved',
  'pending_review',
  'approved',
  'approved',
  'rejected',
  'approved',
  'pending_review',
  'approved',
  'approved',
  'pending_review',
  'approved',
  'rejected',
  'draft',
  'approved'
]

function buildProducts(merchants: MerchantAccount[], stores: Store[]): Product[] {
  const products: Product[] = []
  for (let index = 0; index < 28; index += 1) {
    const merchant = index < 22 ? merchants[0] : merchants[4 + (index % 20)]
    const store = stores.find((item) => item.merchantId === merchant.id) || stores[0]
    const base = BASE_PRODUCTS[index % BASE_PRODUCTS.length]
    const variantLabel = ['', '', '', '礼盒装', '家庭装', '精品装', '尝鲜装'][index % 7]
    const title = variantLabel ? `${base.title} · ${variantLabel}` : base.title
    const status = PRODUCT_STATUSES[index]
    const listed = status === 'approved' && index % 9 !== 8 && index !== 20
    const skus: Sku[] = base.skus.map((sku, skuIndex) => ({
      id: `sku-${index}-${skuIndex + 1}`,
      spec: sku.spec,
      price: money(sku.price + (index % 4) * 2),
      stock: Math.max(0, sku.stock - (index % 5) * 37),
      code: `SKU-${pad(index + 1, 3)}-${skuIndex + 1}`
    }))
    const price = Number(skus[0].price)
    const stock = skus.reduce((sum, sku) => sum + sku.stock, 0)
    const auditRecords: Product['auditRecords'] = [
      {
        id: `audit-${index}-1`,
        action: 'submit',
        operator: merchant.ownerName,
        createdAt: iso(35 - (index % 20), 9)
      }
    ]
    if (status === 'approved') {
      auditRecords.push({
        id: `audit-${index}-2`,
        action: 'approve',
        operator: '产品审核员',
        createdAt: iso(30 - (index % 18), 14)
      })
    }
    if (status === 'rejected') {
      auditRecords.push({
        id: `audit-${index}-2`,
        action: 'reject',
        operator: '产品审核员',
        reason: pick(REJECT_REASONS, index),
        createdAt: iso(28 - (index % 15), 15)
      })
    }
    if (status === 'removed') {
      auditRecords.push({
        id: `audit-${index}-2`,
        action: 'remove',
        operator: '平台管理员',
        reason: '商品信息不符合平台规范',
        createdAt: iso(12, 16)
      })
    }
    const hasChange = status === 'pending_review' && index % 3 === 0
    products.push({
      id: `p${pad(index + 1, 3)}`,
      merchantId: merchant.id,
      storeId: store.id,
      storeName: store.name,
      title,
      subtitle: base.subtitle,
      categoryId: base.categoryId,
      categoryName: base.categoryName,
      description: `${base.title}——甘肃产地直发，${base.subtitle}。${base.origin}产地信息以平台审核记录为准。`,
      price: money(price),
      minPrice: money(price),
      stock,
      sales: 120 + ((index * 73) % 820),
      status,
      listed,
      cover: base.image,
      images: [base.image],
      skus,
      shippingTemplateId: store.shippingTemplates[0]?.id || '',
      greenProfile: {
        origin: base.origin,
        plantingMode: base.mode,
        description: `${base.origin}产地，${base.mode}，绿色资料由商家提交并经平台审核。`,
        status:
          status === 'approved'
            ? 'approved'
            : status === 'pending_review'
              ? 'pending_review'
              : status === 'rejected'
                ? 'rejected'
                : 'draft'
      },
      aidProjectId: index < 3 ? `aid-${index + 1}` : undefined,
      aidProjectName: index < 3 ? base.aid : undefined,
      auditReason:
        status === 'rejected'
          ? pick(REJECT_REASONS, index)
          : status === 'removed'
            ? '商品信息不符合平台规范'
            : undefined,
      auditRecords,
      change: hasChange
        ? [
            {
              field: 'title',
              label: '商品标题',
              oldValue: base.title,
              newValue: title
            },
            {
              field: 'images',
              label: '商品主图',
              oldValue: base.image,
              newValue: base.image
            },
            {
              field: 'description',
              label: '商品描述',
              oldValue: `${base.title}——甘肃产地直发。`,
              newValue: `${base.title}——甘肃产地直发，${base.subtitle}。`
            }
          ]
        : undefined,
      createdAt: iso(55 - index, 8 + (index % 9), index % 60),
      updatedAt: iso(index % 3, 11, index % 60)
    })
  }
  return products
}

function buildMembers(): Member[] {
  return Array.from({ length: 30 }, (_, index) => {
    const name = MEMBER_NAMES[index % MEMBER_NAMES.length]
    const banned = index % 11 === 4
    return {
      id: `u${pad(index + 1, 3)}`,
      nickname: `${name}${index + 1}`,
      email: `buyer${pad(index + 1, 2)}@tanhui.example.com`,
      phone: `1390000${pad(index + 1, 4)}`,
      status: banned ? 'banned' : 'active',
      roles: ['消费者'],
      orderCount: 1 + (index % 9),
      totalPaid: money(68 + index * 37.6),
      points: 120 + index * 47,
      createdAt: iso(120 - index * 2, 10 + (index % 8)),
      lastLoginAt: iso(index % 9, 9 + (index % 10)),
      banReason: banned ? '异常下单行为（演示）' : undefined
    }
  })
}

function buildOrders(
  merchants: MerchantAccount[],
  stores: Store[],
  products: Product[],
  members: Member[]
): Order[] {
  const orders: Order[] = []
  for (let index = 0; index < 36; index += 1) {
    const merchant = index < 26 ? merchants[0] : merchants[4 + (index % 20)]
    const store = stores.find((item) => item.merchantId === merchant.id) || stores[0]
    const merchantProducts = products.filter((item) => item.merchantId === merchant.id)
    const source = merchantProducts.length ? merchantProducts : products.slice(0, 4)
    const product = pick(source, index)
    const product2 = pick(source, index + 2)
    const status = ORDER_STATUSES[index]
    const quantity = 1 + (index % 2)
    const items = [
      {
        id: `oi-${index}-1`,
        productId: product.id,
        title: product.title,
        spec: product.skus[0]?.spec || '默认规格',
        price: product.skus[0]?.price || product.price,
        quantity,
        image: product.cover
      }
    ]
    if (index % 3 === 0) {
      items.push({
        id: `oi-${index}-2`,
        productId: product2.id,
        title: product2.title,
        spec: product2.skus[0]?.spec || '默认规格',
        price: product2.skus[0]?.price || product2.price,
        quantity: 1,
        image: product2.cover
      })
    }
    const itemsTotal = items.reduce((sum, item) => sum + Number(item.price) * item.quantity, 0)
    const shippingFee = itemsTotal >= 99 ? 0 : 8
    const payAmount = itemsTotal + shippingFee
    const member = members[index % members.length]
    // 前两单落在今日，便于工作台演示「今日订单 / 今日销售额」
    const createdAt =
      index === 1
        ? iso(0, 8, 20)
        : index === 2
          ? iso(0, 10, 5)
          : iso(42 - index, 8 + (index % 10), index % 60)
    const paidAt =
      status === 'pending_payment' || status === 'cancelled'
        ? undefined
        : new Date(new Date(createdAt).getTime() + 18 * 60 * 1000).toISOString()
    const shipDeadline = paidAt
      ? new Date(new Date(paidAt).getTime() + 48 * 60 * 60 * 1000).toISOString()
      : undefined
    const shippedAt = ['shipped', 'completed', 'refunded', 'partially_refunded'].includes(status)
      ? new Date(new Date(createdAt).getTime() + 26 * 60 * 60 * 1000).toISOString()
      : undefined
    const completedAt =
      status === 'completed'
        ? new Date(new Date(createdAt).getTime() + 72 * 60 * 60 * 1000).toISOString()
        : undefined
    const refundAmount =
      status === 'refunded' ? payAmount : status === 'partially_refunded' ? payAmount / 2 : 0
    const shipment = shippedAt
      ? {
          carrier: pick(['顺丰速运', '京东物流', '中通快递'], index),
          trackingNo: `SF${202600000 + index}`,
          shippedAt,
          status: completedAt ? 'completed' : 'shipped',
          tracks: [
            { time: shippedAt, text: '商家已发货，包裹已揽收' },
            {
              time: new Date(new Date(shippedAt).getTime() + 6 * 60 * 60 * 1000).toISOString(),
              text: '包裹运输中'
            }
          ]
        }
      : undefined
    orders.push({
      id: `o${pad(index + 1, 3)}`,
      orderNo: `TH2026${pad(index + 1, 4)}`,
      merchantId: merchant.id,
      storeId: store.id,
      storeName: store.name,
      buyerName: member.nickname,
      buyerPhone: member.phone,
      buyerEmail: member.email,
      address: `甘肃省兰州市城关区张掖路街道 ${88 + index} 号 ${1 + (index % 6)} 单元 ${501 + index}`,
      items,
      itemsTotal: money(itemsTotal),
      shippingFee: money(shippingFee),
      payAmount: money(payAmount),
      refundAmount: money(refundAmount),
      status,
      createdAt,
      paidAt,
      shipDeadline,
      shippedAt,
      completedAt,
      shipment,
      remark: index % 4 === 0 ? '请尽快发货' : undefined,
      statusLogs: [
        { time: createdAt, action: 'create', status: 'pending_payment', operator: '买家' },
        ...(paidAt
          ? [{ time: paidAt, action: 'payment_success', status: 'paid', operator: '系统' }]
          : []),
        ...(shippedAt
          ? [{ time: shippedAt, action: 'ship', status: 'shipped', operator: '商家' }]
          : []),
        ...(completedAt
          ? [
              {
                time: completedAt,
                action: 'confirm_receipt',
                status: 'completed',
                operator: '买家'
              }
            ]
          : [])
      ]
    })
  }
  return orders
}

function buildAftersales(
  merchants: MerchantAccount[],
  products: Product[],
  orders: Order[]
): Aftersale[] {
  const aftersales: Aftersale[] = []
  for (let index = 0; index < 24; index += 1) {
    const merchant = index < 18 ? merchants[0] : merchants[4 + (index % 20)]
    const merchantOrders = orders.filter((item) => item.merchantId === merchant.id)
    const order = pick(merchantOrders.length ? merchantOrders : orders, index)
    const status = AFTERSALE_STATUSES[index]
    const amount = status === 'refunded' ? order.payAmount : money(Number(order.payAmount) / 2)
    if (status === 'requested' || status === 'arbitrating') {
      order.status = 'refunding'
      order.refundAmount = '0.00'
    } else if (status === 'refunded') {
      order.status = 'refunded'
      order.refundAmount = order.payAmount
    }
    const merchantProduct = products.find((item) => item.merchantId === merchant.id)
    aftersales.push({
      id: `as${pad(index + 1, 3)}`,
      refundNo: `RF2026${pad(index + 1, 4)}`,
      orderId: order.id,
      orderNo: order.orderNo,
      merchantId: merchant.id,
      storeId: order.storeId,
      storeName: order.storeName,
      buyerName: order.buyerName,
      buyerPhone: order.buyerPhone,
      amount,
      reason: pick(REFUND_REASONS, index),
      evidence: [merchantProduct?.cover || IMG.apple],
      status,
      merchantReason:
        status === 'arbitrating' || status === 'rejected'
          ? '商品已拆封影响二次销售，拒绝退款'
          : undefined,
      adminReason:
        status === 'refunded'
          ? '平台核实符合退款条件，支持退款'
          : status === 'rejected'
            ? '证据不足以支持退款，维持商家处理'
            : undefined,
      createdAt: iso(25 - (index % 20), 9 + (index % 8)),
      handledAt: status === 'requested' ? undefined : iso(20 - (index % 16), 14),
      orderPayAmount: order.payAmount,
      orderRefundAmount: order.refundAmount
    })
  }
  return aftersales
}

function buildSettlements(merchants: MerchantAccount[], stores: Store[]): Settlement[] {
  const settlements: Settlement[] = []
  for (let index = 0; index < 32; index += 1) {
    const merchant = index < 20 ? merchants[0] : merchants[4 + (index % 20)]
    const store = stores.find((item) => item.merchantId === merchant.id) || stores[0]
    const ordersTotal = 1280 + ((index * 733) % 9200)
    const commission = ordersTotal * 0.05
    const refundDeduct = index % 5 === 0 ? ordersTotal * 0.08 : 0
    const payable = ordersTotal - commission - refundDeduct
    const status = index % 5 === 0 ? 'pending' : index % 5 === 1 ? 'confirmed' : 'paid'
    const start = new Date(NOW - (18 + index * 15) * DAY)
    const end = new Date(start.getTime() + 15 * DAY)
    settlements.push({
      id: `st${pad(index + 1, 3)}`,
      settlementNo: `ST2026${pad(index + 1, 4)}`,
      merchantId: merchant.id,
      storeId: store.id,
      storeName: store.name,
      periodStart: start.toISOString(),
      periodEnd: end.toISOString(),
      orderCount: 4 + (index % 23),
      ordersTotal: money(ordersTotal),
      commission: money(commission),
      payable: money(payable),
      refundDeduct: money(refundDeduct),
      status,
      createdAt: iso(18 + index * 15, 10),
      confirmedAt: status !== 'pending' ? iso(15 + index * 15, 11) : undefined,
      paidAt: status === 'paid' ? iso(12 + index * 15, 15) : undefined
    })
  }
  return settlements
}

function buildWithdrawals(merchants: MerchantAccount[]): Withdrawal[] {
  return Array.from({ length: 28 }, (_, index) => {
    const merchant = index < 20 ? merchants[0] : merchants[4 + (index % 20)]
    const status =
      index % 5 === 0
        ? 'pending'
        : index % 5 === 1
          ? 'approved'
          : index % 5 === 2
            ? 'rejected'
            : 'approved'
    return {
      id: `wd${pad(index + 1, 3)}`,
      merchantId: merchant.id,
      amount: money(500 + ((index * 1370) % 18000)),
      accountName: merchant.ownerName,
      bankName: '中国农业银行',
      accountNo: `6228480000${pad(index + 1, 6)}`,
      status,
      createdAt: iso(30 - (index % 25), 10 + (index % 8)),
      handledAt: status === 'pending' ? undefined : iso(26 - (index % 22), 14),
      reason: status === 'rejected' ? '结算账户信息需与营业执照一致' : undefined
    }
  })
}

function buildAnnouncements(): Announcement[] {
  const titles = [
    '平台试运营公告',
    '绿色消费专区上线通知',
    '关于规范商品产地产地信息的通知',
    '春节发货安排',
    '商家结算周期调整说明',
    '助农项目公示（第一期）',
    '绿豆积分规则说明',
    '平台服务协议更新',
    '商品审核标准更新',
    '产地合作社入驻指引',
    '关于打击虚假宣传的公告',
    '平台客服服务时间调整',
    '绿色资料提交规范',
    '订单发货时效提醒',
    '用户隐私保护说明',
    '平台系统维护通知',
    '甘肃特色农产品品控标准',
    '商家违规处理规则',
    '助农公益项目招募',
    '平台年度报告'
  ]
  return titles.map((title, index) => {
    const status = index % 5 === 0 ? 'draft' : index % 7 === 0 ? 'offline' : 'published'
    return {
      id: `ann${pad(index + 1, 3)}`,
      title,
      content: `${title}：碳惠陇原平台当前为演示环境，公告内容为仿真数据，正式规则以平台发布为准。`,
      status,
      author: '运营管理员',
      createdAt: iso(40 - index, 9),
      publishedAt: status === 'published' ? iso(39 - index, 10) : undefined
    }
  })
}

function buildAdmins(): { admins: AdminAccount[]; roles: AdminRole[] } {
  const roleMeta: Array<[AdminRoleCode, string, string]> = [
    ['super_admin', '超级管理员', '全部权限，高风险操作需二次确认'],
    ['ops_admin', '运营管理员', '商家/店铺查看、订单、CMS、助农、审计'],
    ['product_auditor', '商品审核员', '商品审核、平台下架、绿色资料审核'],
    ['finance_admin', '财务管理员', '结算、提现、退款、财务查看'],
    ['cs_admin', '客服管理员', '订单、退款售后、会员查看']
  ]
  const roles: AdminRole[] = roleMeta.map(([code, name, description]) => ({
    code,
    name,
    description,
    permissions: ADMIN_ROLE_PERMISSIONS[code],
    builtIn: true
  }))
  const accountDefs: Array<[string, string, AdminRoleCode]> = [
    ['admin_super', '平台超级管理员', 'super_admin'],
    ['admin_ops', '运营管理员小陇', 'ops_admin'],
    ['admin_audit', '商品审核员小审', 'product_auditor'],
    ['admin_cs', '客服管理员小客', 'cs_admin'],
    ['admin_fin', '财务管理员小财', 'finance_admin']
  ]
  const admins = accountDefs.map(([username, name, roleCode], index) => ({
    id: `a${pad(index + 1, 2)}`,
    username,
    name,
    roleCode,
    roleName: ADMIN_ROLE_NAMES[roleCode],
    permissions: ADMIN_ROLE_PERMISSIONS[roleCode],
    status: 'active' as const,
    avatar: IMG.admin,
    lastLoginAt: iso(index, 9 + index),
    createdAt: iso(220 - index * 10, 9)
  }))
  return { admins, roles }
}

function buildLogs(admins: AdminAccount[], merchants: MerchantAccount[]): OperationLog[] {
  const actions = [
    ['merchant.review', '商家审核', '商家', 'high'],
    ['product.audit', '商品审核', '商品', 'normal'],
    ['product.remove', '平台下架', '商品', 'high'],
    ['aftersale.arbitrate', '售后仲裁', '售后', 'high'],
    ['withdrawal.review', '提现审核', '财务', 'high'],
    ['rbac.role_update', '角色权限修改', '系统', 'high'],
    ['settings.update', '系统设置更新', '系统', 'high'],
    ['order.ship', '订单发货', '订单', 'normal'],
    ['member.ban', '会员封禁', '会员', 'high'],
    ['finance.settlement_confirm', '结算确认', '财务', 'normal'],
    ['cms.announcement_publish', '公告发布', '内容', 'normal'],
    ['aid.project_review', '助农项目审核', '助农', 'normal']
  ] as const
  return Array.from({ length: 40 }, (_, index) => {
    const admin = pick(admins, index)
    const merchant = pick(merchants, index)
    const [action, actionName, module, risk] = actions[index % actions.length]
    return {
      id: `log${pad(index + 1, 3)}`,
      actor: admin.username,
      actorName: admin.name,
      action,
      module,
      target: module === '商家' ? merchant.companyName : `${module} #${pad(index + 1, 3)}`,
      detail: `${actionName}：演示操作记录，操作结果成功`,
      ip: `10.0.0.${10 + (index % 50)}`,
      risk,
      createdAt: iso(20 - (index % 19), 9 + (index % 10), index % 60)
    }
  })
}

function buildNotifications(): Notification[] {
  const defs: Array<[Notification['type'], string, string]> = [
    ['order', '您有新的订单待发货', '订单 TH20260001 已支付，请在 48 小时内发货。'],
    ['aftersale', '买家提交了退款申请', '退款单 RF20260001 等待处理。'],
    ['finance', '结算单已生成', '本期结算单已生成，请核对金额。'],
    ['system', '平台规则更新', '商品审核标准已更新，请查看公告。'],
    ['notice', '平台试运营公告', '当前为演示环境，支付与物流均为仿真数据。']
  ]
  return Array.from({ length: 24 }, (_, index) => {
    const [type, title, content] = defs[index % defs.length]
    return {
      id: `n${pad(index + 1, 3)}`,
      type,
      title,
      content,
      read: index % 4 === 0,
      createdAt: iso(index % 12, 9 + (index % 9)),
      source: '平台'
    }
  })
}

function buildAftersaleRefundDeductions(settlements: Settlement[], aftersales: Aftersale[]): void {
  const refunded = aftersales.filter((item) => item.status === 'refunded')
  settlements.forEach((settlement, index) => {
    if (index % 4 !== 0) return
    const related = refunded.find((item) => item.merchantId === settlement.merchantId)
    if (!related) return
    const deduct = Number(related.amount)
    settlement.refundDeduct = money(deduct)
    settlement.payable = money(
      Math.max(0, Number(settlement.ordersTotal) - Number(settlement.commission) - deduct)
    )
  })
}

export function seedDb(): ConsoleDb {
  const merchants = buildMerchants()
  const stores = buildStores(merchants)
  const products = buildProducts(merchants, stores)
  const members = buildMembers()
  const orders = buildOrders(merchants, stores, products, members)
  const aftersales = buildAftersales(merchants, products, orders)
  const settlements = buildSettlements(merchants, stores)
  buildAftersaleRefundDeductions(settlements, aftersales)
  const withdrawals = buildWithdrawals(merchants)
  const announcements = buildAnnouncements()
  const { admins, roles } = buildAdmins()
  const logs = buildLogs(admins, merchants)
  const notifications = buildNotifications()
  const categories: Category[] = CATEGORY_DEFS.map(([id, name, sort]) => ({
    id,
    name,
    parentId: undefined,
    productCount: products.filter((item) => item.categoryId === id).length,
    sort,
    enabled: true
  }))
  const originSource = originHeat as unknown as { origins: Origin[]; meta: { months: string[] } }
  const origins = originSource.origins
  const originMonths = originSource.meta.months
  const settlementAccounts: Record<string, SettlementAccount> = {}
  const balances: Record<string, MerchantBalance> = {}
  merchants.forEach((merchant, index) => {
    settlementAccounts[merchant.id] = {
      merchantId: merchant.id,
      accountName: merchant.ownerName,
      bankName: '中国农业银行',
      accountNo: `6228480000${pad(index + 1, 6)}`,
      branch: `${merchant.region}支行`,
      verified: merchant.status === 'normal'
    }
    const pending = settlements
      .filter((item) => item.merchantId === merchant.id && item.status === 'pending')
      .reduce((sum, item) => sum + Number(item.payable), 0)
    const frozen = withdrawals
      .filter((item) => item.merchantId === merchant.id && item.status === 'pending')
      .reduce((sum, item) => sum + Number(item.amount), 0)
    const available = index === 0 ? 128600 : 26000 + index * 1800
    balances[merchant.id] = {
      total: money(available + frozen + pending),
      available: money(available),
      frozen: money(frozen),
      withdrawn: '89000.00',
      pendingSettlement: money(pending)
    }
  })
  return {
    version: DB_VERSION,
    seededAt: new Date().toISOString(),
    merchants,
    stores,
    products,
    orders,
    aftersales,
    settlements,
    withdrawals,
    members,
    categories,
    origins,
    originMonths,
    announcements,
    admins,
    roles,
    logs,
    notifications,
    settlementAccounts,
    balances,
    settings: {
      platformName: '碳惠陇原',
      servicePhone: '0931-8888888',
      serviceEmail: 'service@tanhui.example.com',
      address: '甘肃省兰州市城关区',
      icp: '陇ICP备2026000001号',
      notice: '平台为演示环境，支付、物流、积分与助农金额均为仿真数据。'
    },
    commissionRate: '5.00'
  }
}

export const SEEDED_DB_VERSION = DB_VERSION
