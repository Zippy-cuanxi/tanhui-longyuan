import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import HomeCarousel from '../HomeCarousel.vue'

const slides = [
  {
    key: 'catalog',
    label: '全部商品',
    image: '/images/banners/home-main-visual.webp',
    to: '/products',
    alt: '全部商品'
  },
  {
    key: 'green',
    label: '绿色消费区',
    image: '/images/banners/green.webp',
    to: '/green',
    alt: '绿色消费区'
  },
  {
    key: 'join',
    label: '商家入驻',
    image: '/images/banners/join.webp',
    to: '/join',
    alt: '商家入驻——产地直供、平台赋能、共赢陇原'
  }
]

async function createTestRouter(): Promise<Router> {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/products', component: { template: '<div />' } },
      { path: '/green', component: { template: '<div />' } },
      { path: '/join', component: { template: '<div />' } }
    ]
  })
  await router.push('/')
  await router.isReady()
  return router
}

async function mountCarousel(interval = 5000) {
  const router = await createTestRouter()
  const wrapper = mount(HomeCarousel, {
    props: { slides, interval },
    global: { plugins: [router] }
  })
  return { wrapper, router }
}

function currentCount(wrapper: VueWrapper): string {
  return wrapper.find('.home-carousel-count').text()
}

describe('HomeCarousel', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('把每张图片渲染为可点击的栏目链接，并包含商家入驻入口', async () => {
    const { wrapper } = await mountCarousel()

    const links = wrapper.findAll('.home-carousel-slide')
    expect(links).toHaveLength(slides.length)
    expect(wrapper.findAll('.home-carousel-dots button')).toHaveLength(slides.length)

    const joinLink = links[2]
    expect(joinLink.attributes('href')).toBe('/join')
    expect(joinLink.find('img').attributes('src')).toBe('/images/banners/join.webp')
    expect(joinLink.find('img').attributes('alt')).toContain('商家入驻')

    expect(links[0].classes()).toContain('active')
    expect(currentCount(wrapper)).toBe('1 / 3')

    wrapper.unmount()
  })

  it('每 5 秒自动切换到下一张，并在最后一张后回到第一张', async () => {
    const { wrapper } = await mountCarousel()

    await vi.advanceTimersByTimeAsync(5000)
    expect(currentCount(wrapper)).toBe('2 / 3')
    expect(wrapper.findAll('.home-carousel-slide')[1].classes()).toContain('active')

    await vi.advanceTimersByTimeAsync(5000)
    expect(currentCount(wrapper)).toBe('3 / 3')

    await vi.advanceTimersByTimeAsync(5000)
    expect(currentCount(wrapper)).toBe('1 / 3')

    wrapper.unmount()
  })

  it('鼠标悬停时暂停自动播放，移出后按剩余时间恢复', async () => {
    const { wrapper } = await mountCarousel()

    await wrapper.find('.home-carousel').trigger('mouseenter')
    await vi.advanceTimersByTimeAsync(15000)
    expect(currentCount(wrapper)).toBe('1 / 3')

    await wrapper.find('.home-carousel').trigger('mouseleave')
    await vi.advanceTimersByTimeAsync(5000)
    expect(currentCount(wrapper)).toBe('2 / 3')

    wrapper.unmount()
  })

  it('点击指示点或左右箭头可以手动切换', async () => {
    const { wrapper } = await mountCarousel()

    await wrapper.findAll('.home-carousel-dots button')[2].trigger('click')
    expect(currentCount(wrapper)).toBe('3 / 3')

    await wrapper.find('.home-carousel-arrow.next').trigger('click')
    expect(currentCount(wrapper)).toBe('1 / 3')

    await wrapper.find('.home-carousel-arrow.prev').trigger('click')
    expect(currentCount(wrapper)).toBe('3 / 3')

    wrapper.unmount()
  })

  it('点击商家入驻图片跳转到 /join', async () => {
    const { wrapper, router } = await mountCarousel()

    await wrapper.findAll('.home-carousel-slide')[2].trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/join')

    wrapper.unmount()
  })
})
