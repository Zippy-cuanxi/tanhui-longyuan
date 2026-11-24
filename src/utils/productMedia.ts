import { assetUrl } from '@/api/http'
import type { Product } from '@/api/types'
import { productFallbackImage } from './format'

export interface DishInfo {
  image: string
  name: string
  description: string
}

const DISHES: Array<{ match: RegExp; dish: DishInfo }> = [
  {
    match: /马铃薯|土豆/,
    dish: {
      image: assetUrl('/images/dishes/potato-beef.webp'),
      name: '土豆炖牛腩',
      description: '定西马铃薯切块与牛腩同炖，粉糯入味，适合家庭炖菜。'
    }
  },
  {
    match: /小枣|枣/,
    dish: {
      image: assetUrl('/images/dishes/jujube-walnut.webp'),
      name: '枣夹核桃',
      description: '临泽小枣去核夹入核桃仁，枣香与坚果香搭配，适合作为茶点。'
    }
  },
  {
    match: /枸杞/,
    dish: {
      image: assetUrl('/images/dishes/goji-soup.webp'),
      name: '枸杞银耳羹',
      description: '甘肃枸杞搭配银耳慢炖，清甜润口，适合作为日常甜品。'
    }
  },
  {
    match: /百合/,
    dish: {
      image: assetUrl('/images/dishes/lily-stirfry.webp'),
      name: '西芹炒百合',
      description: '兰州百合与西芹清炒，口感清甜脆嫩，适合家常小炒。'
    }
  }
]

export function dishInfoForProduct(title?: string | null): DishInfo | null {
  const text = title || ''
  return DISHES.find((entry) => entry.match.test(text))?.dish || null
}

/** 商品主图（全部商品、产地列表、详情主图、首页卡片等）。 */
export function productMainImage(product: Partial<Product>): string {
  return assetUrl(product.cover_url, productFallbackImage(product.title))
}
