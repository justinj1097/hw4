import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchProducts } from '../api'
import { money, stockLabel } from '../format'
import { useShop } from '../store'
import type { ProductCard } from '../types'

const SHOWN = 6

/** Header search with instant suggestions: live product matches as you type, keyboard navigation, and shortcuts. */
export function SearchBox() {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<ProductCard[]>([])
  const [total, setTotal] = useState(0)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { send } = useShop()
  const boxRef = useRef<HTMLDivElement>(null)
  const listId = useId()
  const term = q.trim()

  // Debounced lookup: wait ~200 ms after the last keystroke, and ignore replies that arrive out of order.
  useEffect(() => {
    if (term.length < 2) {
      setResults([])
      setTotal(0)
      return
    }
    let live = true
    setLoading(true)
    const timer = setTimeout(() => {
      fetchProducts({ q: term, category: null, color: null, size: null, inStock: false, sort: 'featured' })
        .then((r) => {
          if (!live) return
          setResults(r.products.slice(0, SHOWN))
          setTotal(r.total)
          setActive(-1)
        })
        .catch(() => live && setResults([]))
        .finally(() => live && setLoading(false))
    }, 200)
    return () => {
      live = false
      clearTimeout(timer)
    }
  }, [term])

  useEffect(() => {
    const close = (e: MouseEvent) => !boxRef.current?.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  // Rows: product suggestions, then "See all results", then "Ask the assistant".
  const rows = term.length >= 2 ? results.length + 2 : 0
  const finish = () => {
    setOpen(false)
    setActive(-1)
  }
  const choose = (index: number) => {
    if (index >= 0 && index < results.length) {
      navigate(`/products/${encodeURIComponent(results[index].product_id)}`)
      setQ('') // a product was chosen: clear the box for the next search
    }
    else if (index === results.length || index < 0) navigate(term ? `/products?q=${encodeURIComponent(term)}` : '/products')
    else send(`Do you have anything like "${term}"?`)
    finish()
  }

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setActive((a) => (rows ? (a + 1) % rows : -1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => (rows ? (a - 1 + rows) % rows : -1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      choose(active)
    } else if (e.key === 'Escape') {
      finish()
    }
  }

  const showPanel = open && term.length >= 2
  return (
    <div className="search-wrap" ref={boxRef}>
      <div className="search" role="search">
        <input
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKey}
          placeholder="Search hoodies, colleges, sports…"
          aria-label="Search products"
          role="combobox"
          aria-expanded={showPanel}
          aria-controls={listId}
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
          autoComplete="off"
        />
        <button type="button" aria-label="Search" onClick={() => choose(-1)}>
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
            <path d="m20 20-4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
      </div>
      {showPanel && (
        <div className="suggest" id={listId} role="listbox" aria-label="Search suggestions">
          {loading && results.length === 0 && <p className="suggest-empty">Searching…</p>}
          {!loading && results.length === 0 && <p className="suggest-empty">No products match “{term}”.</p>}
          {results.map((p, i) => (
            <button key={p.product_id} id={`${listId}-${i}`} role="option" aria-selected={active === i}
              className={`suggest-item ${active === i ? 'active' : ''}`} onMouseEnter={() => setActive(i)} onClick={() => choose(i)}>
              <img src={p.image_url} alt="" />
              <span className="suggest-text">
                <span className="suggest-name">{p.name}</span>
                <span className="suggest-meta">{p.category} · {money(p.price)}</span>
              </span>
              <span className={`suggest-stock stock-${p.stock_status}`}>{stockLabel(p)}</span>
            </button>
          ))}
          <button id={`${listId}-${results.length}`} role="option" aria-selected={active === results.length}
            className={`suggest-action ${active === results.length ? 'active' : ''}`} onMouseEnter={() => setActive(results.length)} onClick={() => choose(results.length)}>
            {total > 0 ? `See all ${total} result${total === 1 ? '' : 's'} for “${term}” →` : `Browse all products →`}
          </button>
          <button id={`${listId}-${results.length + 1}`} role="option" aria-selected={active === results.length + 1}
            className={`suggest-action ask ${active === results.length + 1 ? 'active' : ''}`} onMouseEnter={() => setActive(results.length + 1)} onClick={() => choose(results.length + 1)}>
            💬 Ask the assistant about “{term}”
          </button>
        </div>
      )}
    </div>
  )
}
