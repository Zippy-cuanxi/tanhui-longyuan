<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { addressApi } from '@/api'
import type { Address } from '@/api/types'
import { errorText } from '@/utils/format'
import { useConfirmStore } from '@/stores/confirm'
import { useToastStore } from '@/stores/toast'
import AddressFormModal from '@/components/AddressFormModal.vue'
import AppIcon from '@/components/AppIcon.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const confirm = useConfirmStore()
const toast = useToastStore()

const addresses = ref<Address[]>([])
const loading = ref(true)
const error = ref('')
const modalVisible = ref(false)
const editing = ref<Address | null>(null)
const fromCheckout = computed(() => route.query.from === 'checkout')

function fullAddress(address: Address): string {
  return `${address.province}${address.city}${address.district || ''}${address.detail}`
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    addresses.value = await addressApi.list()
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

function openAdd(): void {
  editing.value = null
  modalVisible.value = true
}

function openEdit(address: Address): void {
  editing.value = address
  modalVisible.value = true
}

async function onSaved(): Promise<void> {
  await load()
}

async function remove(address: Address): Promise<void> {
  const ok = await confirm.ask({
    title: '删除地址',
    message: `确认删除「${address.receiver} · ${fullAddress(address)}」吗？`,
    confirmText: '删除',
    danger: true
  })
  if (!ok) return
  try {
    await addressApi.remove(address.id)
    toast.show('收货地址已删除', 'success')
    await load()
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  }
}

onMounted(load)
</script>

<template>
  <div class="addresses-view">
    <header class="account-page-head">
      <div>
        <span class="eyebrow">ADDRESSES</span>
        <h2>收货地址</h2>
        <p>管理下单时使用的收货信息。</p>
      </div>
      <div class="head-actions">
        <RouterLink v-if="fromCheckout" to="/checkout" class="ghost-button small">
          <AppIcon name="chevron-left" :size="14" />返回结算
        </RouterLink>
        <button type="button" class="primary-button small" @click="openAdd">
          <AppIcon name="plus" :size="15" />新增地址
        </button>
      </div>
    </header>

    <StateBlock
      :loading="loading"
      :error="error"
      :empty="!loading && !error && !addresses.length"
      empty-text="还没有收货地址"
      @retry="load"
    >
      <template #empty-action>
        <button type="button" class="primary-button small" @click="openAdd">新增收货地址</button>
      </template>
      <div class="address-grid">
        <article v-for="address in addresses" :key="address.id" class="address-card">
          <header>
            <strong>{{ address.receiver }}</strong>
            <span>{{ address.phone }}</span>
            <em v-if="address.is_default">默认</em>
          </header>
          <p>{{ fullAddress(address) }}</p>
          <footer>
            <button type="button" class="ghost-button small" @click="openEdit(address)">
              <AppIcon name="edit" :size="14" />编辑
            </button>
            <button type="button" class="ghost-button small danger-text" @click="remove(address)">
              <AppIcon name="trash" :size="14" />删除
            </button>
          </footer>
        </article>
      </div>
    </StateBlock>

    <AddressFormModal
      :visible="modalVisible"
      :address="editing"
      @close="modalVisible = false"
      @saved="onSaved"
    />
  </div>
</template>
