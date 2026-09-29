import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProductsByIds } from '../api'
import { ProductTile } from '../components/ProductTile'
import { money } from '../format'
import { useShop } from '../store'
import type { ProductCard } from '../types'

/** The wishlist: saved products with live price and stock, plus one-click help from the assistant. */
export function SavedPage() {
  const { saved, send, user } = useShop()
  const [products, setProducts] = useState<ProductCard[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let live = true
    if (saved.length === 0) {
      setProducts([])
      setLoading(false)
      return
    }
    fetchProductsByIds(saved)
      .then((r) => live && setProducts(r.products))
      .catch(() => live && setProducts([]))
      .finally(() => live && setLoading(false))
    return () => {
      live = false
    }
  }, [saved])

  const total = products.reduce((sum, p) => sum + p.price, 0)
  return (
    <div className="container shop">
      <div className="section-head">
        <h1 className="page-title">Saved items</h1>
        <span className="muted">{saved.length} saved{products.length > 0 && ` · ${money(total)} together`}</span>
      </div>
      {!user && saved.length > 0 && (
        <p className="muted small">Saved in this browser. <Link to="/signup">Create an account</Link> to keep your chats too.</p>
      )}
      {loading && <p className="muted">Loading…</p>}
      {!loading && saved.length === 0 && (
        <div className="empty">
          <p>You haven't saved anything yet. Tap the ♡ on any product to keep it here.</p>
          <Link className="btn btn-primary" to="/products">Browse products</Link>
        </div>
      )}
      {products.length > 0 && (
        <>
          <div className="saved-actions">
            <button className="btn btn-primary" onClick={() => send('Compare my saved items: price, and which sizes are in stock.')}>
              Ask the assistant to compare my saved items
            </button>
            {products.length > 1 && (
              <button className="btn btn-outline" onClick={() => send('Which of my saved items is the best gift, and is it in stock in M?')}>
                Which is the best gift?
              </button>
            )}
          </div>
          <div className="grid">
            {products.map((p) => <ProductTile key={p.product_id} product={p} />)}
          </div>
        </>
      )}
    </div>
  )
}
