/**
 * 静态演示：管理端审核通过商品的消费者端发布区。
 *
 * GitHub Pages 没有后端，管理端使用 console mock 数据（localStorage），
 * 消费者端使用构建时快照。两者原本互不相通，导致“管理端审核通过”的商品
 * 不会出现在消费者端「全部商品」。这里用独立 localStorage 作为发布通道：
 * - 管理端审核通过 → publishDemoProduct 写入；
 * - 消费者端列表/详情 → demoAdapter 合并读取；
 * - 驳回/强制下架 → unpublishDemoProduct 移除。
 */

const STORAGE_KEY = 'tanhui_demo_published_products'

export interface DemoPublishedSku {
  id: string
  spec: string
  price: number
  code: string | null
}

export interface DemoPublishedProduct {
  id: string
  store_id: string
  store_name: string
  category_name: string
  title: string
  subtitle: string | null
  description: string
  cover_url: string | null
  min_price: number
  created_at: string
  skus: DemoPublishedSku[]
  images: Array<{ id: string; url: string; sort: number }>
  origin: string
  planting_mode: string | null
  green_description: string | null
}

/** 管理端商品（只取发布需要的字段，避免跨层依赖 console 类型）。 */
export interface PublishSource {
  id: string
  storeId: string
  storeName: string
  categoryName: string
  title: string
  subtitle: string
  description: string
  cover: string
  price: string
  images: string[]
  skus: Array<{ id: string; spec: string; price: string; code?: string }>
  greenProfile?: { origin?: string; plantingMode?: string; description?: string }
}

function readRaw(): Record<string, DemoPublishedProduct> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as Record<string, DemoPublishedProduct>
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function writeRaw(value: Record<string, DemoPublishedProduct>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  } catch {
    // 存储满或隐私模式：忽略，内存态仍可演示
  }
}

/** 读取所有已发布商品（消费者端合并展示）。 */
export function readPublishedProducts(): DemoPublishedProduct[] {
  return Object.values(readRaw())
}

/** 管理端审核通过：发布/更新到消费者端目录。 */
export function publishDemoProduct(source: PublishSource): void {
  const images = (source.images?.length ? source.images : [source.cover]).filter(Boolean)
  const record: DemoPublishedProduct = {
    id: source.id,
    store_id: source.storeId ? `demo-${source.storeId}` : 'demo-store',
    store_name: source.storeName || '甘肃产地直供',
    category_name: source.categoryName || '',
    title: source.title,
    subtitle: source.subtitle || null,
    description: source.description || '',
    cover_url: images[0] || null,
    min_price: Number(source.price) || 0,
    created_at: new Date().toISOString(),
    skus: (source.skus || []).map((sku) => ({
      id: sku.id,
      spec: sku.spec,
      price: Number(sku.price) || 0,
      code: sku.code || null
    })),
    images: images.map((url, index) => ({ id: `${source.id}-img-${index + 1}`, url, sort: index })),
    origin: source.greenProfile?.origin || '甘肃',
    planting_mode: source.greenProfile?.plantingMode || null,
    green_description: source.greenProfile?.description || null
  }
  const all = readRaw()
  all[record.id] = record
  writeRaw(all)
}

/** 驳回/下架：从消费者端目录移除。 */
export function unpublishDemoProduct(id: string): void {
  const all = readRaw()
  if (!(id in all)) return
  delete all[id]
  writeRaw(all)
}
