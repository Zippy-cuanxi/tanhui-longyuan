<script setup lang="ts">
import { computed } from 'vue'
import { assetUrl } from '@/api/http'
import { asString, isSafeExternalLink, isSafeInternalLink } from '@/utils/cms'

const props = withDefaults(
  defineProps<{
    config: Record<string, unknown>
    variant?: 'home' | 'page'
    fallbackImage?: string
  }>(),
  { variant: 'home', fallbackImage: '/assets/banners/home-hero.webp' }
)

const image = computed(() => {
  const raw = asString(props.config.image_url, '')
  if (!raw || raw.includes('example.com')) return props.fallbackImage
  return assetUrl(raw, props.fallbackImage)
})
const title = computed(() => asString(props.config.title, '来自陇原的自然好物'))
const linkType = computed(() => asString(props.config.link_type, 'internal'))
const linkUrl = computed(() => asString(props.config.link_url, '/products'))
const hasLink = computed(() =>
  linkType.value === 'external'
    ? isSafeExternalLink(linkUrl.value)
    : isSafeInternalLink(linkUrl.value)
)
const linkTarget = computed(() => (linkType.value === 'external' ? linkUrl.value : linkUrl.value))
</script>

<template>
  <section class="banner-section" :class="`banner-${variant}`" :aria-label="title">
    <a
      v-if="hasLink && linkType === 'external'"
      :href="linkTarget"
      target="_blank"
      rel="noopener noreferrer"
      class="banner-link"
    >
      <img :src="image" :alt="title" />
    </a>
    <RouterLink v-else-if="hasLink" :to="linkTarget" class="banner-link">
      <img :src="image" :alt="title" />
    </RouterLink>
    <div v-else class="banner-link">
      <img :src="image" :alt="title" />
    </div>
    <h1 v-if="variant === 'home'" class="sr-only">{{ title }}</h1>
  </section>
</template>
