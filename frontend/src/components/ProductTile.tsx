import { Link } from 'react-router-dom'
import { money, shortText, stockLabel } from '../format'
import type { ProductCard } from '../types'
import { SaveButton } from './SaveButton'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

interface Props {
  product: ProductCard
  fromChat?: boolean
  compact?: boolean
  /** Short info from the chat agent; falls back to the catalogue description. */
  highlight?: string
  /** The product whose page is open right now. */
  current?: boolean
}

/** A product card. Clicking it opens that product's own page. */
export function ProductTile({ product: p, fromChat = false, compact = false, highlight, current = false }: Props) {
  const info = highlight || p.description
  return (
    <Link to={`/products/${encodeURIComponent(p.product_id)}`} className={`tile ${compact ? 'tile-compact' : ''} ${fromChat ? 'tile-from-chat' : ''} ${current ? 'tile-current' : ''}`}
      aria-current={current ? 'page' : undefined}>
      <div className="tile-image">
        <img src={p.image_url} alt={p.name} loading="lazy" />
        {fromChat && !compact && <span className="badge badge-chat">From your chat</span>}
        {current && <span className="badge badge-chat">Viewing</span>}
        <SaveButton productId={p.product_id} name={p.name} />
        {p.stock_status !== 'in_stock' && (
          <span className={`badge ${p.stock_status === 'sold_out' ? 'badge-sold' : 'badge-low'}`}>{stockLabel(p)}</span>
        )}
      </div>
      <div className="tile-body">
        <span className="tile-category">{p.category}</span>
        <span className="tile-name">{p.name}</span>
        <span className="tile-price hang-tag"><span className="tag-price">{money(p.price)}</span></span>
        {!compact && (
          <span className="size-dots" aria-label={p.stock_status === 'sold_out' ? 'Sold out in every size' : `In stock in ${p.sizes_in_stock.join(', ')}`}>
            {SIZES.map((s) => (
              <span key={s} className={p.sizes_in_stock.includes(s) ? 'on' : 'off'} aria-hidden="true">{s}</span>
            ))}
          </span>
        )}
        {!compact && info && <span className="tile-desc">{shortText(info, 90)}</span>}
      </div>
    </Link>
  )
}
