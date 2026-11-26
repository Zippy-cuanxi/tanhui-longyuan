import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import HomeView from '../HomeView.vue'
import HomeCarousel from '@/components/HomeCarousel.vue'

vi.mock('@/api', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@/api')>()
  return {
    ...mod,
    cmsApi: {
      ...mod.cmsApi,
      config: vi.fn().mockRejectedValue(new Error('offline'))
    },
    catalogApi: {
      ...mod.catalogApi,
      categories: vi.fn().mockResolvedValue([]),
      products: vi.fn().mockResolvedValue({ items: [] })
    }
  }
})

vi.mock('@/composables/useCatalogLive', () => ({
  useCatalogLive: vi.fn()
}))

async function mountHome() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/products', component: { template: '<div />' } },
      { path: '/origin', component: { template: '<div />' } },
      { path: '/green', component: { template: '<div />' } },
      { path: '/aid', component: { template: '<div />' } },
      { path: '/join', component: { template: '<div />' } },
      { path: '/coupons', component: { template: '<div />' } },
      { path: '/account/points', component: { template: '<div />' } }
    ]
  })
  await router.push('/')
  await router.isReady()

  const wrapper = mount(HomeView, {
    global: {
      plugins: [router],
      stubs: {
        HomeOriginMap: true,
        ProductGridSection: true,
        ProductCard: true,
        StateBlock: true,
        CmsSectionRenderer: true
      }
    }
  })
  await flushPromises()
  return wrapper
}

describe('HomeView 轮播配置', () => {
  it('轮播数据包含跳转到商家入驻页的新图片', async () => {
    const wrapper = await mountHome()

    const slides = wrapper.findComponent(HomeCarousel).props('slides') as Array<{
      key: string
      label: string
      image: string
      to: string
      alt: string
    }>

    expect(slides).toHaveLength(5)
    const joinSlide = slides[slides.length - 1]
    expect(joinSlide).toMatchObject({
      key: 'join',
      label: '商家入驻',
      to: '/join'
    })
    expect(joinSlide.image).toMatch(/\/images\/banners\/join\.webp$/)
    expect(joinSlide.alt).toContain('商家入驻')

    wrapper.unmount()
  })
})
