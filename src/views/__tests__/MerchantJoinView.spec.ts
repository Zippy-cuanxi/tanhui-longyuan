import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import MerchantJoinView from '../MerchantJoinView.vue'
import { useToastStore } from '@/stores/toast'

vi.mock('@/api', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@/api')>()
  return {
    ...mod,
    merchantApi: {
      ...mod.merchantApi,
      apply: vi.fn().mockResolvedValue(undefined)
    }
  }
})

async function createTestRouter(): Promise<Router> {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/join', component: { template: '<div />' } },
      { path: '/help', component: { template: '<div />' } },
      { path: '/console/login', component: { template: '<div />' } },
      { path: '/console/admin/products/review', component: { template: '<div />' } }
    ]
  })
  await router.push('/join')
  await router.isReady()
  return router
}

async function mountJoinPage() {
  const router = await createTestRouter()
  const wrapper = (await mount(MerchantJoinView, {
    global: { plugins: [router] }
  })) as VueWrapper
  return { wrapper, router }
}

describe('MerchantJoinView 右侧入口', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('在帮助中心下方渲染“商品审核后台”入口', async () => {
    const { wrapper } = await mountJoinPage()

    const sideCards = wrapper.findAll('.join-side > *')
    expect(sideCards).toHaveLength(3)

    const entry = sideCards[2]
    expect(entry.classes()).toContain('join-console-entry')
    expect(entry.text()).toContain('商品审核后台')
    expect(entry.text()).toContain('管理员登录后进入待审商品列表')

    wrapper.unmount()
  })

  it('入口指向带 redirect 参数的管理员登录地址', async () => {
    const { wrapper } = await mountJoinPage()

    const entry = wrapper.find('.join-console-entry')
    expect(entry.attributes('href')).toBe('/console/login?redirect=/console/admin/products/review')

    wrapper.unmount()
  })

  it('点击入口后进入管理员登录页并保留 redirect 参数', async () => {
    const { wrapper, router } = await mountJoinPage()

    await wrapper.find('.join-console-entry').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/console/login')
    expect(router.currentRoute.value.query.redirect).toBe('/console/admin/products/review')

    wrapper.unmount()
  })

  it('未勾选协议提交时只提示，不调用入驻接口', async () => {
    const { wrapper } = await mountJoinPage()
    const toast = useToastStore()
    const { merchantApi } = await import('@/api')

    await wrapper.find('.join-submit').trigger('click')

    expect(toast.message).toContain('请先阅读并同意')
    expect(merchantApi.apply).not.toHaveBeenCalled()

    wrapper.unmount()
  })
})
