<script setup lang="ts">
import { computed } from 'vue'
import {
  AFTERSALE_STATUS,
  ANNOUNCEMENT_STATUS,
  MEMBER_STATUS,
  MERCHANT_STATUS,
  ORDER_STATUS,
  PRODUCT_STATUS,
  RISK_LEVEL,
  SETTLEMENT_STATUS,
  STORE_STATUS,
  WITHDRAWAL_STATUS,
  statusMeta
} from '@/console/constants/labels'

type StatusKind =
  | 'merchant'
  | 'product'
  | 'order'
  | 'aftersale'
  | 'settlement'
  | 'withdrawal'
  | 'announcement'
  | 'member'
  | 'store'
  | 'risk'

const props = defineProps<{ kind: StatusKind; value?: string | null }>()

const dictionaries: Record<StatusKind, Record<string, ReturnType<typeof statusMeta>>> = {
  merchant: MERCHANT_STATUS,
  product: PRODUCT_STATUS,
  order: ORDER_STATUS,
  aftersale: AFTERSALE_STATUS,
  settlement: SETTLEMENT_STATUS,
  withdrawal: WITHDRAWAL_STATUS,
  announcement: ANNOUNCEMENT_STATUS,
  member: MEMBER_STATUS,
  store: STORE_STATUS,
  risk: RISK_LEVEL
}

const meta = computed(() => statusMeta(dictionaries[props.kind], props.value))
</script>

<template>
  <span class="console-status" :style="{ color: meta.color, background: meta.bg }">
    <i />{{ meta.label }}
  </span>
</template>
