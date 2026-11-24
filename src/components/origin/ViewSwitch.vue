<script setup lang="ts">
// 3D / 2D 视图切换：分段按钮
defineProps<{ view: '3d' | '2d' }>()
const emit = defineEmits<{ change: [view: '3d' | '2d'] }>()
</script>

<template>
  <div class="view-switch" role="group" aria-label="地图视图切换">
    <button
      type="button"
      :class="{ active: view === '3d' }"
      :aria-pressed="view === '3d'"
      @click="emit('change', '3d')"
    >
      3D
    </button>
    <button
      type="button"
      :class="{ active: view === '2d' }"
      :aria-pressed="view === '2d'"
      @click="emit('change', '2d')"
    >
      2D
    </button>
  </div>
</template>
