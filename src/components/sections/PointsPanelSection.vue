<script setup lang="ts">
import { asString } from '@/utils/cms'
import { pointsCopy } from '@/utils/format'
import AppIcon from '../AppIcon.vue'

const props = defineProps<{ config: Record<string, unknown> }>()
const title = pointsCopy(asString(props.config.title, '绿色积分'))
const description = pointsCopy(asString(props.config.description, '每一次绿色消费，都值得被记录。'))
</script>

<template>
  <section class="cms-points-panel">
    <span class="cms-points-icon"><AppIcon name="leaf" :size="26" /></span>
    <div>
      <span class="eyebrow">GREEN POINTS</span>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
    <RouterLink to="/account/points" class="outline-button"
      >查看积分 <AppIcon name="arrow-right" :size="15"
    /></RouterLink>
  </section>
</template>
