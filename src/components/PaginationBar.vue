<script setup lang="ts">
import { computed } from 'vue'
import type { Pagination } from '@/api/types'
import AppIcon from './AppIcon.vue'

const props = defineProps<{ pagination: Pagination }>()
const emit = defineEmits<{ change: [page: number] }>()

const pages = computed(() => {
  const total = props.pagination.total_pages
  const current = props.pagination.page
  if (total <= 1) return []
  const start = Math.max(1, Math.min(current - 2, total - 4))
  const length = Math.min(5, total)
  return Array.from({ length }, (_, index) => start + index)
})

function go(page: number): void {
  if (page < 1 || page > props.pagination.total_pages || page === props.pagination.page) return
  emit('change', page)
}
</script>

<template>
  <nav v-if="pagination.total_pages > 1" class="pagination" aria-label="分页">
    <button
      type="button"
      aria-label="上一页"
      :disabled="pagination.page <= 1"
      @click="go(pagination.page - 1)"
    >
      <AppIcon name="chevron-left" :size="16" />
    </button>
    <button
      v-for="page in pages"
      :key="page"
      type="button"
      :class="{ active: page === pagination.page }"
      :aria-current="page === pagination.page ? 'page' : undefined"
      :aria-label="`第 ${page} 页`"
      @click="go(page)"
    >
      {{ page }}
    </button>
    <button
      type="button"
      aria-label="下一页"
      :disabled="pagination.page >= pagination.total_pages"
      @click="go(pagination.page + 1)"
    >
      <AppIcon name="chevron-right" :size="16" />
    </button>
    <span class="pagination-total">共 {{ pagination.total }} 件</span>
  </nav>
</template>
