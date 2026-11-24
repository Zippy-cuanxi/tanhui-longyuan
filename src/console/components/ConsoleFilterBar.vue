<script setup lang="ts">
withDefaults(defineProps<{ loading?: boolean }>(), { loading: false })
const emit = defineEmits<{ search: []; reset: [] }>()
</script>

<template>
  <section class="console-filter">
    <el-form inline @submit.prevent="emit('search')">
      <slot />
      <el-form-item>
        <div class="console-filter-actions">
          <el-button type="primary" native-type="submit" :loading="loading">
            <el-icon><Search /></el-icon>查询
          </el-button>
          <el-button @click="emit('reset')">
            <el-icon><RefreshLeft /></el-icon>重置
          </el-button>
          <slot name="actions" />
        </div>
      </el-form-item>
    </el-form>
  </section>
</template>
