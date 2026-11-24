<script setup lang="ts">
import { computed } from 'vue'
import { assetUrl } from '@/api/http'
import { asString, isSafeExternalLink, isSafeInternalLink } from '@/utils/cms'

const props = defineProps<{ config: Record<string, unknown> }>()
const title = asString(props.config.title, '')
const icon = asString(props.config.icon_url, '')
const linkType = asString(props.config.link_type, 'internal')
const linkUrl = asString(props.config.link_url, '/')
const safe = computed(() =>
  linkType === 'external' ? isSafeExternalLink(linkUrl) : isSafeInternalLink(linkUrl)
)
</script>

<template>
  <div class="cms-navigation-item">
    <img v-if="icon" :src="assetUrl(icon)" :alt="title" />
    <a
      v-if="safe && linkType === 'external'"
      :href="linkUrl"
      target="_blank"
      rel="noopener noreferrer"
    >
      {{ title }}
    </a>
    <RouterLink v-else-if="safe" :to="linkUrl">{{ title }}</RouterLink>
    <span v-else>{{ title }}</span>
  </div>
</template>
