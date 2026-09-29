import { useEffect, useRef } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { useShop } from '../store'
import type { BrowseLink } from '../types'
import { ProductTile } from './ProductTile'

function browseHref(b: BrowseLink) {
  const params = new URLSearchParams()
  if (b.category) params.set('category', b.category)
  if (b.query) params.set('q', b.query)
  if (b.color) params.set('color', b.color)
  return `/products?${params}`
}

/**
 * Renders the chat's product matches as cards at the top of whatever page the shopper is on.
 * The data is the backend's `showcase` (agent picks + live catalogue data); each card links to its product page.
 */
export function ChatShowcase({ placement = 'top' }: { placement?: 'top' | 'inline' }) {
  const { showcase, showcaseKey, dismissShowcase, setChatOpen } = useShop()
  const { pathname } = useLocation()
  const { productId } = useParams()
  const ref = useRef<HTMLElement>(null)
  // Product pages show their own large detail view first; there the cards sit underneath as a compact row.
  const onProductPage = pathname.startsWith('/products/')
  const compact = placement === 'inline'

  // When a new reply brings cards, bring them into view (but not when a page simply opens with old results).
  const seenKey = useRef(showcaseKey)
  useEffect(() => {
    if (showcaseKey && showcaseKey !== seenKey.current) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    seenKey.current = showcaseKey
  }, [showcaseKey])

  if (!showcase || (placement === 'top' && onProductPage)) return null
  const { title, items, browse, total_matches: total } = showcase
  const more = browse && total && total > items.length

  return (
    <section ref={ref} id="chat-showcase" key={showcaseKey ?? title} className={`showcase ${compact ? 'showcase-compact' : ''}`} aria-label={title} aria-live="polite">
      <div className="container">
        <div className="showcase-head">
          <div>
            <span className="showcase-eyebrow">From your chat</span>
            <h2>{title}</h2>
            <span className="muted small">
              {more ? `Showing ${items.length} of ${total}` : `${items.length} ${items.length === 1 ? 'product' : 'products'}`} · click a card for sizes and details
            </span>
          </div>
          <div className="showcase-actions">
            {more && <Link className="btn btn-outline" to={browseHref(browse)}>See all {total} →</Link>}
            <button className="link-button" onClick={() => setChatOpen(true)}>Keep chatting</button>
            <button className="showcase-close" onClick={dismissShowcase} aria-label="Hide these results">×</button>
          </div>
        </div>
        <div className={compact ? 'showcase-row' : 'grid grid-showcase'}>
          {items.map((p, i) => (
            <div key={p.product_id} className="showcase-item" style={{ animationDelay: `${Math.min(i, 11) * 45}ms` }}>
              <ProductTile product={p} highlight={p.highlight} compact={compact} current={p.product_id === productId} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
