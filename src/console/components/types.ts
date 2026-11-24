export interface TableColumn {
  prop?: string
  label: string
  width?: string | number
  minWidth?: string | number
  align?: 'left' | 'center' | 'right'
  slot?: string
  formatter?: (row: Record<string, unknown>) => string | number
  showOverflowTooltip?: boolean
  fixed?: boolean | 'left' | 'right'
}
