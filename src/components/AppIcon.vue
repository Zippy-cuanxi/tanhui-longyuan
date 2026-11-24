<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    name: string
    size?: number | string
    strokeWidth?: number
  }>(),
  { size: 20, strokeWidth: 1.8 }
)

const paths: Record<string, string[]> = {
  search: ['M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z', 'm21 21-4.35-4.35'],
  cart: ['M6 7h12l-1 12H7L6 7Z', 'M9 7V5a3 3 0 0 1 6 0v2'],
  user: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z', 'M5 21a7 7 0 0 1 14 0'],
  'chevron-left': ['m15 18-6-6 6-6'],
  'chevron-right': ['m9 18 6-6-6-6'],
  'chevron-down': ['m6 9 6 6 6-6'],
  'chevron-up': ['m18 15-6-6-6 6'],
  leaf: ['M20 4C12 4 5 8 5 16c0 2 1 4 3 4 8 0 12-7 12-16Z', 'M4 21c4-4 8-6 12-8'],
  check: ['m5 12 4 4L19 6'],
  map: ['M9 18 3 21V6l6-3 6 3 6-3v15l-6 3-6-3Z', 'M9 18V3', 'M15 21V6'],
  plus: ['M12 5v14', 'M5 12h14'],
  minus: ['M5 12h14'],
  grid: ['M4 4h6v6H4V4Z', 'M14 4h6v6h-6V4Z', 'M4 14h6v6H4v-6Z', 'M14 14h6v6h-6v-6Z'],
  close: ['m6 6 12 12', 'M18 6 6 18'],
  trash: ['M4 7h16', 'M9 7V4h6v3', 'm6 7 1 14h10l1-14', 'M10 11v6', 'M14 11v6'],
  location: [
    'M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11Z',
    'M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z'
  ],
  package: ['M3 7l9-4 9 4-9 4-9-4Z', 'M3 7v10l9 4 9-4V7', 'M12 11v10'],
  truck: [
    'M3 7h11v8H3V7Z',
    'M14 10h4l3 3v2h-7v-5Z',
    'M7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
    'M18 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z'
  ],
  clock: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M12 8v5l3 2'],
  phone: ['M6 3h4l2 5-2 2c1 2 3 4 5 5l2-2 5 2v4c0 1-1 2-2 2C10 21 3 14 3 5c0-1 1-2 2-2Z'],
  edit: ['m4 20 4-1 11-11-3-3L5 16l-1 4Z', 'm14 7 3 3'],
  home: ['m3 11 9-8 9 8', 'M5 10v10h14V10'],
  gift: [
    'M4 11h16v9H4v-9Z',
    'M3 7h18v4H3V7Z',
    'M12 7v13',
    'M12 7c-2 0-4-1-4-3 0-1 .7-2 2-2 2 0 2 2 2 5Z',
    'M12 7c2 0 4-1 4-3 0-1-.7-2-2-2-2 0-2 2-2 5Z'
  ],
  'arrow-right': ['M5 12h14', 'm13 6 6 6-6 6'],
  copy: ['M8 8h11v12H8V8Z', 'M5 16H4V4h11v3'],
  alert: ['M12 3 2 21h20L12 3Z', 'M12 9v6', 'M12 18h.01'],
  info: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M12 11v5', 'M12 8h.01'],
  star: ['m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1L3.2 9.4l6.1-.9L12 3Z'],
  shield: ['M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3Z', 'm9 12 2 2 4-5'],
  wallet: ['M3 7a2 2 0 0 1 2-2h13v4H5a2 2 0 0 0-2 2v8h16V9', 'M3 7v12h18V7H5', 'M16 13h2'],
  bell: ['M18 16H6l1-2v-4a5 5 0 0 1 10 0v4l1 2Z', 'M10 19a2 2 0 0 0 4 0'],
  refresh: ['M20 11a8 8 0 1 0-2 6', 'M20 4v7h-7'],
  logout: ['M10 5H5v14h5', 'M14 8l4 4-4 4', 'M8 12h10'],
  card: ['M3 6h18v12H3V6Z', 'M3 10h18', 'M7 15h3'],
  chart: ['M4 20V10', 'M10 20V4', 'M16 20v-7', 'M22 20H2'],
  heart: ['M12 21s-7-4.5-7-10a4 4 0 0 1 7-2 4 4 0 0 1 7 2c0 5.5-7 10-7 10Z'],
  sprout: ['M12 21V10', 'M12 10C8 10 5 8 4 4c4 0 8 2 8 6Z', 'M12 14c4 0 7-2 8-6-4 0-8 2-8 6Z'],
  mountain: ['m3 20 6-16 4 9 3-5 5 12H3Z'],
  wheat: [
    'M12 21V8',
    'M8 14c0-3 2-5 4-6 2 1 4 3 4 6-2 0-4-1-4-3 0 2-2 3-4 3Z',
    'M8 9c0-3 2-5 4-6 2 1 4 3 4 6'
  ],
  sparkle: ['m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z'],
  filter: ['M4 6h16', 'M7 12h10', 'M10 18h4'],
  eye: ['M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z', 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z']
}

const iconPaths = computed(() => paths[props.name] || paths.info)
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="(d, index) in iconPaths" :key="index" :d="d" />
  </svg>
</template>
