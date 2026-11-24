<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { addressApi } from '@/api'
import type { Address, AddressInput } from '@/api/types'
import { errorText } from '@/utils/format'
import { useToastStore } from '@/stores/toast'
import AppIcon from './AppIcon.vue'

const props = defineProps<{
  visible: boolean
  address?: Address | null
}>()

const emit = defineEmits<{ close: []; saved: [address: Address] }>()

const toast = useToastStore()
const saving = ref(false)
const error = ref('')
const form = reactive<AddressInput>({
  receiver: '',
  phone: '',
  province: '甘肃省',
  city: '',
  district: '',
  detail: '',
  is_default: false
})

function reset(): void {
  const source = props.address
  form.receiver = source?.receiver || ''
  form.phone = source?.phone || ''
  form.province = source?.province || '甘肃省'
  form.city = source?.city || ''
  form.district = source?.district || ''
  form.detail = source?.detail || ''
  form.is_default = source?.is_default || false
  error.value = ''
}

watch(
  () => [props.visible, props.address] as const,
  () => {
    if (props.visible) reset()
  },
  { immediate: true }
)

function validate(): string {
  if (!form.receiver.trim()) return '请填写收货人姓名'
  if (!/^[0-9+\-\s]{6,20}$/.test(form.phone.trim())) return '请填写有效的联系电话'
  if (!form.province.trim()) return '请填写省份'
  if (!form.city.trim()) return '请填写城市'
  if (!form.detail.trim()) return '请填写详细地址'
  return ''
}

async function submit(): Promise<void> {
  error.value = validate()
  if (error.value) return
  saving.value = true
  try {
    const payload: AddressInput = {
      ...form,
      receiver: form.receiver.trim(),
      phone: form.phone.trim(),
      province: form.province.trim(),
      city: form.city.trim(),
      district: form.district?.trim() || null,
      detail: form.detail.trim()
    }
    const saved = props.address
      ? await addressApi.update(props.address.id, payload)
      : await addressApi.create(payload)
    toast.show(props.address ? '收货地址已更新' : '收货地址已新增', 'success')
    emit('saved', saved)
    emit('close')
  } catch (err) {
    error.value = errorText(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-mask" @click.self="emit('close')">
        <div class="modal-card address-modal" role="dialog" aria-modal="true" aria-label="收货地址">
          <header class="modal-card-head">
            <div>
              <span class="eyebrow">SHIPPING ADDRESS</span>
              <h2>{{ address ? '编辑收货地址' : '新增收货地址' }}</h2>
            </div>
            <button type="button" class="icon-button" aria-label="关闭" @click="emit('close')">
              <AppIcon name="close" :size="18" />
            </button>
          </header>

          <form class="form-grid" @submit.prevent="submit">
            <label class="field">
              <span>收货人</span>
              <input v-model="form.receiver" maxlength="64" placeholder="请填写收货人姓名" />
            </label>
            <label class="field">
              <span>联系电话</span>
              <input
                v-model="form.phone"
                maxlength="32"
                placeholder="如 13800001234"
                inputmode="tel"
              />
            </label>
            <label class="field">
              <span>省份</span>
              <input
                v-model="form.province"
                maxlength="32"
                placeholder="甘肃省"
                list="province-list"
              />
              <datalist id="province-list">
                <option value="甘肃省" />
                <option value="陕西省" />
                <option value="青海省" />
                <option value="宁夏回族自治区" />
                <option value="新疆维吾尔自治区" />
              </datalist>
            </label>
            <label class="field">
              <span>城市</span>
              <input v-model="form.city" maxlength="32" placeholder="如 兰州市" list="city-list" />
              <datalist id="city-list">
                <option value="兰州市" />
                <option value="定西市" />
                <option value="平凉市" />
                <option value="武威市" />
                <option value="张掖市" />
                <option value="天水市" />
                <option value="陇南市" />
              </datalist>
            </label>
            <label class="field">
              <span>区 / 县</span>
              <input v-model="form.district" maxlength="32" placeholder="如 城关区" />
            </label>
            <label class="field field-wide">
              <span>详细地址</span>
              <input v-model="form.detail" maxlength="255" placeholder="街道、门牌号、楼栋单元等" />
            </label>
            <label class="check-row field-wide">
              <input v-model="form.is_default" type="checkbox" />
              <span>设为默认收货地址</span>
            </label>

            <p v-if="error" class="form-error field-wide">{{ error }}</p>

            <div class="modal-actions field-wide">
              <button type="button" class="ghost-button" @click="emit('close')">取消</button>
              <button type="submit" class="primary-button" :disabled="saving">
                <span v-if="saving" class="mini-spinner" />
                {{ saving ? '保存中…' : '保存地址' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
