<script setup lang="ts">
import { asString } from '@/utils/cms'

const props = defineProps<{ config: Record<string, unknown> }>()
const title = asString(props.config.title, '')
const text = asString(props.config.text, '')
</script>

<template>
  <section v-if="text" class="cms-rich-text section-block">
    <h2 v-if="title">{{ title }}</h2>
    <p>{{ text }}</p>
  </section>
</template>
