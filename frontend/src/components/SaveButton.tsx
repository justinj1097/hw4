import { useState, type MouseEvent } from 'react'
import { useShop } from '../store'

/** Heart toggle for the wishlist. Works inside a card link without opening the product. */
export function SaveButton({ productId, name, variant = 'icon' }: { productId: string; name: string; variant?: 'icon' | 'button' }) {
  const { isSaved, toggleSaved } = useShop()
  const saved = isSaved(productId)
  const [burst, setBurst] = useState(0)
  const toggle = (e: MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!saved) setBurst((b) => b + 1)
    toggleSaved(productId)
  }
  const label = saved ? `Remove ${name} from saved items` : `Save ${name}`
  return (
    <button type="button" className={`save-btn save-${variant} ${saved ? 'is-saved' : ''}`} onClick={toggle} aria-pressed={saved} aria-label={label} title={label}>
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path d="M12 20.5s-7.5-4.6-9.3-9.2C1.4 7.9 3.6 4.5 7 4.5c2 0 3.4 1.1 5 3 1.6-1.9 3-3 5-3 3.4 0 5.6 3.4 4.3 6.8-1.8 4.6-9.3 9.2-9.3 9.2z"
          fill={saved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      </svg>
      {variant === 'button' && <span>{saved ? 'Saved' : 'Save'}</span>}
      {burst > 0 && saved && (
        <span key={burst} className="burst" aria-hidden="true">
          {[0, 1, 2, 3, 4, 5].map((i) => <i key={i} style={{ '--i': i } as React.CSSProperties} />)}
        </span>
      )}
    </button>
  )
}
