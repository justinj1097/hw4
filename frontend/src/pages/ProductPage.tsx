import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, fetchProduct, fetchProducts } from '../api'
import { ChatShowcase } from '../components/ChatShowcase'
import { ProductTile } from '../components/ProductTile'
import { SaveButton } from '../components/SaveButton'
import { money, stockLabel } from '../format'
import { useShop } from '../store'
import type { ProductCard, ProductDetail } from '../types'

/** One product: large image on the left, full details (price, description, colors, stock by size) on the right. */
export function ProductPage() {
  const { productId = '' } = useParams()
  const { send, setViewing } = useShop()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [related, setRelated] = useState<ProductCard[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    let live = true
    setProduct(null)
    setError('')
    window.scrollTo({ top: 0 })
    fetchProduct(productId)
      .then((p) => {
        if (!live) return
        setProduct(p)
        setViewing({ id: p.product_id, name: p.name })
        document.title = `${p.name} | Campus Customs`
        return fetchProducts({ q: '', category: p.category, color: null, size: null, inStock: true, sort: 'featured' })
      })
      .then((r) => live && r && setRelated(r.products.filter((x) => x.product_id !== productId).slice(0, 4)))
      .catch((e) => live && setError(e instanceof ApiError && e.status === 404 ? 'We could not find that product.' : 'Could not load this product.'))
    return () => {
      live = false
      setViewing(null)
      document.title = 'Campus Customs | Official Yale Merchandise'
    }
  }, [productId, setViewing])

  if (error) {
    return (
      <div className="container prose-page">
        <h1>{error}</h1>
        <Link className="btn btn-primary" to="/products">Back to all products</Link>
      </div>
    )
  }
  if (!product) return <div className="container prose-page muted">Loading…</div>

  return (
    <div className="container product-page">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/products">Products</Link> <span aria-hidden="true">/</span>{' '}
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>{product.category}</Link> <span aria-hidden="true">/</span>{' '}
        <span>{product.name}</span>
      </nav>

      <div className="detail">
        <div className="detail-image zoomable"
          onMouseMove={(e) => {
            const r = e.currentTarget.getBoundingClientRect()
            e.currentTarget.style.setProperty('--zx', `${((e.clientX - r.left) / r.width) * 100}%`)
            e.currentTarget.style.setProperty('--zy', `${((e.clientY - r.top) / r.height) * 100}%`)
          }}>
          <img src={product.image_url} alt={product.name} />
          <span className="zoom-hint" aria-hidden="true">Hover to zoom</span>
        </div>
        <div className="detail-info">
          <span className="tile-category">{product.category} · {product.garment_type}</span>
          <h1>{product.name}</h1>
          <div className="price-row">
            <p className="detail-price hang-tag big"><span className="tag-price">{money(product.price)}</span></p>
            <SaveButton productId={product.product_id} name={product.name} variant="button" />
          </div>
          <p className={`stock-line stock-${product.stock_status}`}>{stockLabel(product)}</p>
          <p className="detail-desc">{product.description}</p>
          <p className="detail-colors"><strong>Colors:</strong> {product.colors.join(', ')}</p>

          <div>
            <p className="sizes-label"><strong>Stock by size</strong></p>
            <div className="sizes" role="list" aria-label="Stock by size">
              {product.inventory.map((s) => (
                <span key={s.size} role="listitem" className={`size ${s.quantity === 0 ? 'size-out' : s.quantity <= 5 ? 'size-low' : ''}`}
                  title={s.quantity === 0 ? 'Sold out' : `${s.quantity} in stock`}>
                  <b>{s.size}</b>
                  <small>{s.quantity === 0 ? 'Sold out' : s.quantity <= 5 ? `${s.quantity} left` : 'In stock'}</small>
                </span>
              ))}
            </div>
          </div>

          <p className="muted small">
            Buy in store at 57 Broadway, New Haven, or online at yalebulldogblue.com. Returns within 30 days, unworn with tags.
          </p>
          <div className="detail-actions">
            <button className="btn btn-primary" onClick={() => send(`Tell me about the ${product.name}. Is it in stock, and what would go well with it?`)}>
              Ask the assistant about this
            </button>
            <Link className="btn btn-outline" to="/products">Back to products</Link>
          </div>
        </div>
      </div>

      <ChatShowcase placement="inline" />

      {related.length > 0 && (
        <section className="home-section">
          <div className="section-head">
            <h2>More {product.category.toLowerCase()}</h2>
          </div>
          <div className="grid">
            {related.map((p) => <ProductTile key={p.product_id} product={p} />)}
          </div>
        </section>
      )}
    </div>
  )
}
