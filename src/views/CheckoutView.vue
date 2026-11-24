<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { addressApi, cartApi, orderApi, pointsApi } from '@/api'
import { assetUrl } from '@/api/http'
import type { Address, OrderItemInput, Preview } from '@/api/types'
import { errorText, money, productFallbackImage } from '@/utils/format'
import { useCartStore } from '@/stores/cart'
import { useCheckoutStore } from '@/stores/checkout'
import { useToastStore } from '@/stores/toast'
import AppIcon from '@/components/AppIcon.vue'
import AddressFormModal from '@/components/AddressFormModal.vue'
import StateBlock from '@/components/StateBlock.vue'

const router = useRouter()
const cart = useCartStore()
const checkout = useCheckoutStore()
const toast = useToastStore()

const addresses = ref<Address[]>([])
const selectedAddressId = ref('')
const addressLoading = ref(true)
const addressError = ref('')
const addressModal = ref(false)
const editingAddress = ref<Address | null>(null)

const pointsBalance = ref<number | null>(null)
const usePoints = ref(false)
const preview = ref<Preview | null>(null)
const previewLoading = ref(false)
const previewError = ref('')
const remark = ref('')
const submitting = ref(false)
const submitError = ref('')

const directMode = computed(() => Boolean(checkout.directItems?.length))
const orderItems = computed<OrderItemInput[]>(() => {
  if (checkout.directItems?.length) {
    return checkout.directItems.map((item) => ({
      sku_id: item.sku_id,
      quantity: item.quantity,
      expected_unit_price: item.expected_unit_price
    }))
  }
  return cart.checkedItems.map((item) => ({
    sku_id: item.sku_id,
    quantity: item.quantity,
    expected_unit_price: item.current_price
  }))
})
const totalQuantity = computed(() => orderItems.value.reduce((sum, item) => sum + item.quantity, 0))
const selectedAddress = computed(
  () => addresses.value.find((address) => address.id === selectedAddressId.value) || null
)
const imageMap = computed(() => {
  const map = new Map<string, string>()
  cart.items.forEach((item) => {
    map.set(item.sku_id, assetUrl(item.image_url, productFallbackImage(item.product_title)))
  })
  checkout.directItems?.forEach((item) => {
    map.set(item.sku_id, assetUrl(item.image_url, productFallbackImage(item.title)))
  })
  return map
})
const canSubmit = computed(() =>
  Boolean(preview.value && selectedAddress.value && orderItems.value.length && !submitting.value)
)

function fullAddress(address: Address): string {
  return `${address.province}${address.city}${address.district || ''}${address.detail}`
}

async function loadAddresses(): Promise<void> {
  addressLoading.value = true
  addressError.value = ''
  try {
    addresses.value = await addressApi.list()
    const preferred = addresses.value.find((address) => address.is_default) || addresses.value[0]
    selectedAddressId.value = preferred?.id || ''
  } catch (err) {
    addressError.value = errorText(err)
  } finally {
    addressLoading.value = false
  }
}

async function loadPoints(): Promise<void> {
  try {
    const account = await pointsApi.account()
    pointsBalance.value = account.balance
    if (account.balance <= 0) usePoints.value = false
  } catch {
    pointsBalance.value = null
  }
}

async function refreshPreview(): Promise<void> {
  if (!orderItems.value.length) return
  previewLoading.value = true
  previewError.value = ''
  try {
    preview.value = await orderApi.preview({
      items: orderItems.value,
      use_points: usePoints.value,
      address_id: selectedAddressId.value || null
    })
  } catch (err) {
    previewError.value = errorText(err)
    preview.value = null
  } finally {
    previewLoading.value = false
  }
}

function itemsWithPreviewPrices(): OrderItemInput[] {
  const priceMap = new Map<string, string>()
  preview.value?.stores.forEach((store) => {
    store.items.forEach((item) => {
      priceMap.set(item.sku_id, item.unit_price)
    })
  })
  return orderItems.value.map((item) => ({
    ...item,
    expected_unit_price: priceMap.get(item.sku_id) || item.expected_unit_price || null
  }))
}

function openAddAddress(): void {
  editingAddress.value = null
  addressModal.value = true
}

function openEditAddress(address: Address): void {
  editingAddress.value = address
  addressModal.value = true
}

async function onAddressSaved(address: Address): Promise<void> {
  await loadAddresses()
  selectedAddressId.value = address.id
}

function makeIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `order-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function submit(): Promise<void> {
  if (submitting.value) return
  submitError.value = ''
  if (!selectedAddress.value) {
    submitError.value = '请先选择收货地址'
    return
  }
  if (!preview.value) {
    submitError.value = '订单金额尚未计算完成，请稍后重试'
    return
  }
  submitting.value = true
  const orderedCartItemIds = directMode.value ? [] : cart.checkedItems.map((item) => item.id)
  try {
    const order = await orderApi.create({
      address_id: selectedAddress.value.id,
      items: itemsWithPreviewPrices(),
      use_points: usePoints.value,
      remark: remark.value.trim() || null,
      idempotency_key: makeIdempotencyKey()
    })
    checkout.clearDirect()
    try {
      if (orderedCartItemIds.length) {
        await Promise.all(orderedCartItemIds.map((itemId) => cartApi.remove(itemId)))
      }
      await cart.fetchCart()
    } catch {
      // 订单已创建，购物车清理失败不阻断支付
    }
    toast.show('订单已创建，请完成支付', 'success')
    router.push({ name: 'payment', params: { orderId: order.id } })
  } catch (err) {
    const code = (err as { code?: string }).code
    submitError.value = errorText(err)
    if (code === 'PRICE_CHANGED' || code === 'INSUFFICIENT_STOCK') {
      await refreshPreview()
    }
  } finally {
    submitting.value = false
  }
}

watch(usePoints, () => {
  refreshPreview()
})

onMounted(async () => {
  if (!directMode.value) {
    try {
      await cart.fetchCart()
    } catch {
      // 错误在下文状态中展示
    }
  }
  if (!orderItems.value.length) {
    toast.show('请先在购物车勾选商品', 'warning')
    router.replace({ name: 'cart' })
    return
  }
  await Promise.all([loadAddresses(), loadPoints()])
  await refreshPreview()
})
</script>

<template>
  <main class="page-main checkout-page">
    <div class="page-container">
      <header class="page-heading">
        <div>
          <span class="eyebrow">CHECKOUT</span>
          <h1>确认订单</h1>
          <p>{{ directMode ? '立即购买商品' : '购物车已选商品' }} · 共 {{ totalQuantity }} 件</p>
        </div>
        <RouterLink :to="directMode ? '/products' : '/cart'" class="outline-button small">
          <AppIcon name="chevron-left" :size="15" />返回
        </RouterLink>
      </header>

      <div class="checkout-layout">
        <div class="checkout-main">
          <section class="checkout-card">
            <header class="checkout-card-head">
              <div>
                <span class="eyebrow">SHIPPING</span>
                <h2>收货地址</h2>
              </div>
              <button type="button" class="outline-button small" @click="openAddAddress">
                <AppIcon name="plus" :size="14" />新增地址
              </button>
            </header>
            <StateBlock
              :loading="addressLoading"
              :error="addressError"
              :empty="!addressLoading && !addressError && !addresses.length"
              empty-text="还没有收货地址，请先新增"
              compact
              @retry="loadAddresses"
            >
              <template #empty-action>
                <button type="button" class="primary-button small" @click="openAddAddress">
                  新增收货地址
                </button>
              </template>
            </StateBlock>
            <div v-if="addresses.length" class="address-options">
              <label
                v-for="address in addresses"
                :key="address.id"
                class="address-option"
                :class="{ active: selectedAddressId === address.id }"
              >
                <input
                  v-model="selectedAddressId"
                  type="radio"
                  :value="address.id"
                  name="address"
                />
                <span class="address-option-body">
                  <span class="address-option-top">
                    <strong>{{ address.receiver }}</strong>
                    <span>{{ address.phone }}</span>
                    <em v-if="address.is_default">默认</em>
                  </span>
                  <span class="address-option-text">{{ fullAddress(address) }}</span>
                </span>
                <button
                  type="button"
                  class="icon-button small"
                  aria-label="编辑地址"
                  @click.prevent.stop="openEditAddress(address)"
                >
                  <AppIcon name="edit" :size="15" />
                </button>
              </label>
            </div>
          </section>

          <section class="checkout-card">
            <header class="checkout-card-head">
              <div>
                <span class="eyebrow">ITEMS</span>
                <h2>商品清单</h2>
              </div>
              <span class="muted-text">价格由服务端计算</span>
            </header>
            <StateBlock
              :loading="previewLoading"
              :error="previewError"
              empty-text="暂无可结算商品"
              :empty="!previewLoading && !previewError && !preview"
              compact
              @retry="refreshPreview"
            >
              <div v-if="preview" class="checkout-stores">
                <article
                  v-for="store in preview.stores"
                  :key="store.store_id"
                  class="checkout-store"
                >
                  <header>
                    <span class="store-mark"><AppIcon name="location" :size="14" /></span>
                    <strong>{{ store.store_name }}</strong>
                    <span class="muted-text">运费 ¥{{ money(store.shipping_fee) }}</span>
                  </header>
                  <ul>
                    <li v-for="item in store.items" :key="`${store.store_id}-${item.sku_id}`">
                      <img
                        :src="imageMap.get(item.sku_id) || productFallbackImage(item.title)"
                        :alt="item.title"
                      />
                      <div>
                        <strong>{{ item.title }}</strong>
                        <span>{{ item.spec }}</span>
                      </div>
                      <span class="checkout-item-price"
                        >¥{{ money(item.unit_price) }} × {{ item.quantity }}</span
                      >
                      <strong class="checkout-item-subtotal">¥{{ money(item.subtotal) }}</strong>
                    </li>
                  </ul>
                </article>
              </div>
            </StateBlock>
          </section>

          <section class="checkout-card">
            <header class="checkout-card-head">
              <div>
                <span class="eyebrow">POINTS</span>
                <h2>绿色积分</h2>
              </div>
              <span class="muted-text"
                >当前 {{ pointsBalance === null ? '—' : pointsBalance }} 绿色积分</span
              >
            </header>
            <label class="check-row points-toggle" :class="{ disabled: !pointsBalance }">
              <input v-model="usePoints" type="checkbox" :disabled="!pointsBalance" />
              <span>使用绿色积分抵扣</span>
            </label>
            <p class="muted-text">
              积分抵扣比例与上限以平台配置为准，实际抵扣金额由服务端预览计算。
            </p>
          </section>

          <section class="checkout-card">
            <header class="checkout-card-head">
              <div>
                <span class="eyebrow">REMARK</span>
                <h2>订单备注</h2>
              </div>
              <span class="muted-text">{{ remark.length }}/255</span>
            </header>
            <textarea
              v-model="remark"
              maxlength="255"
              rows="3"
              placeholder="选填，可填写配送时间、包装等备注"
            />
          </section>
        </div>

        <aside class="checkout-summary">
          <span class="eyebrow">PAYMENT SUMMARY</span>
          <h2>金额明细</h2>
          <dl>
            <div>
              <dt>商品金额</dt>
              <dd>¥{{ money(preview?.items_total) }}</dd>
            </div>
            <div>
              <dt>运费</dt>
              <dd>¥{{ money(preview?.shipping_fee) }}</dd>
            </div>
            <div v-if="preview && preview.points_deduct !== '0.00'" class="deduct-row">
              <dt>
                积分抵扣 <small>({{ preview.points_used }} 绿色积分)</small>
              </dt>
              <dd>-¥{{ money(preview.points_deduct) }}</dd>
            </div>
            <div class="total-row">
              <dt>应付金额</dt>
              <dd>¥{{ money(preview?.pay_amount) }}</dd>
            </div>
          </dl>
          <p class="summary-note">提交后进入沙箱支付流程；支付成功与否以服务端支付单状态为准。</p>
          <p v-if="submitError" class="form-error">{{ submitError }}</p>
          <button
            class="primary-button full-button"
            type="button"
            :disabled="!canSubmit"
            @click="submit"
          >
            <span v-if="submitting" class="mini-spinner" />
            {{ submitting ? '提交中…' : `提交订单 · ¥${money(preview?.pay_amount)}` }}
          </button>
          <button
            v-if="previewError"
            class="ghost-button full-button"
            type="button"
            @click="refreshPreview"
          >
            <AppIcon name="refresh" :size="15" />重新计价
          </button>
          <p class="summary-terms">
            提交订单即表示同意平台交易规则；价格、库存与优惠以服务端最终校验为准。
          </p>
        </aside>
      </div>
    </div>

    <AddressFormModal
      :visible="addressModal"
      :address="editingAddress"
      @close="addressModal = false"
      @saved="onAddressSaved"
    />
  </main>
</template>
