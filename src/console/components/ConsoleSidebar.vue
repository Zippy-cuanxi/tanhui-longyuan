<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { ConsoleMenuGroup, ConsoleMenuItem } from '@/console/constants/menu'

const props = defineProps<{
  menus: ConsoleMenuGroup[]
  collapsed: boolean
}>()

const route = useRoute()
const flatMenus = computed(() => props.menus.flatMap((group) => group.items))

function queryMatches(item: ConsoleMenuItem): boolean {
  if (!item.query) return true
  return Object.entries(item.query).every(
    ([key, value]) => String(route.query[key] ?? '') === value
  )
}

function hasExactMenuItem(): boolean {
  return flatMenus.value.some((item) => item.path === route.path)
}

function hasQueryMenuItem(): boolean {
  return flatMenus.value.some(
    (item) => item.path === route.path && Boolean(item.query) && queryMatches(item)
  )
}

function isActive(item: ConsoleMenuItem): boolean {
  if (item.query) {
    return route.path === item.path && queryMatches(item)
  }
  if (route.path === item.path) {
    // 同一路径下存在 query 菜单（系统设置 / 操作日志）时，避免两个菜单同时高亮
    return !hasQueryMenuItem()
  }
  if (item.activePrefix && route.path.startsWith(item.activePrefix)) {
    // 子页面（详情 / 编辑）高亮父菜单；若子页面本身有菜单项则不重复高亮
    return !hasExactMenuItem()
  }
  return false
}

function iconPath(item: ConsoleMenuItem): string {
  const active = isActive(item)
  return `/console-assets/icons/${item.icon}-${active ? 'green' : 'gray'}.svg`
}

function toOf(item: ConsoleMenuItem) {
  return { path: item.path, query: item.query }
}
</script>

<template>
  <aside class="console-sidebar" :class="{ collapsed }">
    <RouterLink to="/console" class="console-brand" aria-label="碳惠陇原后台">
      <img
        :src="collapsed ? '/console-assets/icons/points-green.svg' : '/images/logo/logo.png'"
        alt="碳惠陇原"
      />
    </RouterLink>

    <nav class="console-menu" aria-label="后台主导航">
      <section v-for="group in menus" :key="group.title" class="console-menu-group">
        <div class="console-menu-title">{{ group.title }}</div>
        <RouterLink
          v-for="item in group.items"
          :key="`${group.title}-${item.label}-${item.path}`"
          :to="toOf(item)"
          class="console-menu-item"
          :class="{ active: isActive(item) }"
          :title="collapsed ? item.label : undefined"
        >
          <img :src="iconPath(item)" :alt="item.label" />
          <span class="menu-label">{{ item.label }}</span>
          <span v-if="item.comingSoon" class="menu-dot" title="二期功能" />
        </RouterLink>
      </section>
    </nav>
    <div class="console-sidebar-foot">碳惠陇原后台 · 仿真数据<br />v1.0 · 2026</div>
  </aside>
</template>
