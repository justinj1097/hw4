import type { ProductCard } from './types'

export const money = (n: number) => (Number.isInteger(n) ? `$${n}` : `$${n.toFixed(2)}`)

/** Trim text to about `max` characters at a word boundary. */
export function shortText(text: string, max: number) {
  if (text.length <= max) return text
  return text.slice(0, text.lastIndexOf(' ', max)).replace(/[,.;:]$/, '') + '…'
}

export function stockLabel(p: Pick<ProductCard, 'stock_status' | 'total_stock'>) {
  if (p.stock_status === 'sold_out') return 'Sold out'
  if (p.stock_status === 'low_stock') return `Only ${p.total_stock} left`
  return 'In stock'
}

