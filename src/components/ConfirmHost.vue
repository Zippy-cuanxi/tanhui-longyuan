<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { useConfirmStore } from '@/stores/confirm'
import AppIcon from './AppIcon.vue'

const confirm = useConfirmStore()

function onKeydown(event: KeyboardEvent): void {
  if (!confirm.state.visible) return
  if (event.key === 'Escape') confirm.settle(false)
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="confirm.state.visible" class="modal-mask" @click.self="confirm.settle(false)">
        <div
          class="confirm-dialog"
          role="dialog"
          aria-modal="true"
          :aria-label="confirm.state.title"
        >
          <div class="confirm-head">
            <span class="confirm-icon" :class="{ danger: confirm.state.danger }">
              <AppIcon name="alert" :size="18" />
            </span>
            <h2>{{ confirm.state.title }}</h2>
          </div>
          <p>{{ confirm.state.message }}</p>
          <div class="confirm-actions">
            <button class="ghost-button" type="button" @click="confirm.settle(false)">
              {{ confirm.state.cancelText }}
            </button>
            <button
              class="primary-button"
              :class="{ danger: confirm.state.danger }"
              type="button"
              @click="confirm.settle(true)"
            >
              {{ confirm.state.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
