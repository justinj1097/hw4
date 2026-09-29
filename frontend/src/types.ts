// Mirrors backend/app/models.py.

export type StockStatus = 'in_stock' | 'low_stock' | 'sold_out'

export interface ProductCard {
  product_id: string
  name: string
  category: string
  garment_type: string
  description: string
  colors: string[]
  price: number
  image_url: string
  total_stock: number
  sizes_in_stock: string[]
  stock_status: StockStatus
}

export interface SizeStock {
  size: string
  quantity: number
}

export interface ProductDetail extends ProductCard {
  search_tags: string[]
  inventory: SizeStock[]
}

export interface Facets {
  categories: { name: string; count: number }[]
  colors: string[]
  min_price: number
  max_price: number
}

export interface User {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
  created_at: string
}

// The product-card contract: the agent picks products, the backend fills in live data, the page renders it.
export interface ShowcaseCard extends ProductCard {
  highlight: string
}

export interface BrowseLink {
  category: string | null
  query: string | null
  color: string | null
}

export interface Showcase {
  title: string
  items: ShowcaseCard[]
  browse: BrowseLink | null
  total_matches: number | null
}

/** What the backend actually looked up for an answer (written from tool calls, not by the model). */
export interface Checks {
  checked_at: string
  items: string[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  showcase: Showcase | null
  checks?: Checks | null
}

export type Sort = 'featured' | 'price_asc' | 'price_desc' | 'name'

export interface Filters {
  q: string
  category: string | null
  color: string | null
  size: string | null
  inStock: boolean
  sort: Sort
}

/** Where the shopper is when they send a chat message (the server double-checks it). */
export interface PageContext {
  path: string
  product_id: string | null
  category: string | null
  search: string | null
  saved_ids: string[]
}
