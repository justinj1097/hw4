import { Fragment, type ReactNode } from 'react'

/** Inline **bold** only; everything else is plain text, so model output can never inject HTML. */
function inline(text: string, key: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4 ? (
      <strong key={`${key}-${i}`}>{part.slice(2, -2)}</strong>
    ) : (
      <Fragment key={`${key}-${i}`}>{part}</Fragment>
    ),
  )
}

/** A tiny, safe markdown subset for chat replies: paragraphs, "- " / "1. " lists, and **bold**. */
export function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let list: { ordered: boolean; items: string[] } | null = null
  const flush = () => {
    if (!list) return
    const Tag = list.ordered ? 'ol' : 'ul'
    blocks.push(
      <Tag key={`l${blocks.length}`}>
        {list.items.map((item, i) => (
          <li key={i}>{inline(item, `li${blocks.length}-${i}`)}</li>
        ))}
      </Tag>,
    )
    list = null
  }
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    const bullet = line.match(/^[-*•]\s+(.*)$/)
    const numbered = line.match(/^\d+[.)]\s+(.*)$/)
    if (bullet || numbered) {
      const ordered = Boolean(numbered)
      if (list && list.ordered !== ordered) flush()
      list = list ?? { ordered, items: [] }
      list.items.push((bullet ?? numbered)![1])
    } else {
      flush()
      if (line) blocks.push(<p key={`p${blocks.length}`}>{inline(line.replace(/^#+\s*/, ''), `p${blocks.length}`)}</p>)
    }
  }
  flush()
  return <>{blocks}</>
}
