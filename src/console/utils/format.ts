const SHANGHAI = 'Asia/Shanghai'

export function formatMoney(value?: string | number | null): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number') return value.toFixed(2)
  if (/^-?\d+(\.\d+)?$/.test(value)) {
    const [integer, fraction = ''] = value.split('.')
    return `${integer}.${fraction.padEnd(2, '0').slice(0, 2)}`
  }
  return value
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const text = new Intl.DateTimeFormat('zh-CN', {
    timeZone: SHANGHAI,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)
  return text.replace(/\//g, '-')
}

export function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const text = new Intl.DateTimeFormat('zh-CN', {
    timeZone: SHANGHAI,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(date)
  return text.replace(/\//g, '-')
}

export function formatDateInput(date: Date): string {
  const text = new Intl.DateTimeFormat('zh-CN', {
    timeZone: SHANGHAI,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(date)
  const [year, month, day] = text.replace(/\//g, '-').split('-')
  return `${year}-${month}-${day}`
}

export function formatPeriod(start?: string | null, end?: string | null): string {
  if (!start || !end) return '—'
  const endDate = new Date(end)
  endDate.setDate(endDate.getDate() - 1)
  return `${formatDate(start)} ~ ${formatDate(endDate.toISOString())}`
}

export function formatPercent(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(1)}%`
}

export function maskPhone(value?: string | null): string {
  if (!value) return '—'
  if (/^\d{11}$/.test(value)) return `${value.slice(0, 3)}****${value.slice(7)}`
  return value
}

export function maskEmail(value?: string | null): string {
  if (!value) return '—'
  const [name, domain] = value.split('@')
  if (!domain) return value
  return `${name.slice(0, 1)}***@${domain}`
}

export function maskAddress(value?: string | null): string {
  if (!value) return '—'
  if (value.length <= 10) return value
  return `${value.slice(0, 8)}****${value.slice(-2)}`
}

export function isOverdue(deadline?: string | null): boolean {
  if (!deadline) return false
  return new Date(deadline).getTime() < Date.now()
}

export function hoursUntil(deadline?: string | null): number {
  if (!deadline) return 0
  return Math.ceil((new Date(deadline).getTime() - Date.now()) / 3600000)
}

export function relativeTime(iso?: string | null): string {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  return `${days} 天前`
}

export function toNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0
  return Number(value)
}

export function downloadCsv(
  filename: string,
  rows: Array<Record<string, string | number>>,
  headers: Array<{ key: string; label: string }>
): void {
  const escape = (value: string | number | undefined): string => {
    const text = value === undefined || value === null ? '' : String(value)
    return `"${text.replace(/"/g, '""')}"`
  }
  const lines = [
    headers.map((item) => escape(item.label)).join(','),
    ...rows.map((row) => headers.map((item) => escape(row[item.key])).join(','))
  ]
  const blob = new Blob([`\uFEFF${lines.join('\r\n')}`], {
    type: 'text/csv;charset=utf-8'
  })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(link.href)
}

export async function copyText(value: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(value)
    return true
  } catch {
    return false
  }
}
