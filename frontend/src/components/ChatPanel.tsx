import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useShop } from '../store'
import { Boola } from './Boola'
import { Markdown } from './Markdown'
import { ProductTile } from './ProductTile'

const PRODUCT_SUGGESTIONS = ['Do you have this in pink?', 'Is this in stock in medium?', 'What goes well with this?']
const SUGGESTIONS = [
  'What hoodies do you have in navy?',
  'Gift ideas for a Yale parent under $80',
  'Is the Yale Dad T-shirt in stock in XL?',
  'What is your return policy?',
]

/** Floating chat in the bottom-right corner of every page. It sends messages to the backend's /api/chat. */
export function ChatPanel() {
  const { chatOpen: open, setChatOpen, user, messages, sending, chatError: error, send, clearChat, viewing } = useShop()
  const suggestions = viewing ? PRODUCT_SUGGESTIONS : SUGGESTIONS
  const [draft, setDraft] = useState('')
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending, open])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const submit = (text: string) => {
    const t = text.trim()
    if (!t || sending) return
    send(t)
    setDraft('')
  }

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit(draft)
    }
  }

  const showOnPage = () => document.getElementById('chat-showcase')?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => setChatOpen(true)} aria-label="Open the shopping assistant, Boola">
        <span className="launcher-bubble">Ask Boola</span>
        <Boola size={58} mood="idle" />
      </button>
    )
  }

  return (
    <aside className="chat" aria-label="Shopping assistant">
      <div className="chat-head">
        <Boola size={42} mood={sending ? 'thinking' : 'happy'} />
        <div className="chat-title">
          <strong>Boola</strong>
          <span>Campus Customs shopping help · {user ? `hi, ${user.first_name}! Chats are saved` : 'log in to save chats'}</span>
        </div>
        <div className="chat-head-actions">
          {messages.length > 0 && <button className="link-button light" onClick={clearChat}>Clear</button>}
          <button className="chat-close" onClick={() => setChatOpen(false)} aria-label="Close assistant">×</button>
        </div>
      </div>

      <div className="chat-list" ref={listRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <p className="chat-hello">
              <em>Woof, hi{user ? ` ${user.first_name}` : ''}!</em> I'm Boola, the Campus Customs bulldog. I can sniff out merch, check prices and
              stock by size, and answer store questions. Try:
            </p>
            <div className="chips">
              {suggestions.map((s) => <button key={s} className="chip" onClick={() => submit(s)}>{s}</button>)}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`msg msg-${m.role}`}>
            {m.role === 'assistant' ? (
              <div className="msg-row">
                <Boola size={28} />
                <div className="bubble"><Markdown text={m.content} /></div>
              </div>
            ) : (
              <div className="bubble">{m.content}</div>
            )}
            {m.role === 'assistant' && m.checks && m.checks.items.length > 0 && (
              <p className="checks" title="Written by the server from the lookups it actually ran for this answer">
                <span aria-hidden="true">✓</span> Checked the store database at{' '}
                {new Date(m.checks.checked_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}: {m.checks.items.join(' · ')}
              </p>
            )}
            {m.role === 'assistant' && m.showcase && (
              <>
                <div className="msg-products">
                  {m.showcase.items.slice(0, 4).map((p) => <ProductTile key={p.product_id} product={p} compact />)}
                </div>
                <button className="link-button show-on-page" onClick={showOnPage}>
                  {m.showcase.items.length > 4 ? `See all ${m.showcase.items.length} on the page ↑` : 'See them on the page ↑'}
                </button>
              </>
            )}
          </div>
        ))}
        {sending && (
          <div className="msg msg-assistant">
            <div className="msg-row">
              <Boola size={28} mood="thinking" />
              <div className="bubble typing" aria-live="polite">
                <span className="paws" aria-hidden="true"><span>🐾</span><span>🐾</span><span>🐾</span></span>
                <span className="typing-text">Sniffing around the stockroom…</span>
              </div>
            </div>
          </div>
        )}
        {error && <p className="form-error chat-error" role="alert">{error}</p>}
      </div>

      {viewing && (
        <div className="chat-context" title="The assistant knows which product page you're on">
          Asking about: <strong>{viewing.name}</strong>
        </div>
      )}
      <div className="chat-input">
        <textarea ref={inputRef} rows={1} value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={onKey}
          placeholder="Ask Boola about sizes, prices, gifts…" aria-label="Message" maxLength={2000} />
        <button className="btn btn-primary" onClick={() => submit(draft)} disabled={sending || !draft.trim()}>Send</button>
      </div>
    </aside>
  )
}
