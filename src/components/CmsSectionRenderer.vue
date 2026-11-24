<script setup lang="ts">
import type { CmsSection } from '@/api/types'
import BannerSection from './sections/BannerSection.vue'
import ProductGridSection from './sections/ProductGridSection.vue'
import RichTextSection from './sections/RichTextSection.vue'
import PointsPanelSection from './sections/PointsPanelSection.vue'
import AidProjectSection from './sections/AidProjectSection.vue'
import NavigationSection from './sections/NavigationSection.vue'

defineProps<{ section: CmsSection }>()

const supported = new Set([
  'banner',
  'product_grid',
  'rich_text',
  'points_panel',
  'aid_project',
  'navigation'
])
</script>

<template>
  <template v-if="section.enabled">
    <BannerSection
      v-if="section.section_type === 'banner'"
      :config="section.config"
      variant="page"
    />
    <ProductGridSection
      v-else-if="section.section_type === 'product_grid'"
      :config="section.config"
      :columns="4"
    />
    <RichTextSection v-else-if="section.section_type === 'rich_text'" :config="section.config" />
    <PointsPanelSection
      v-else-if="section.section_type === 'points_panel'"
      :config="section.config"
    />
    <AidProjectSection
      v-else-if="section.section_type === 'aid_project'"
      :config="section.config"
    />
    <NavigationSection v-else-if="section.section_type === 'navigation'" :config="section.config" />
    <span v-else class="sr-only"
      >未知组件已安全降级：{{
        supported.has(section.section_type) ? '' : section.section_type
      }}</span
    >
  </template>
</template>
