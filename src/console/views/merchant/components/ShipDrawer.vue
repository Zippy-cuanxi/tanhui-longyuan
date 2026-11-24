<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import ConsoleDetailDrawer from '@/console/components/ConsoleDetailDrawer.vue'
import ConsoleMasked from '@/console/components/ConsoleMasked.vue'
import { merchantApi, type Order } from '@/console/api'
import { SHIPPING_CARRIERS } from '@/console/constants/labels'
import { useConsoleAuth } from '@/console/stores/auth'
import { toErrorState } from '@/console/utils/errors'

const props = defineProps<{
  modelValue: boolean
  order: Order | null
}>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  shipped: [order: Order]
}>()

const auth = useConsoleAuth()
const form = reactive({ carrier: SHIPPING_CARRIERS[0], trackingNo: '' })
const submitting = ref(false)
const error = ref('')

const merchantId = computed(() => auth.merchantAccount?.id || '')
const canShip = computed(() => props.order?.status === 'paid')

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      form.carrier = SHIPPING_CARRIERS[0]
      form.trackingNo = ''
      error.value = ''
    }
  }
)

function close(): void {
  emit('update:modelValue', false)
}

async function submit(): Promise<void> {
  if (!props.order || submitting.value) return
  error.value = ''
  if (!form.carrier) {
    error.value = '请选择快递公司'
    return
  }
  const tracking = form.trackingNo.trim()
  if (!/^[A-Za-z0-9-]{6,32}$/.test(tracking)) {
    error.value = '快递单号需为 6–32 位字母、数字或短横线'
    return
  }
  submitting.value = true
  try {
    const order = await merchantApi.shipOrder(
      merchantId.value,
      props.order.id,
      form.carrier,
      tracking
    )
    ElMessage.success('发货成功，订单状态已更新为「待收货」')
    emit('shipped', order)
    close()
  } catch (err) {
    error.value = toErrorState(err, '发货失败，请稍后重试').message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <ConsoleDetailDrawer
    :model-value="modelValue"
    title="订单发货"
    size="560px"
    @update:model-value="(value: boolean) => emit('update:modelValue', value)"
  >
    <template v-if="order">
      <div v-if="!canShip" class="console-login-error">
        当前订单状态为「{{ order.status }}」，仅待发货订单可执行发货。
      </div>
      <div class="console-summary-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr))">
        <div class="console-summary-item">
          <span>订单号</span>
          <strong style="font-size: 14px">{{ order.orderNo }}</strong>
        </div>
        <div class="console-summary-item">
          <span>应付金额</span>
          <strong class="amount" style="font-size: 18px">¥{{ order.payAmount }}</strong>
        </div>
        <div class="console-summary-item">
          <span>收货人</span>
          <strong style="font-size: 13px">{{ order.buyerName }}</strong>
        </div>
        <div class="console-summary-item">
          <span>联系电话</span>
          <strong style="font-size: 13px">
            <ConsoleMasked :value="order.buyerPhone" kind="phone" />
          </strong>
        </div>
      </div>

      <div class="console-detail-section" style="margin-top: 18px">
        <h4>收货信息</h4>
        <div class="console-detail-field">
          <label>收货地址</label>
          <span><ConsoleMasked :value="order.address" kind="address" /></span>
        </div>
        <div class="console-detail-field">
          <label>商品件数</label>
          <span>{{ order.items.reduce((sum, item) => sum + item.quantity, 0) }} 件</span>
        </div>
        <div v-if="order.remark" class="console-detail-field">
          <label>买家备注</label>
          <span>{{ order.remark }}</span>
        </div>
      </div>

      <div class="console-detail-section" style="margin-top: 18px">
        <h4>填写物流信息 <span>必填</span></h4>
        <el-form label-position="top" :disabled="submitting || !canShip">
          <el-form-item label="快递公司" required>
            <el-select v-model="form.carrier" style="width: 100%">
              <el-option
                v-for="carrier in SHIPPING_CARRIERS"
                :key="carrier"
                :label="carrier"
                :value="carrier"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="快递单号" required>
            <el-input
              v-model="form.trackingNo"
              maxlength="32"
              placeholder="请输入 6–32 位字母、数字或短横线"
              @keyup.enter="submit"
            />
          </el-form-item>
        </el-form>
        <p class="console-muted" style="font-size: 11px">
          仿真环境：发货后订单状态变为「待收货」，物流轨迹为本地演示数据。
        </p>
        <p v-if="error" class="console-login-error">{{ error }}</p>
      </div>
    </template>

    <template #footer>
      <el-button :disabled="submitting" @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!canShip" @click="submit">
        确认发货
      </el-button>
    </template>
  </ConsoleDetailDrawer>
</template>
