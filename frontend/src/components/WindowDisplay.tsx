import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { money } from '../format'
import type { ProductCard } from '../types'

/** The shop window: featured products rotate on a lit display stand, like the window at 57 Broadway. */
export function WindowDisplay({ products }: { products: ProductCard[] }) {
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    if (paused || products.length < 2 || matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const timer = setInterval(() => setIndex((i) => (i + 1) % products.length), 3800)
    return () => clearInterval(timer)
  }, [paused, products.length])

  if (products.length === 0) return <div className="window" aria-hidden="true" />
  const p = products[index % products.length]
  return (
    <div className="window" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
      <div className="window-glass">
        <span className="window-sign" aria-hidden="true">In the window</span>
        {products.map((item, i) => (
          <img key={item.product_id} src={item.image_url} alt={i === index ? item.name : ''} className={`window-item ${i === index ? 'on' : ''}`} />
        ))}
        <div className="window-stand" aria-hidden="true" />
        <Link to={`/products/${encodeURIComponent(p.product_id)}`} className="hang-tag big" key={p.product_id}>
          <span className="tag-name">{p.name}</span>
          <span className="tag-price">{money(p.price)}</span>
        </Link>
      </div>
      <div className="window-dots" role="tablist" aria-label="Featured products">
        {products.map((item, i) => (
          <button key={item.product_id} role="tab" aria-selected={i === index} aria-label={item.name} className={i === index ? 'on' : ''} onClick={() => setIndex(i)} />
        ))}
      </div>
    </div>
  )
}
