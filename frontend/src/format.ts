/** Display helpers for result values. */

export function formatValue(v: unknown, key = ''): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'boolean') return v ? 'true' : 'false'
  if (typeof v === 'number') {
    const money = /spend|price|value|amount|total/i.test(key)
    const abs = Math.abs(v)
    if (money) {
      if (abs >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
      if (abs >= 1e6) return `$${(v / 1e6).toFixed(2)}M`
      return `$${v.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
    }
    return v.toLocaleString('en-US', { maximumFractionDigits: 2 })
  }
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

export function compactNumber(v: number): string {
  return Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(v)
}
