import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { ApiError, clearChatHistory, fetchChatHistory, fetchFacets, fetchMe, getToken, sendChat, setToken } from './api'
import type { ChatMessage, Facets, PageContext, Showcase, User } from './types'

const GUEST_CHAT_KEY = 'cc_guest_chat'
let nextId = 0
const localId = () => `local-${Date.now()}-${nextId++}`

function readSaved(key: string): string[] {
  try {
    const ids = JSON.parse(localStorage.getItem(key) ?? '[]')
    return Array.isArray(ids) ? ids.filter((x) => typeof x === 'string').slice(0, 30) : []
  } catch {
    return []
  }
}

function loadGuestChat(): ChatMessage[] {
  try {
    const saved: ChatMessage[] = JSON.parse(sessionStorage.getItem(GUEST_CHAT_KEY) ?? '[]')
    return saved.map((m) => ({ ...m, showcase: m.showcase ?? null }))
  } catch {
    return []
  }
}

interface Shop {
  facets: Facets | null
  user: User | null
  signIn: (token: string, user: User) => void
  signOut: () => void
  chatOpen: boolean
  setChatOpen: (open: boolean) => void
  messages: ChatMessage[]
  sending: boolean
  chatError: string
  send: (text: string) => void
  clearChat: () => void
  /** Cards from the latest assistant reply that had products: rendered on the page by <ChatShowcase />. */
  showcase: Showcase | null
  /** Changes each time a new reply brings cards, so the page can scroll them into view. */
  showcaseKey: string | null
  dismissShowcase: () => void
  /** The product whose page is open (set by ProductPage), so chat questions like "this in pink?" have a subject. */
  viewing: { id: string; name: string } | null
  setViewing: (v: { id: string; name: string } | null) => void
  /** Saved items (wishlist): product ids, newest first. Kept in this browser, separately per account. */
  saved: string[]
  isSaved: (id: string) => boolean
  toggleSaved: (id: string) => void
}

const ShopContext = createContext<Shop | null>(null)

export function ShopProvider({ children }: { children: ReactNode }) {
  const [facets, setFacets] = useState<Facets | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>(loadGuestChat)
  const [sending, setSending] = useState(false)
  const [chatError, setChatError] = useState('')
  const [freshShowcase, setFreshShowcase] = useState<string | null>(null)
  const [dismissedId, setDismissedId] = useState<string | null>(null)
  const [viewing, setViewing] = useState<{ id: string; name: string } | null>(null)
  const location = useLocation()
  const savedKey = `cc_saved:${user?.id ?? 'guest'}`
  const [saved, setSaved] = useState<string[]>(() => readSaved('cc_saved:guest'))
  useEffect(() => setSaved(readSaved(savedKey)), [savedKey])
  const toggleSaved = useCallback(
    (id: string) =>
      setSaved((current) => {
        const next = current.includes(id) ? current.filter((x) => x !== id) : [id, ...current].slice(0, 30)
        localStorage.setItem(savedKey, JSON.stringify(next))
        return next
      }),
    [savedKey],
  )
  const isSaved = useCallback((id: string) => saved.includes(id), [saved])

  useEffect(() => {
    fetchFacets().then(setFacets).catch(() => setFacets(null))
    if (getToken()) fetchMe().then(setUser).catch(() => setToken(null))
  }, [])

  // Signed-in shoppers load their saved chat; guests keep theirs for this browser tab only.
  useEffect(() => {
    if (user) fetchChatHistory().then(setMessages).catch(() => setMessages([]))
    else setMessages(loadGuestChat())
  }, [user])

  useEffect(() => {
    if (!user) sessionStorage.setItem(GUEST_CHAT_KEY, JSON.stringify(messages.slice(-30)))
  }, [messages, user])

  const signIn = useCallback((token: string, u: User) => {
    setToken(token)
    setUser(u)
  }, [])

  const signOut = useCallback(() => {
    setToken(null)
    setUser(null)
    sessionStorage.removeItem(GUEST_CHAT_KEY)
  }, [])

  const send = useCallback(
    async (text: string) => {
      setChatOpen(true)
      setChatError('')
      const history = user ? [] : messages.slice(-12).map(({ role, content }) => ({ role, content }))
      const params = new URLSearchParams(location.search)
      const onProduct = location.pathname.startsWith('/products/')
      const page: PageContext = {
        path: location.pathname,
        product_id: onProduct ? (viewing?.id ?? decodeURIComponent(location.pathname.slice('/products/'.length))) : null,
        category: location.pathname === '/products' ? params.get('category') : null,
        search: location.pathname === '/products' ? params.get('q') : null,
        saved_ids: saved,
      }
      setMessages((m) => [...m, { id: localId(), role: 'user', content: text, showcase: null }])
      setSending(true)
      try {
        const res = await sendChat(text, history, page)
        const id = localId()
        setMessages((m) => [...m, { id, role: 'assistant', content: res.reply, showcase: res.showcase, checks: res.checks }])
        if (res.showcase) setFreshShowcase(id)
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          setToken(null)
          setUser(null)
        }
        setChatError((e as Error).message)
      } finally {
        setSending(false)
      }
    },
    [messages, user, location.pathname, location.search, viewing, saved],
  )

  const clearChat = useCallback(async () => {
    if (user) await clearChatHistory().catch(() => undefined)
    setMessages([])
  }, [user])

  const latest = useMemo(() => [...messages].reverse().find((m) => m.role === 'assistant' && m.showcase), [messages])
  const showcase = latest && latest.id !== dismissedId ? latest.showcase : null
  const dismissShowcase = useCallback(() => setDismissedId(latest?.id ?? null), [latest])

  const value: Shop = {
    facets, user, signIn, signOut, chatOpen, setChatOpen, messages, sending, chatError, send, clearChat,
    showcase, showcaseKey: freshShowcase, dismissShowcase, viewing, setViewing, saved, isSaved, toggleSaved,
  }
  return <ShopContext.Provider value={value}>{children}</ShopContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useShop(): Shop {
  const shop = useContext(ShopContext)
  if (!shop) throw new Error('useShop must be used inside <ShopProvider>')
  return shop
}
