import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts } from '../api'
import { ProductTile } from '../components/ProductTile'
import { useShop } from '../store'
import type { Filters, ProductCard, Sort } from '../types'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const SORTS: Sort[] = ['featured', 'price_asc', 'price_desc', 'name']

/** The URL holds the filters, so Home's category links, search, and the back button all work. */
function filtersFrom(params: URLSearchParams): Filters {
  const sort = params.get('sort') as Sort | null
  return {
    q: params.get('q') ?? '',
    category: params.get('category'),
    color: params.get('color'),
    size: params.get('size'),
    inStock: params.get('in_stock') === 'true',
    sort: sort && SORTS.includes(sort) ? sort : 'featured',
  }
}

export function ProductsPage() {
  const { facets, showcase, send } = useShop()
  const [params, setParams] = useSearchParams()
  const filters = useMemo(() => filtersFrom(params), [params])
  const [products, setProducts] = useState<ProductCard[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const pickIds = useMemo(() => new Set(showcase?.items.map((p) => p.product_id) ?? []), [showcase])

  useEffect(() => {
    let live = true
    setLoading(true)
    fetchProducts(filters)
      .then((r) => live && (setProducts(r.products), setError('')))
      .catch(() => live && setError('Could not load products. Is the backend running on port 8000?'))
      .finally(() => live && setLoading(false))
    return () => {
      live = false
    }
  }, [filters])

  const set = (key: string, value: string | null) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }

  const filtered = Boolean(filters.q || filters.category || filters.color || filters.size || filters.inStock)

  return (
    <>
      <section className="shop container" aria-label="Products">
        <div className="section-head">
          <h1 className="page-title">{filters.q ? `Results for “${filters.q}”` : filters.category ?? 'All products'}</h1>
          <span className="muted">{loading ? 'Loading…' : `${products.length} products`}</span>
        </div>

        <div className="category-pills" role="group" aria-label="Category">
          <button className={!filters.category ? 'pill active' : 'pill'} onClick={() => set('category', null)}>All</button>
          {facets?.categories.map((c) => (
            <button key={c.name} className={filters.category === c.name ? 'pill active' : 'pill'} onClick={() => set('category', c.name)}>
              {c.name}
            </button>
          ))}
        </div>

        <div className="toolbar">
          <select value={filters.color ?? ''} onChange={(e) => set('color', e.target.value || null)} aria-label="Color">
            <option value="">All colors</option>
            {facets?.colors.map((c) => <option key={c} value={c}>{c[0].toUpperCase() + c.slice(1)}</option>)}
          </select>
          <select value={filters.size ?? ''} onChange={(e) => set('size', e.target.value || null)} aria-label="Size in stock">
            <option value="">Any size</option>
            {SIZES.map((s) => <option key={s} value={s}>{s} in stock</option>)}
          </select>
          <label className="check">
            <input type="checkbox" checked={filters.inStock} onChange={(e) => set('in_stock', e.target.checked ? 'true' : null)} /> In stock only
          </label>
          <select value={filters.sort} onChange={(e) => set('sort', e.target.value === 'featured' ? null : e.target.value)} aria-label="Sort">
            <option value="featured">Featured</option>
            <option value="price_asc">Price: low to high</option>
            <option value="price_desc">Price: high to low</option>
            <option value="name">Name A–Z</option>
          </select>
          {filtered && <button className="link-button" onClick={() => setParams(new URLSearchParams())}>Clear filters</button>}
        </div>

        {error && <p className="form-error">{error}</p>}
        {!loading && !error && products.length === 0 && (
          <div className="empty">
            <p>No products match those filters.</p>
            <button className="btn btn-primary" onClick={() => send(`I'm looking for ${filters.q || 'something'}${filters.color ? ` in ${filters.color}` : ''}. What do you have?`)}>
              Ask the assistant for alternatives
            </button>
          </div>
        )}
        <div className="grid">
          {products.map((p) => <ProductTile key={p.product_id} product={p} fromChat={pickIds.has(p.product_id)} />)}
        </div>
      </section>
    </>
  )
}
