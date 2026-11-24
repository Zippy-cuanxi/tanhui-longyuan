import { onBeforeUnmount, onMounted, ref } from 'vue'

/** 1280–1365 宽度下隐藏次要表格列，保证 1280 桌面端不出现表格横向滚动。 */
export function useCompactTable(breakpoint = 1366) {
  const compact = ref(typeof window !== 'undefined' && window.innerWidth < breakpoint)

  function update(): void {
    compact.value = window.innerWidth < breakpoint
  }

  onMounted(() => {
    update()
    window.addEventListener('resize', update)
  })
  onBeforeUnmount(() => window.removeEventListener('resize', update))

  return { compact }
}
