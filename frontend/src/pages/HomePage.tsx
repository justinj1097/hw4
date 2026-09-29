import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts } from '../api'
import { ProductTile } from '../components/ProductTile'
import { WindowDisplay } from '../components/WindowDisplay'
import { useShop } from '../store'
import type { ProductCard } from '../types'

const FEATURED = ['yale-mom-hoodie', 'district-vit-crewneck-vintage-bulldog', 'saybrook-college-crewneck', '2025-yale-vs-harvard-t-shirt', 'basic-hoodie-big-yale', 'champion-full-zip-hood']

const PROMISES = [
  { title: 'Officially licensed', text: 'Every piece carries real Yale marks, approved by the university. No knock-offs.' },
  { title: 'Made in New Haven', text: 'Most printing and embroidery happens in our own shop, a short walk from Old Campus.' },
  { title: 'Here since 1975', text: 'Bulldogs have shopped with us for nearly fifty years, and we are still family-run.' },
  { title: 'Custom orders', text: 'Outfitting a team, club, reunion, or event? We print and embroider group orders too.' },
]

export function HomePage() {
  const { facets, setChatOpen } = useShop()
  const [featured, setFeatured] = useState<ProductCard[]>([])

  useEffect(() => {
    fetchProducts({ q: '', category: null, color: null, size: null, inStock: false, sort: 'featured' })
      .then((r) => {
        const byId = new Map(r.products.map((p) => [p.product_id, p]))
        setFeatured(FEATURED.map((id) => byId.get(id)).filter((p): p is ProductCard => Boolean(p)))
      })
      .catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="storefront" aria-label="Campus Customs, 57 Broadway">
        <div className="awning" aria-hidden="true" />
        <div className="container storefront-inner">
          <div className="hero-copy">
            <p className="est">Est. <span>1975</span> · 57 Broadway, New Haven</p>
            <h1 className="varsity">Wear your<br />Bulldog pride</h1>
            <p className="hero-text">
              New Haven's oldest official Yale shop, printing and stitching Yale gear a block from Old Campus for nearly fifty
              years. Find your hoodie, your college crest, or the perfect gift for a proud Yale parent.
            </p>
            <div className="hero-actions">
              <Link className="btn btn-light" to="/products">Shop the store</Link>
              <button className="btn btn-outline-light" onClick={() => setChatOpen(true)}>Ask Boola 🐾</button>
            </div>
            <ul className="hero-facts">
              <li><b>102</b> styles</li>
              <li><b>XS–XXL</b> sizes</li>
              <li><b>30-day</b> returns</li>
            </ul>
          </div>
          <WindowDisplay products={featured} />
        </div>
      </section>

      <section className="container home-section">
        <div className="section-head">
          <h2>Shop by category</h2>
          <Link className="link-button" to="/products">View everything →</Link>
        </div>
        <div className="category-grid">
          {facets?.categories.map((c) => (
            <Link key={c.name} to={`/products?category=${encodeURIComponent(c.name)}`} className="category-card">
              <span className="category-name">{c.name}</span>
              <span className="muted small">{c.count} styles</span>
            </Link>
          ))}
        </div>
      </section>

      {featured.length > 0 && (
        <section className="container home-section">
          <div className="section-head">
            <h2>Campus favorites</h2>
            <span className="est small-est">Picked by the counter staff</span>
          </div>
          <div className="grid">
            {featured.map((p) => <ProductTile key={p.product_id} product={p} />)}
          </div>
        </section>
      )}

      <section className="promise-band">
        <div className="container promise-grid">
          {PROMISES.map((p) => (
            <div key={p.title}>
              <h3>{p.title}</h3>
              <p>{p.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="container home-section visit">
        <div>
          <h2>Visit us on Broadway</h2>
          <p>
            Stop by 57 Broadway in New Haven to try things on, or ask our assistant about sizes and stock before you come.
            Call ahead for hours: (475) 301-4205.
          </p>
        </div>
        <Link className="btn btn-primary" to="/about">Our story</Link>
      </section>
    </>
  )
}
