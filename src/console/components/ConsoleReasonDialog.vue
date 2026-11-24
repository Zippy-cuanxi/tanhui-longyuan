<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    visible: boolean
    title: string
    label?: string
    placeholder?: string
    minLength?: number
    quickReasons?: string[]
    loading?: boolean
    danger?: boolean
  }>(),
  {
    label: '原因',
    placeholder: '请输入原因（至少 2 个字）',
    minLength: 2,
    quickReasons: () => [],
    loading: false,
    danger: false
  }
)
const emit = defineEmits<{
  'update:visible': [value: boolean]
  confirm: [reason: string]
}>()

const reason = ref('')
const error = ref('')

watch(
  () => props.visible,
  (value) => {
    if (value) {
      reason.value = ''
      error.value = ''
    }
  }
)

function choose(value: string): void {
  reason.value = value
  error.value = ''
}

function submit(): void {
  const text = reason.value.trim()
  if (text.length < props.minLength) {
    error.value = `请填写至少 ${props.minLength} 个字的${props.label}`
    return
  }
  emit('confirm', text)
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="480px"
    append-to-body
    :close-on-click-modal="!loading"
    :close-on-press-escape="!loading"
    @update:model-value="(value: boolean) => emit('update:visible', value)"
  >
    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item :label="label" :error="error">
        <el-input
          v-model="reason"
          type="textarea"
          :rows="4"
          maxlength="255"
          show-word-limit
          :placeholder="placeholder"
        />
        <div v-if="quickReasons.length" class="console-reason-quick">
          <button v-for="item in quickReasons" :key="item" type="button" @click="choose(item)">
            {{ item }}
          </button>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="console-inline-actions" style="justify-content: flex-end">
        <el-button :disabled="loading" @click="emit('update:visible', false)">取消</el-button>
        <el-button :type="danger ? 'danger' : 'primary'" :loading="loading" @click="submit">
          确认
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>
